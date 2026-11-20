#!/usr/bin/env python3
"""
Extract deterministic official LLMmap (USENIX Security 2025) open-set embeddings
and exact mixed-routing evaluation distances from Study S5a JSONL logs.

Runs once with PyTorch + Transformers via `uv run` and writes a compact JSON
artifact (`results/s5a_llmmap_inference.json`) so that `s5_analyze.py` and the
offline replication package remain 100% pure NumPy with zero PyTorch dependency.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
EXT_DIR = Path(__file__).resolve().parent
DATA_PATH = EXT_DIR / "data" / "s5a_llmmap.jsonl"
OUT_PATH = EXT_DIR / "results" / "s5a_llmmap_inference.json"
TARGETS_PATH = ROOT / "extensions" / "live_validation_20261111" / "configs" / "targets.s3_20models_locked64.json"
PROMPTS_PATH = EXT_DIR / "configs" / "prompts_s5_competitors.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract official LLMmap open-set embeddings for S5a")
    parser.add_argument(
        "--llmmap-repo",
        type=str,
        required=True,
        help="Path to cloned pasquini-dario/LLMmap repository",
    )
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20261120)
    args = parser.parse_args()

    repo_path = Path(args.llmmap_repo).resolve()
    sys.path.insert(0, str(repo_path))
    from LLMmap.inference import load_LLMmap  # noqa: E402

    model_dir = repo_path / "data" / "pretrained_models" / "default"
    t0 = time.perf_counter()
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[LLMmap] Loading pretrained open-set model on device={device}...", flush=True)
    # Load on CPU first because LLMmap calls torch.load without map_location
    conf, inf = load_LLMmap(str(model_dir), device="cpu")
    if device == "mps":
        inf.emb_model.model = inf.emb_model.model.to(device)
        inf.model = inf.model.to(device)
        inf.emb_queries = inf.emb_queries.to(device)
    print(f"[LLMmap] Loaded in {time.perf_counter() - t0:.1f}s (is_open={conf['is_open']}, max_chars={conf['max_number_chars_response']})", flush=True)

    targets = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))["targets"]
    tids = [t["id"] for t in targets]
    tid_to_model = {t["id"]: t["model"] for t in targets}
    s5_cfg = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))["s5a_llmmap"]
    prompt_ids = [p["prompt_id"] for p in s5_cfg["prompts"]]
    n_reps = int(s5_cfg["reps"])
    max_chars = int(conf["max_number_chars_response"])

    # Verify verbatim query order matches conf["queries"]
    for idx, p in enumerate(s5_cfg["prompts"]):
        assert p["text"] == conf["queries"][idx], f"Query {idx} mismatch vs conf.json!"

    # Load S5a JSONL (deduplicated by trial_key keeping latest)
    rows_by_key: dict[str, dict[str, Any]] = {}
    for line in DATA_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows_by_key[r["trial_key"]] = r

    # Organize preprocessed answer strings: answers[tid][rep][q_idx]
    answers_grid: list[str] = []
    index_map: dict[tuple[str, int, int], int] = {}
    blocked_grid: dict[str, list[int]] = collections.defaultdict(list)

    for tid in tids:
        for rep in range(n_reps):
            for q_idx, pid in enumerate(prompt_ids):
                tk = f"s5a_llmmap|{tid}|{pid}|rep{rep}"
                r = rows_by_key[tk]
                txt = (r.get("raw_text") or "")[:max_chars]
                index_map[(tid, rep, q_idx)] = len(answers_grid)
                answers_grid.append(txt)
                if r.get("blocked_by_moderation") or r.get("http_status") != 200:
                    blocked_grid[tid].append((rep, q_idx, r.get("http_status")))

    print(f"[LLMmap] Computing E5-large-instruct embeddings for {len(answers_grid)} answers...", flush=True)
    t1 = time.perf_counter()
    with torch.no_grad():
        all_ans_embs = inf.emb_model.get_embedding_batched(answers_grid, batch_size=args.batch_size)
        all_ans_embs = all_ans_embs.to(device)
        q_embs = inf.emb_queries.to(device)  # (8, 1024)
    print(f"[LLMmap] Answer embeddings shape={tuple(all_ans_embs.shape)} in {time.perf_counter() - t1:.1f}s", flush=True)

    # Helper: run InferenceModelLLMmap on batches of 8-query answer index lists
    def run_traces_batch(idx_batches: list[list[int]], chunk_size: int = 256) -> np.ndarray:
        outs: list[np.ndarray] = []
        with torch.no_grad():
            for start in range(0, len(idx_batches), chunk_size):
                chunk = idx_batches[start : start + chunk_size]
                idx_t = torch.tensor(chunk, dtype=torch.long, device=device)  # (B, 8)
                ans_e = all_ans_embs[idx_t]  # (B, 8, 1024)
                q_e = q_embs.unsqueeze(0).expand(ans_e.size(0), -1, -1)  # (B, 8, 1024)
                traces = torch.cat((q_e, ans_e), dim=2)  # (B, 8, 2048)
                emb_384 = inf.model(traces).cpu().numpy()  # (B, 384)
                outs.append(emb_384)
        return np.concatenate(outs, axis=0)

    # 1. Clean trace embeddings: 20 targets x 6 reps = 120 traces
    clean_batches: list[list[int]] = []
    clean_meta: list[tuple[str, int]] = []
    for tid in tids:
        for rep in range(n_reps):
            clean_batches.append([index_map[(tid, rep, q)] for q in range(8)])
            clean_meta.append((tid, rep))

    clean_embs = run_traces_batch(clean_batches)
    clean_emb_dict: dict[str, list[list[float]]] = {tid: [] for tid in tids}
    for (tid, rep), vec in zip(clean_meta, clean_embs):
        clean_emb_dict[tid].append([round(float(x), 6) for x in vec])

    # 2. Check pre-shipped 2024 52-template DB coverage & zero-shot top-1
    shipped_templates = inf.templates_map or {}
    shipped_names = sorted(shipped_templates.keys())
    shipped_db = np.stack([shipped_templates[k] for k in shipped_names], axis=0)
    zero_shot_top1: dict[str, dict[str, Any]] = {}
    for tid in tids:
        mean_vec = np.mean(np.array(clean_emb_dict[tid], dtype=np.float64), axis=0, keepdims=True)
        dists = np.linalg.norm(shipped_db - mean_vec, axis=1)
        best_i = int(np.argmin(dists))
        zero_shot_top1[tid] = {
            "claimed_model": tid_to_model[tid],
            "nearest_shipped_template": shipped_names[best_i],
            "distance": round(float(dists[best_i]), 4),
        }

    # 3. Exact Mixed-Routing Simulation (per-query independent Bernoulli fallback with prob lambda)
    # Enroll on reps 0,1,2 (3-trace averaged template = 24 calls) AND single-trace rep 0 (8 calls).
    # Test on reps 3,4,5 (3 traces = 24 calls) AND single-trace rep 3 (8 calls).
    # For every ordered (declared M, substitute R != M) pair (380 pairs) x 5 fixed seeds x lambda in {0.20, 0.40, 0.50}:
    # replace each individual query response with substitute R's response at the same (rep, q) with prob lambda,
    # pass each resulting 8-query trace through InferenceModelLLMmap, and compute Euclidean distance to enrolled template.
    rng = np.random.default_rng(args.seed)
    lambdas = [0.20, 0.40, 0.50]
    n_seeds = 5

    # Precompute enrollment templates
    enroll_1 = {tid: np.array(clean_emb_dict[tid][0], dtype=np.float64) for tid in tids}
    enroll_3 = {tid: np.mean(np.array(clean_emb_dict[tid][:3], dtype=np.float64), axis=0) for tid in tids}

    # Pure genuine distances (lambda=0) for 1v1 (rep0 vs rep3) and 3v3 (reps 0..2 vs 3..5)
    pure_gen_1 = {
        tid: float(np.linalg.norm(np.array(clean_emb_dict[tid][3]) - enroll_1[tid]))
        for tid in tids
    }
    pure_gen_3 = {
        tid: float(np.linalg.norm(np.mean(np.array(clean_emb_dict[tid][3:6]), axis=0) - enroll_3[tid]))
        for tid in tids
    }
    pure_imp_1 = [
        float(np.linalg.norm(np.array(clean_emb_dict[r][3]) - enroll_1[m]))
        for m in tids for r in tids if r != m
    ]
    pure_imp_3 = [
        float(np.linalg.norm(np.mean(np.array(clean_emb_dict[r][3:6]), axis=0) - enroll_3[m]))
        for m in tids for r in tids if r != m
    ]

    t2 = time.perf_counter()
    mixed_results: dict[str, Any] = {}
    for lam in lambdas:
        lam_key = f"{lam:.2f}"
        # Build all traces for (seed, m, r, trace_rep in [3,4,5]): 5 * 380 * 3 = 5,700 traces
        trace_batches: list[list[int]] = []
        meta_pairs: list[tuple[int, str, str]] = []
        for s_idx in range(n_seeds):
            for m in tids:
                for r in tids:
                    if r == m:
                        continue
                    meta_pairs.append((s_idx, m, r))
                    for rep in (3, 4, 5):
                        mask = rng.random(8) < lam
                        trace_batches.append([
                            index_map[(r if mask[q] else m, rep, q)]
                            for q in range(8)
                        ])
        embs = run_traces_batch(trace_batches, chunk_size=512)  # (5*380*3, 384)
        embs = embs.reshape(len(meta_pairs), 3, 384)

        dists_1_all: list[float] = []
        dists_3_all: list[float] = []
        dists_3_max_all: list[float] = []
        for idx, (s_idx, m, r) in enumerate(meta_pairs):
            e3 = embs[idx]  # (3, 384)
            # 1-trace test (rep 3) vs 1-trace enroll (rep 0)
            d1 = float(np.linalg.norm(e3[0] - enroll_1[m]))
            # 3-trace averaged embedding test (reps 3..5) vs 3-trace enroll (reps 0..2)
            d3_mean = float(np.linalg.norm(e3.mean(axis=0) - enroll_3[m]))
            # 3-trace mean of per-trace distances (also check max per-trace distance)
            d3_per = np.linalg.norm(e3 - enroll_3[m][None, :], axis=1)
            dists_1_all.append(round(d1, 6))
            dists_3_all.append(round(d3_mean, 6))
            dists_3_max_all.append(round(float(d3_per.max()), 6))

        mixed_results[lam_key] = {
            "n_seeds": n_seeds,
            "n_pairs_per_seed": len(tids) * (len(tids) - 1),
            "dists_1trace_vs_1enroll": dists_1_all,
            "dists_3trace_avg_vs_3enroll": dists_3_all,
            "dists_3trace_max_vs_3enroll": dists_3_max_all,
        }
    print(f"[LLMmap] Mixed-routing batched inference finished in {time.perf_counter() - t2:.1f}s", flush=True)

    # Local CPU inference latency benchmark (10 runs of single 8-query trace through E5 + Transformer)
    inf_cpu_emb = inf.emb_model.model.to("cpu")
    inf_cpu_net = inf.model.to("cpu")
    q_cpu = inf.emb_queries.to("cpu")
    sample_answers = [answers_grid[index_map[(tids[0], 0, q)]] for q in range(8)]
    lat_ms: list[float] = []
    with torch.no_grad():
        # Warmup
        _tok = inf.emb_model.tokenizer(sample_answers, return_tensors="pt", padding=True, add_special_tokens=True, truncation=True, max_length=512)
        _ae = inf.emb_model.get_embs(inf_cpu_emb(**_tok), _tok.attention_mask)
        _ = inf_cpu_net(torch.cat((q_cpu, _ae), dim=1).unsqueeze(0))
        for _ in range(5):
            ts = time.perf_counter()
            _tok = inf.emb_model.tokenizer(sample_answers, return_tensors="pt", padding=True, add_special_tokens=True, truncation=True, max_length=512)
            _ae = inf.emb_model.get_embs(inf_cpu_emb(**_tok), _tok.attention_mask)
            _ = inf_cpu_net(torch.cat((q_cpu, _ae), dim=1).unsqueeze(0))
            lat_ms.append(round((time.perf_counter() - ts) * 1000.0, 2))
    print(f"[LLMmap] CPU single-trace scoring median latency: {float(np.median(lat_ms)):.1f} ms", flush=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_source": "pasquini-dario/LLMmap data/pretrained_models/default (is_open=true, feature_size=384, emb=intfloat/multilingual-e5-large-instruct)",
        "seed": args.seed,
        "targets": tids,
        "n_reps": n_reps,
        "shipped_template_count": len(shipped_names),
        "shipped_template_names": shipped_names,
        "zero_shot_nearest_shipped": zero_shot_top1,
        "blocked_entries_count": {k: len(v) for k, v in blocked_grid.items()},
        "cpu_single_trace_inference_ms": {
            "runs_ms": lat_ms,
            "median_ms": round(float(np.median(lat_ms)), 2),
        },
        "clean_trace_embeddings_384d": clean_emb_dict,
        "mixed_routing": {
            "pure_gen_1v1": pure_gen_1,
            "pure_gen_3v3": pure_gen_3,
            "pure_imp_1v1_summary": {
                "mean": round(float(np.mean(pure_imp_1)), 6),
                "min": round(float(np.min(pure_imp_1)), 6),
            },
            "pure_imp_3v3_summary": {
                "mean": round(float(np.mean(pure_imp_3)), 6),
                "min": round(float(np.min(pure_imp_3)), 6),
            },
            "lambdas": mixed_results,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[LLMmap] Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)", flush=True)


if __name__ == "__main__":
    main()
