#!/usr/bin/env python3
"""
Deterministic Offline Analyzer for Study S5 (Competitor Benchmark on OpenRouter).

Pure NumPy (zero PyTorch dependency): consumes
  - data/s5a_llmmap.jsonl + results/s5a_llmmap_inference.json (LLMmap USENIX Security 2025)
  - data/s5b_gao_longform.jsonl (Gao et al. ICLR 2025 native long-form mmd_hamming + 4-gram)
  - data/s5c_hueprint_anchor.jsonl (same-day HuePrint 10-probe anchor + 9-day S3->S5c check)

Produces `results/s5_results.json` and a human-readable summary on stdout.
"""

from __future__ import annotations

import collections
import hashlib
import itertools
import json
import math
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze as an  # noqa: E402
from hueprint_audit.core import (  # noqa: E402
    group as hp_group,
    jitter_group,
    matrix as hp_matrix,
    stats as hp_stats,
    thresholds as hp_thresholds,
)
from hueprint_audit.baselines import exact_mmd_u_cell  # noqa: E402

TARGETS_PATH = ROOT / "extensions" / "live_validation_20261111" / "configs" / "targets.s3_20models_locked64.json"
PRICING_PATH = EXT_DIR / "configs" / "openrouter_pricing_20261120.json"
PROMPTS_PATH = EXT_DIR / "configs" / "prompts_s5_competitors.json"
S3_COLOR_PATH = ROOT / "extensions" / "live_validation_20261111" / "data" / "s3a_hueprint_locked64_n30.jsonl"
DATA_DIR = EXT_DIR / "data"
RES_DIR = EXT_DIR / "results"

# Scenario L (Llama-3.3-70B) and Scenario G (GPT-4o) common catalog rates (USD per token)
RATE_L = (0.71e-6, 0.71e-6)
RATE_G = (2.50e-6, 10.00e-6)

# Refusal / injection / gateway rule detectors (transparent operational telemetry)
REFUSAL_TEXT_RE = re.compile(
    r"\b(i cannot|i can't|cannot assist|cannot help|cannot provide|can't help|can't provide|can't assist|"
    r"not able to|unable to|won't provide|refuse|illegal|dangerous|harmful|explosive|sorry,?\s+i)\b",
    re.IGNORECASE,
)
INJECTION_PROMPT_RE = re.compile(r"(ignore\s+(that|the|previous|above)|\]\]\]\]|\}\}\}\}|\*/)", re.IGNORECASE)
HARMFUL_PROMPT_RE = re.compile(r"\b(build\s+a\s+bomb|make\s+a\s+bomb|explosive)\b", re.IGNORECASE)
S4_LITERAL_RE = re.compile(r"#RRGGBB|R\s*,\s*G\s*,\s*B", re.IGNORECASE)
S4_DIRECTIVE_RE = re.compile(
    r"(respond\s+with\s+only|reply\s+with\s+only|do\s+not\s+output\s+anything\s+except|"
    r"no\s+words,?\s+no\s+explanation|start\s+the\s+continuation\s+immediately)",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl_dedup(path: Path) -> tuple[list[dict[str, Any]], int, str]:
    raw_lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    latest: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for ln in raw_lines:
        r = json.loads(ln)
        k = r["trial_key"]
        if k not in latest:
            order.append(k)
        latest[k] = r
    return [latest[k] for k in order], len(raw_lines), sha256_file(path)


def estimate_c8_seconds(latencies_ms: list[float], workers: int = 8) -> float:
    """Ideal greedy makespan of recorded latencies across `workers` parallel slots (seconds)."""
    if not latencies_ms:
        return 0.0
    slots = [0.0] * workers
    for ms in latencies_ms:
        idx = int(np.argmin(slots))
        slots[idx] += max(0.0, float(ms))
    return max(slots) / 1000.0


def summarize_overhead(
    rows: list[dict[str, Any]],
    tids: list[str],
    pricing_by_tid: dict[str, tuple[float, float]],
    rep_filter=None,
    prompt_filter=None,
) -> dict[str, Any]:
    by_tid: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        if rep_filter is not None and not rep_filter(int(r["rep"])):
            continue
        if prompt_filter is not None and not prompt_filter(r["prompt_id"]):
            continue
        by_tid[r["target_id"]].append(r)

    per_t = []
    for tid in tids:
        tr = by_tid.get(tid, [])
        in_tok = sum(int((r.get("usage") or {}).get("input_tokens") or 0) for r in tr)
        out_tok = sum(int((r.get("usage") or {}).get("output_tokens") or 0) for r in tr)
        lats = [float(r.get("latency_ms") or 0.0) for r in tr]
        in_r, out_r = pricing_by_tid[tid]
        per_t.append({
            "target_id": tid,
            "calls": len(tr),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "usd_L": in_tok * RATE_L[0] + out_tok * RATE_L[1],
            "usd_G": in_tok * RATE_G[0] + out_tok * RATE_G[1],
            "usd_actual_catalog": in_tok * in_r + out_tok * out_r,
            "call_p50_s": (statistics.median(lats) / 1000.0) if lats else 0.0,
            "est_c8_s": estimate_c8_seconds(lats, workers=8),
        })

    return {
        "calls_median": int(statistics.median(x["calls"] for x in per_t)),
        "input_tokens_median": round(float(statistics.median(x["input_tokens"] for x in per_t)), 1),
        "output_tokens_median": round(float(statistics.median(x["output_tokens"] for x in per_t)), 1),
        "usd_L_median": round(float(statistics.median(x["usd_L"] for x in per_t)), 4),
        "usd_G_median": round(float(statistics.median(x["usd_G"] for x in per_t)), 4),
        "usd_actual_median": round(float(statistics.median(x["usd_actual_catalog"] for x in per_t)), 4),
        "usd_actual_total_20models": round(float(sum(x["usd_actual_catalog"] for x in per_t)), 4),
        "call_p50_s_median": round(float(statistics.median(x["call_p50_s"] for x in per_t)), 2),
        "est_c8_s_median": round(float(statistics.median(x["est_c8_s"] for x in per_t)), 2),
    }


def make_family_masks(tids: list[str], family_by_tid: dict[str, str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(tids)
    pos = np.eye(n, dtype=bool)
    neg_all = ~pos
    neg_fam = np.array(
        [[i != j and family_by_tid[tids[i]] == family_by_tid[tids[j]] for j in range(n)] for i in range(n)],
        dtype=bool,
    )
    return pos, neg_all, neg_fam


def eval_dist_matrix(mat: np.ndarray, pos: np.ndarray, neg_all: np.ndarray, neg_fam: np.ndarray) -> dict[str, Any]:
    s_all = hp_stats(mat, pos, neg_all)
    s_fam = hp_stats(mat, pos, neg_fam)
    return {
        "auc": round(s_all["auc"], 4),
        "eer": round(s_all["eer"], 4),
        "eer_pct": round(100.0 * s_all["eer"], 2),
        "eer_discrete_pct": round(100.0 * s_all["eer_discrete"], 2),
        "top1": round(s_all["top1"], 4),
        "top1_hits": f"{int(round(s_all['top1'] * len(mat)))}/{len(mat)}",
        "genuine_mean": round(s_all["genuine_mean"], 4),
        "impostor_mean": round(s_all["impostor_mean"], 4),
        "within_family_auc": round(s_fam["auc"], 4),
        "within_family_eer_pct": round(100.0 * s_fam["eer"], 2),
        "n_within_family_neg": int(neg_fam.sum()),
    }


# ---------------------------------------------------------------------------
# Arm S5a: LLMmap (USENIX Security 2025) official open-set analysis
# ---------------------------------------------------------------------------

def analyze_s5a(
    rows: list[dict[str, Any]],
    tids: list[str],
    family_by_tid: dict[str, str],
    pricing_by_tid: dict[str, tuple[float, float]],
    llmmap_inf: dict[str, Any],
) -> dict[str, Any]:
    pos, neg_all, neg_fam = make_family_masks(tids, family_by_tid)
    embs = {tid: np.array(llmmap_inf["clean_trace_embeddings_384d"][tid], dtype=np.float64) for tid in tids}

    # Operational safety / moderation / refusal telemetry
    total = len(rows)
    http_ok = sum(1 for r in rows if r.get("http_status") == 200)
    mod_blocks = [r for r in rows if r.get("blocked_by_moderation")]
    other_errs = [r for r in rows if r.get("http_status") != 200 and not r.get("blocked_by_moderation")]
    q1_rows = [r for r in rows if r["prompt_id"] == "llmmap_q1"]
    q1_mod_blocks = sum(1 for r in q1_rows if r.get("blocked_by_moderation"))
    q1_text_refusals = sum(
        1 for r in q1_rows
        if r.get("http_status") == 200 and REFUSAL_TEXT_RE.search(r.get("raw_text") or "")
    )
    q1_models_blocked = sorted({r["target_id"] for r in q1_rows if r.get("blocked_by_moderation")})
    q1_models_refused_or_blocked = sorted({
        r["target_id"] for r in q1_rows
        if r.get("blocked_by_moderation") or (r.get("http_status") == 200 and REFUSAL_TEXT_RE.search(r.get("raw_text") or ""))
    })

    # Prompt-level gateway signature rates (across the 8 official queries)
    s5a_prompts = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))["s5a_llmmap"]["prompts"]
    n_inj_prompts = sum(1 for p in s5a_prompts if INJECTION_PROMPT_RE.search(p["text"]))
    n_harm_prompts = sum(1 for p in s5a_prompts if HARMFUL_PROMPT_RE.search(p["text"]))
    n_flagged_any = sum(
        1 for p in s5a_prompts
        if INJECTION_PROMPT_RE.search(p["text"]) or HARMFUL_PROMPT_RE.search(p["text"])
    )

    def pairwise_euclid(enroll_reps: list[int], query_reps: list[int], sub_tids: list[str] | None = None) -> np.ndarray:
        use = sub_tids or tids
        E = np.stack([embs[t][enroll_reps].mean(axis=0) for t in use], axis=0)
        Q = np.stack([embs[t][query_reps].mean(axis=0) for t in use], axis=0)
        diff = E[:, None, :] - Q[None, :, :]
        return np.linalg.norm(diff, axis=-1)

    # Disjoint 1v1 pairs: (0,1), (2,3), (4,5) and canonical (0,3)
    pair_splits_1v1 = [([0], [1]), ([2], [3]), ([4], [5]), ([0], [3])]
    res_1v1_list = [eval_dist_matrix(pairwise_euclid(a, b), pos, neg_all, neg_fam) for a, b in pair_splits_1v1[:3]]
    res_1v1_03 = eval_dist_matrix(pairwise_euclid([0], [3]), pos, neg_all, neg_fam)
    res_2v2 = eval_dist_matrix(pairwise_euclid([0, 1], [2, 3]), pos, neg_all, neg_fam)
    res_3v3 = eval_dist_matrix(pairwise_euclid([0, 1, 2], [3, 4, 5]), pos, neg_all, neg_fam)

    # Subset excluding any model that experienced HTTP moderation blocks (for fair sensitivity check)
    clean_tids = [t for t in tids if t not in set(q1_models_blocked)]
    sub_pos, sub_neg_all, sub_neg_fam = make_family_masks(clean_tids, family_by_tid)
    res_1v1_noblock = eval_dist_matrix(pairwise_euclid([0], [3], clean_tids), sub_pos, sub_neg_all, sub_neg_fam)
    res_3v3_noblock = eval_dist_matrix(pairwise_euclid([0, 1, 2], [3, 4, 5], clean_tids), sub_pos, sub_neg_all, sub_neg_fam)

    # Zero-shot shipped template overlap check
    shipped_lower = {s.lower() for s in llmmap_inf["shipped_template_names"]}
    claimed_models = {r["target_id"]: r["claimed_model"] for r in rows}
    overlap_2024 = [
        tid for tid in tids
        if any(tok in shipped_lower for tok in [claimed_models[tid].lower(), claimed_models[tid].split("/")[-1].lower()])
    ]
    # Also check loose substring overlap (e.g. gpt-4o -> gpt-4o-2024-05-13, llama-3.1-8b-instruct -> meta-llama/Meta-Llama-3.1-8B-Instruct)
    loose_overlap = []
    for tid in tids:
        slug = claimed_models[tid].split("/")[-1].lower()
        if any(slug in s or s.split("/")[-1] in slug for s in shipped_lower):
            loose_overlap.append(tid)

    # Mixed-routing analysis from exact batched InferenceModelLLMmap outputs
    mr = llmmap_inf["mixed_routing"]
    pure_g1 = np.array([mr["pure_gen_1v1"][t] for t in tids], dtype=np.float64)
    pure_g3 = np.array([mr["pure_gen_3v3"][t] for t in tids], dtype=np.float64)
    # Apples-to-apples max-of-3 genuine distances against 3-trace enrollment template
    pure_g3_max = np.array([
        max(float(np.linalg.norm(embs[t][rep] - embs[t][:3].mean(axis=0))) for rep in (3, 4, 5))
        for t in tids
    ], dtype=np.float64)
    mat_1v1_03 = pairwise_euclid([0], [3])
    mat_3v3 = pairwise_euclid([0, 1, 2], [3, 4, 5])
    tau_mid_1 = hp_thresholds(mat_1v1_03)["tau_mid"]
    tau_mid_3 = hp_thresholds(mat_3v3)["tau_mid"]
    tau_q95_1 = float(np.quantile(pure_g1, 0.95))
    tau_q95_3 = float(np.quantile(pure_g3, 0.95))
    tau_q95_3max = float(np.quantile(pure_g3_max, 0.95))

    # Build within-family indicator aligned to (5 seeds x ordered m != r)
    pair_is_same_fam = np.array(
        [family_by_tid[m] == family_by_tid[r] for _s in range(5) for m in tids for r in tids if r != m],
        dtype=bool,
    )

    mixed_summary: dict[str, Any] = {}
    for lam_key, blk in mr["lambdas"].items():
        d1 = np.array(blk["dists_1trace_vs_1enroll"], dtype=np.float64)
        d3 = np.array(blk["dists_3trace_avg_vs_3enroll"], dtype=np.float64)
        d3_max = np.array(blk["dists_3trace_max_vs_3enroll"], dtype=np.float64)
        r1 = an.compute_roc_eer(pure_g1.tolist(), d1.tolist())
        r3 = an.compute_roc_eer(pure_g3.tolist(), d3.tolist())
        r3_max = an.compute_roc_eer(pure_g3_max.tolist(), d3_max.tolist())
        r3_fam = an.compute_roc_eer(pure_g3.tolist(), d3[pair_is_same_fam].tolist())
        r1_fam = an.compute_roc_eer(pure_g1.tolist(), d1[pair_is_same_fam].tolist())
        mixed_summary[lam_key] = {
            "1trace_8calls": {
                "auc": round(r1["auc_raw"], 4),
                "eer_pct": round(100.0 * r1["eer_linear_raw"], 2),
                "det_at_tau_mid_pct": round(100.0 * float(np.mean(d1 > tau_mid_1)), 2),
                "det_at_q95_fpr5_pct": round(100.0 * float(np.mean(d1 > tau_q95_1)), 2),
                "within_family_auc": round(r1_fam["auc_raw"], 4),
                "within_family_det_q95_pct": round(100.0 * float(np.mean(d1[pair_is_same_fam] > tau_q95_1)), 2),
            },
            "3trace_24calls_avg": {
                "auc": round(r3["auc_raw"], 4),
                "eer_pct": round(100.0 * r3["eer_linear_raw"], 2),
                "det_at_tau_mid_pct": round(100.0 * float(np.mean(d3 > tau_mid_3)), 2),
                "det_at_q95_fpr5_pct": round(100.0 * float(np.mean(d3 > tau_q95_3)), 2),
                "within_family_auc": round(r3_fam["auc_raw"], 4),
                "within_family_det_q95_pct": round(100.0 * float(np.mean(d3[pair_is_same_fam] > tau_q95_3)), 2),
            },
            "3trace_24calls_max": {
                "auc": round(r3_max["auc_raw"], 4),
                "eer_pct": round(100.0 * r3_max["eer_linear_raw"], 2),
                "det_at_q95_fpr5_pct": round(100.0 * float(np.mean(d3_max > tau_q95_3max)), 2),
            },
        }

    return {
        "health": {
            "unique_trials": total,
            "http_200_count": http_ok,
            "http_200_pct": round(100.0 * http_ok / max(1, total), 2),
            "moderation_blocks_total": len(mod_blocks),
            "other_errors_total": len(other_errs),
            "q1_bomb_total": len(q1_rows),
            "q1_bomb_http_mod_blocks": q1_mod_blocks,
            "q1_bomb_text_refusals": q1_text_refusals,
            "q1_bomb_refusal_or_block_pct": round(100.0 * (q1_mod_blocks + q1_text_refusals) / max(1, len(q1_rows)), 2),
            "q1_models_http_blocked": q1_models_blocked,
            "q1_models_refused_or_blocked_count": len(q1_models_refused_or_blocked),
            "prompt_injection_queries_of_8": n_inj_prompts,
            "harmful_keyword_queries_of_8": n_harm_prompts,
            "security_flagged_queries_of_8": n_flagged_any,
            "shipped_2024_db_loose_overlap_of_20": loose_overlap,
        },
        "verification": {
            "1v1_8calls_mean_3disjoint": {
                "auc": round(float(np.mean([x["auc"] for x in res_1v1_list])), 4),
                "eer_pct": round(float(np.mean([x["eer_pct"] for x in res_1v1_list])), 2),
                "top1": round(float(np.mean([x["top1"] for x in res_1v1_list])), 4),
                "within_family_eer_pct": round(float(np.mean([x["within_family_eer_pct"] for x in res_1v1_list])), 2),
                "splits": res_1v1_list,
            },
            "1v1_8calls_rep0v3": res_1v1_03,
            "2v2_16calls_rep01v23": res_2v2,
            "3v3_24calls_rep012v345": res_3v3,
            "sensitivity_no_http_blocked_models": {
                "n_models": len(clean_tids),
                "1v1_8calls_rep0v3": res_1v1_noblock,
                "3v3_24calls_rep012v345": res_3v3_noblock,
            },
        },
        "mixed_routing": {
            "tau_mid_1v1": round(tau_mid_1, 4),
            "tau_mid_3v3": round(tau_mid_3, 4),
            "clean_frr_at_tau_mid_1v1_pct": round(100.0 * float(np.mean(pure_g1 > tau_mid_1)), 2),
            "clean_frr_at_tau_mid_3v3_pct": round(100.0 * float(np.mean(pure_g3 > tau_mid_3)), 2),
            "by_lambda": mixed_summary,
        },
        "cpu_scoring_median_ms": llmmap_inf["cpu_single_trace_inference_ms"]["median_ms"],
        "overhead": {
            "1trace_8calls": summarize_overhead(rows, tids, pricing_by_tid, rep_filter=lambda r: r == 3),
            "3trace_24calls": summarize_overhead(rows, tids, pricing_by_tid, rep_filter=lambda r: r in (3, 4, 5)),
        },
    }


# ---------------------------------------------------------------------------
# Arm S5b: Gao et al. (ICLR 2025) official Unicode Hamming MMD & 4-gram MMD
# ---------------------------------------------------------------------------

def encode_unicode_matrix(texts: list[str], L: int) -> np.ndarray:
    arr = np.full((len(texts), L), -1, dtype=np.int32)
    for idx, s in enumerate(texts):
        s_trunc = (s or "")[:L]
        if s_trunc:
            arr[idx, : len(s_trunc)] = [ord(c) for c in s_trunc]
    return arr


def gao_mmd_hamming_from_blocks(
    blocks_x: list[np.ndarray],
    blocks_y: list[np.ndarray],
) -> float:
    """
    Exact reproduction of Gao et al. (ICLR 2025) `mmd_hamming` from
    `model_equality_testing/src/tests.py` (lines 26-154) with `normalize=True`.

    Each entry in `blocks_x` / `blocks_y` is an `(n_p, L)` int32 Unicode codepoint
    array (padded with -1) for prompt `p`. Since diag(K_XX) = L for every sequence,
    cosine normalization divides Hamming matches by L. Zeroing cross-prompt entries
    and diagonals gives the exact U-statistic MMD.
    """
    sum_xx = 0.0
    sum_xy = 0.0
    sum_yy = 0.0
    n_xx = 0
    n_xy = 0
    n_yy = 0
    for X, Y in zip(blocks_x, blocks_y):
        nx, L = X.shape
        ny = Y.shape[0]
        if nx < 2 or ny < 2:
            continue
        kxx = np.mean(X[:, None, :] == X[None, :, :], axis=-1)
        kxy = np.mean(X[:, None, :] == Y[None, :, :], axis=-1)
        kyy = np.mean(Y[:, None, :] == Y[None, :, :], axis=-1)
        sum_xx += float(kxx.sum() - np.trace(kxx))
        sum_xy += float(kxy.sum())
        sum_yy += float(kyy.sum() - np.trace(kyy))
        n_xx += nx * (nx - 1)
        n_xy += nx * ny
        n_yy += ny * (ny - 1)
    if n_xx == 0 or n_xy == 0 or n_yy == 0:
        return 0.0
    return sum_xx / n_xx - 2.0 * sum_xy / n_xy + sum_yy / n_yy


def gao_mmd_hamming_permutation_p(
    blocks_x: list[np.ndarray],
    blocks_y: list[np.ndarray],
    n_perm: int,
    rng: np.random.Generator,
) -> tuple[float, float]:
    """
    Prompt-stratified permutation p-value for Gao et al.'s `mmd_hamming`.
    Precomputes the (nx+ny, nx+ny) normalized Hamming Gram matrix once per prompt
    so 999 permutations run in <1 ms per pair.
    """
    K_list = []
    nx_list = []
    ny_list = []
    for X, Y in zip(blocks_x, blocks_y):
        nx = X.shape[0]
        ny = Y.shape[0]
        if nx < 2 or ny < 2:
            continue
        Z = np.concatenate([X, Y], axis=0)
        K = np.mean(Z[:, None, :] == Z[None, :, :], axis=-1)
        np.fill_diagonal(K, 0.0)
        K_list.append(K)
        nx_list.append(nx)
        ny_list.append(ny)

    n_xx = sum(nx * (nx - 1) for nx in nx_list)
    n_xy = sum(nx * ny for nx, ny in zip(nx_list, ny_list))
    n_yy = sum(ny * (ny - 1) for ny in ny_list)

    def eval_split(masks: list[np.ndarray]) -> float:
        sxx = sxy = syy = 0.0
        for K, m in zip(K_list, masks):
            # m is bool array of length nx+ny (True = X, False = Y)
            m_f = m.astype(np.float64)
            y_f = 1.0 - m_f
            sxx += float(m_f @ K @ m_f)
            syy += float(y_f @ K @ y_f)
            sxy += float(m_f @ K @ y_f)
        return sxx / n_xx - 2.0 * sxy / n_xy + syy / n_yy

    obs_masks = [np.array([True] * nx + [False] * ny) for nx, ny in zip(nx_list, ny_list)]
    obs = eval_split(obs_masks)

    # Vectorized permutation across all B permutations per prompt!
    # For each prompt p, draw (n_perm, nx+ny) boolean indicator matrix M
    sxx_b = np.zeros(n_perm, dtype=np.float64)
    syy_b = np.zeros(n_perm, dtype=np.float64)
    sxy_b = np.zeros(n_perm, dtype=np.float64)
    for K, nx, ny in zip(K_list, nx_list, ny_list):
        tot = nx + ny
        # Random permutation indices of shape (n_perm, tot)
        keys = rng.random((n_perm, tot))
        order = np.argpartition(keys, nx, axis=1)
        M = np.zeros((n_perm, tot), dtype=np.float64)
        rows_idx = np.arange(n_perm)[:, None]
        M[rows_idx, order[:, :nx]] = 1.0
        Y = 1.0 - M
        MK = M @ K
        YK = Y @ K
        sxx_b += np.sum(MK * M, axis=1)
        syy_b += np.sum(YK * Y, axis=1)
        sxy_b += np.sum(MK * Y, axis=1)
    perm_stats = sxx_b / n_xx - 2.0 * sxy_b / n_xy + syy_b / n_yy
    pval = (1.0 + float(np.sum(perm_stats >= obs - 1e-12))) / (n_perm + 1.0)
    return float(obs), float(pval)


def build_char_ngram_kernel_matrix(texts: list[str], k: int = 4) -> np.ndarray:
    """Normalized k-spectrum (character k-gram bag) cosine kernel matrix (Gao et al. mmd_kspectrum)."""
    n = len(texts)
    counters: list[collections.Counter[str]] = []
    norms = np.zeros(n, dtype=np.float64)
    for i, s in enumerate(texts):
        s_clean = s or ""
        c = collections.Counter(s_clean[j : j + k] for j in range(max(0, len(s_clean) - k + 1)))
        counters.append(c)
        norms[i] = math.sqrt(sum(v * v for v in c.values()))
    K = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        ci = counters[i]
        ni = norms[i]
        for j in range(i, n):
            nj = norms[j]
            if ni == 0.0 or nj == 0.0:
                val = 1.0 if (ni == 0.0 and nj == 0.0) else 0.0
            else:
                # iterate smaller counter
                a, b = (ci, counters[j]) if len(ci) <= len(counters[j]) else (counters[j], ci)
                dot = sum(v * b[gram] for gram, v in a.items() if gram in b)
                val = dot / (ni * nj)
            K[i, j] = K[j, i] = val
    return K


def analyze_s5b(
    rows: list[dict[str, Any]],
    tids: list[str],
    family_by_tid: dict[str, str],
    pricing_by_tid: dict[str, tuple[float, float]],
    L: int = 256,
    seed: int = 20261120,
) -> dict[str, Any]:
    pos, neg_all, neg_fam = make_family_masks(tids, family_by_tid)
    s5b_prompts = [p["prompt_id"] for p in json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))["s5b_gao_longform"]["prompts"]]

    # Index rows: text_grid[tid][pid][rep]
    text_grid: dict[str, dict[str, dict[int, str]]] = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in rows:
        text_grid[r["target_id"]][r["prompt_id"]][int(r["rep"])] = r.get("raw_text") or ""

    # Pre-encode Unicode matrices per (tid, pid) across all 10 reps: shape (10, L)
    enc: dict[str, dict[str, np.ndarray]] = {}
    for tid in tids:
        enc[tid] = {}
        for pid in s5b_prompts:
            seq_list = [text_grid[tid][pid][rep] for rep in range(10)]
            enc[tid][pid] = encode_unicode_matrix(seq_list, L=L)

    # Helper: compute 20x20 pairwise Gao mmd_hamming matrix for given prompt subset & rep splits
    def mmd_hamming_matrix(pids: list[str], enroll_reps: list[int], query_reps: list[int]) -> np.ndarray:
        n = len(tids)
        mat = np.zeros((n, n), dtype=np.float64)
        for i, ti in enumerate(tids):
            bx = [enc[ti][pid][enroll_reps] for pid in pids]
            for j, tj in enumerate(tids):
                by = [enc[tj][pid][query_reps] for pid in pids]
                mat[i, j] = gao_mmd_hamming_from_blocks(bx, by)
        return mat

    # 1. Schedule comparisons:
    # (a) K=5, 2v2 (10 calls/side, USD-matched to HuePrint 30 calls) averaged across 20 deterministic 5-prompt subsets
    rng_sub = np.random.default_rng(seed)
    all_5_combos = list(itertools.combinations(s5b_prompts, 5))
    chosen_idx = rng_sub.choice(len(all_5_combos), size=20, replace=False)
    k5_2v2_stats = []
    for ci in chosen_idx:
        sub_p = list(all_5_combos[int(ci)])
        m_sub = mmd_hamming_matrix(sub_p, [0, 1], [2, 3])
        k5_2v2_stats.append(eval_dist_matrix(m_sub, pos, neg_all, neg_fam))

    # (b) K=10, 2v2 (20 calls/side), 3v3 (30 calls/side), 5v5 (50 calls/side)
    mat_2v2 = mmd_hamming_matrix(s5b_prompts, [0, 1], [2, 3])
    mat_3v3 = mmd_hamming_matrix(s5b_prompts, [0, 1, 2], [3, 4, 5])
    mat_5v5 = mmd_hamming_matrix(s5b_prompts, [0, 1, 2, 3, 4], [5, 6, 7, 8, 9])

    res_2v2 = eval_dist_matrix(mat_2v2, pos, neg_all, neg_fam)
    res_3v3 = eval_dist_matrix(mat_3v3, pos, neg_all, neg_fam)
    res_5v5 = eval_dist_matrix(mat_5v5, pos, neg_all, neg_fam)

    # Sensitivity check at L=200 and L=400 for 3v3 and 5v5
    l_sens = {}
    for L_alt in (200, 400):
        enc_alt = {tid: {pid: encode_unicode_matrix([text_grid[tid][pid][r] for r in range(10)], L=L_alt) for pid in s5b_prompts} for tid in tids}
        m3_alt = np.zeros((len(tids), len(tids)))
        m5_alt = np.zeros((len(tids), len(tids)))
        for i, ti in enumerate(tids):
            for j, tj in enumerate(tids):
                m3_alt[i, j] = gao_mmd_hamming_from_blocks([enc_alt[ti][p][:3] for p in s5b_prompts], [enc_alt[tj][p][3:6] for p in s5b_prompts])
                m5_alt[i, j] = gao_mmd_hamming_from_blocks([enc_alt[ti][p][:5] for p in s5b_prompts], [enc_alt[tj][p][5:10] for p in s5b_prompts])
        l_sens[str(L_alt)] = {
            "3v3_eer_pct": eval_dist_matrix(m3_alt, pos, neg_all, neg_fam)["eer_pct"],
            "5v5_eer_pct": eval_dist_matrix(m5_alt, pos, neg_all, neg_fam)["eer_pct"],
        }

    # Sensitivity check: Gao et al. 4-gram k-spectrum MMD (character 4-grams) on K5 2v2, K10 2v2, 3v3, 5v5
    # Precompute 200x200 Gram matrix per prompt across (20 tids x 10 reps)
    k4_per_prompt: dict[str, np.ndarray] = {}
    for pid in s5b_prompts:
        all_t = [text_grid[tid][pid][r] for tid in tids for r in range(10)]
        K_big = build_char_ngram_kernel_matrix(all_t, k=4)
        np.fill_diagonal(K_big, 0.0)
        k4_per_prompt[pid] = K_big

    def mmd_4gram_matrix(pids: list[str], er: list[int], qr: list[int]) -> np.ndarray:
        n = len(tids)
        mat = np.zeros((n, n), dtype=np.float64)
        ne, nq = len(er), len(qr)
        for pid in pids:
            K_big = k4_per_prompt[pid]
            for i in range(n):
                ix = [i * 10 + r for r in er]
                xx = K_big[np.ix_(ix, ix)].sum() / (ne * (ne - 1))
                for j in range(n):
                    jy = [j * 10 + r for r in qr]
                    yy = K_big[np.ix_(jy, jy)].sum() / (nq * (nq - 1))
                    xy = K_big[np.ix_(ix, jy)].sum() / (ne * nq)
                    mat[i, j] += (xx - 2.0 * xy + yy) / len(pids)
        return mat

    k5_4g_stats = [
        eval_dist_matrix(mmd_4gram_matrix(list(all_5_combos[int(ci)]), [0, 1], [2, 3]), pos, neg_all, neg_fam)
        for ci in chosen_idx
    ]
    res_4g_2v2 = eval_dist_matrix(mmd_4gram_matrix(s5b_prompts, [0, 1], [2, 3]), pos, neg_all, neg_fam)
    res_4g_3v3 = eval_dist_matrix(mmd_4gram_matrix(s5b_prompts, [0, 1, 2], [3, 4, 5]), pos, neg_all, neg_fam)
    res_4g_5v5 = eval_dist_matrix(mmd_4gram_matrix(s5b_prompts, [0, 1, 2, 3, 4], [5, 6, 7, 8, 9]), pos, neg_all, neg_fam)

    # 2. Official 999-permutation test p <= 0.05 on 3v3 and 5v5
    rng_perm = np.random.default_rng(seed + 101)
    perm_res = {}
    for label, er, qr in [("3v3_30calls", [0, 1, 2], [3, 4, 5]), ("5v5_50calls", [0, 1, 2, 3, 4], [5, 6, 7, 8, 9])]:
        pmat = np.zeros((len(tids), len(tids)), dtype=np.float64)
        t_pair_ms = []
        for i, ti in enumerate(tids):
            bx = [enc[ti][p][er] for p in s5b_prompts]
            for j, tj in enumerate(tids):
                by = [enc[tj][p][qr] for p in s5b_prompts]
                t0 = time.perf_counter()
                _, pv = gao_mmd_hamming_permutation_p(bx, by, n_perm=999, rng=rng_perm)
                if len(t_pair_ms) < 20:
                    t_pair_ms.append((time.perf_counter() - t0) * 1000.0)
                pmat[i, j] = pv
        perm_res[label] = {
            "genuine_rej_pct": round(100.0 * float(np.mean(pmat[pos] <= 0.05)), 2),
            "impostor_rej_pct": round(100.0 * float(np.mean(pmat[neg_all] <= 0.05)), 2),
            "within_family_rej_pct": round(100.0 * float(np.mean(pmat[neg_fam] <= 0.05)), 2),
            "cpu_perm999_median_ms": round(float(np.median(t_pair_ms)), 2),
        }

    # 3. Mixed-routing evaluation (lambda in {0.20, 0.40, 0.50}, 5 fixed seeds across all 380 ordered pairs)
    rng_mix = np.random.default_rng(seed + 202)
    pair_is_same_fam = np.array(
        [family_by_tid[m] == family_by_tid[r] for _s in range(5) for m in tids for r in tids if r != m],
        dtype=bool,
    )
    mixed_out = {}
    for label, er, qr, mat_clean in [
        ("3v3_30calls", [0, 1, 2], [3, 4, 5], mat_3v3),
        ("5v5_50calls", [0, 1, 2, 3, 4], [5, 6, 7, 8, 9], mat_5v5),
    ]:
        pure_g = np.diag(mat_clean)
        tau_mid = hp_thresholds(mat_clean)["tau_mid"]
        tau_q95 = float(np.quantile(pure_g, 0.95))
        lam_dict = {}
        for lam in (0.20, 0.40, 0.50):
            mix_scores = []
            for _s in range(5):
                for m in tids:
                    bx = [enc[m][p][er] for p in s5b_prompts]
                    for r in tids:
                        if r == m:
                            continue
                        by = []
                        for p in s5b_prompts:
                            mask = rng_mix.random(len(qr)) < lam
                            arr = np.where(mask[:, None], enc[r][p][qr], enc[m][p][qr])
                            by.append(arr)
                        mix_scores.append(gao_mmd_hamming_from_blocks(bx, by))
            ms = np.array(mix_scores, dtype=np.float64)
            roc = an.compute_roc_eer(pure_g.tolist(), ms.tolist())
            roc_fam = an.compute_roc_eer(pure_g.tolist(), ms[pair_is_same_fam].tolist())
            lam_dict[f"{lam:.2f}"] = {
                "auc": round(roc["auc_raw"], 4),
                "eer_pct": round(100.0 * roc["eer_linear_raw"], 2),
                "det_at_tau_mid_pct": round(100.0 * float(np.mean(ms > tau_mid)), 2),
                "det_at_q95_fpr5_pct": round(100.0 * float(np.mean(ms > tau_q95)), 2),
                "within_family_auc": round(roc_fam["auc_raw"], 4),
                "within_family_det_q95_pct": round(100.0 * float(np.mean(ms[pair_is_same_fam] > tau_q95)), 2),
            }
        mixed_out[label] = {
            "tau_mid": round(tau_mid, 5),
            "clean_frr_at_tau_mid_pct": round(100.0 * float(np.mean(pure_g > tau_mid)), 2),
            "by_lambda": lam_dict,
        }

    # Single-pair CPU scoring latency (mmd_hamming only, no perm)
    bx0 = [enc[tids[0]][p][:3] for p in s5b_prompts]
    by0 = [enc[tids[1]][p][3:6] for p in s5b_prompts]
    t_raw = []
    for _ in range(30):
        t0 = time.perf_counter()
        _ = gao_mmd_hamming_from_blocks(bx0, by0)
        t_raw.append((time.perf_counter() - t0) * 1000.0)

    http_ok = sum(1 for r in rows if r.get("http_status") == 200)
    nonempty = sum(1 for r in rows if (r.get("raw_text") or "").strip())
    mean_chars = float(np.mean([len(r.get("raw_text") or "") for r in rows]))

    return {
        "health": {
            "unique_trials": len(rows),
            "http_200_count": http_ok,
            "http_200_pct": round(100.0 * http_ok / max(1, len(rows)), 2),
            "nonempty_pct": round(100.0 * nonempty / max(1, len(rows)), 2),
            "mean_completion_chars": round(mean_chars, 1),
            "moderation_blocks_total": sum(1 for r in rows if r.get("blocked_by_moderation")),
        },
        "verification_mmd_hamming": {
            "K5_2v2_10calls_mean20": {
                "auc": round(float(np.mean([x["auc"] for x in k5_2v2_stats])), 4),
                "eer_pct": round(float(np.mean([x["eer_pct"] for x in k5_2v2_stats])), 2),
                "within_family_eer_pct": round(float(np.mean([x["within_family_eer_pct"] for x in k5_2v2_stats])), 2),
            },
            "K10_2v2_20calls": res_2v2,
            "K10_3v3_30calls": res_3v3,
            "K10_5v5_50calls": res_5v5,
            "L_sensitivity": l_sens,
        },
        "verification_mmd_4gram": {
            "K5_2v2_10calls_mean20": {
                "auc": round(float(np.mean([x["auc"] for x in k5_4g_stats])), 4),
                "eer_pct": round(float(np.mean([x["eer_pct"] for x in k5_4g_stats])), 2),
                "within_family_eer_pct": round(float(np.mean([x["within_family_eer_pct"] for x in k5_4g_stats])), 2),
            },
            "K10_2v2_20calls": res_4g_2v2,
            "K10_3v3_30calls": res_4g_3v3,
            "K10_5v5_50calls": res_4g_5v5,
        },
        "permutation_p005": perm_res,
        "mixed_routing": mixed_out,
        "cpu_single_pair_median_ms": round(float(np.median(t_raw)), 3),
        "overhead": {
            "K5_2v2_10calls": summarize_overhead(rows, tids, pricing_by_tid, rep_filter=lambda r: r in (2, 3), prompt_filter=lambda p: p in set(s5b_prompts[:5])),
            "K10_2v2_20calls": summarize_overhead(rows, tids, pricing_by_tid, rep_filter=lambda r: r in (2, 3)),
            "K10_3v3_30calls": summarize_overhead(rows, tids, pricing_by_tid, rep_filter=lambda r: r in (3, 4, 5)),
            "K10_5v5_50calls": summarize_overhead(rows, tids, pricing_by_tid, rep_filter=lambda r: r in (5, 6, 7, 8, 9)),
        },
    }


# ---------------------------------------------------------------------------
# Arm S5c: Same-day HuePrint Anchor + 9-Day Longitudinal S3a -> S5c Transfer
# ---------------------------------------------------------------------------

def analyze_s5c(
    rows: list[dict[str, Any]],
    tids: list[str],
    family_by_tid: dict[str, str],
    pricing_by_tid: dict[str, tuple[float, float]],
    seed: int = 20261120,
) -> dict[str, Any]:
    pos, neg_all, neg_fam = make_family_masks(tids, family_by_tid)

    # First-half (reps 0,1,2) vs second-half (reps 3,4,5) -- identical split geometry to S5a/S5b
    g_first = hp_group([r for r in rows if int(r["rep"]) in (0, 1, 2)])
    g_second = hp_group([r for r in rows if int(r["rep"]) in (3, 4, 5)])
    ids_fh, mats_fh, _ = hp_matrix(g_first, g_second)
    assert ids_fh == sorted(tids)

    # Odd/even split (HuePrint standard)
    g_odd = hp_group([r for r in rows if int(r["rep"]) % 2 == 1])
    g_even = hp_group([r for r in rows if int(r["rep"]) % 2 == 0])
    ids_oe, mats_oe, _ = hp_matrix(g_odd, g_even)

    # Reorder matrices to match `tids` order
    idx_map = [ids_fh.index(t) for t in tids]
    def reorder(m: np.ndarray) -> np.ndarray:
        return m[np.ix_(idx_map, idx_map)]

    # Color MMD-U on same-day S5c 3v3 (first vs second half)
    def color_mmd_u_matrix(ga: dict, gb: dict) -> np.ndarray:
        n = len(tids)
        mat = np.zeros((n, n), dtype=np.float64)
        for i, ti in enumerate(tids):
            for j, tj in enumerate(tids):
                cells = sorted(set(ga[ti]) & set(gb[tj]))
                vals = []
                for c in cells:
                    sa = [r.get("raw_text") or "" for r in ga[ti][c]]
                    sb = [r.get("raw_text") or "" for r in gb[tj][c]]
                    if len(sa) >= 2 and len(sb) >= 2:
                        frac = exact_mmd_u_cell(sa, sb)
                        vals.append(float(frac))
                mat[i, j] = sum(vals) / len(vals)
        return mat

    mat_mmd_fh = color_mmd_u_matrix(g_first, g_second)
    mat_mmd_oe = color_mmd_u_matrix(g_odd, g_even)

    # Jitter +-8 RGB on S5c 3v3 (10 fixed seeds)
    jit_e_eers = []
    jit_mmd_eers = []
    for js in range(20261021, 20261031):
        g_j = jitter_group(g_second, amplitude=8, seed=js, raw=True)
        _, mj, _ = hp_matrix(g_first, g_j)
        jit_e_eers.append(eval_dist_matrix(reorder(mj["energy_reg"]), pos, neg_all, neg_fam)["eer_pct"])
        mmj = color_mmd_u_matrix(g_first, g_j)
        jit_mmd_eers.append(eval_dist_matrix(mmj, pos, neg_all, neg_fam)["eer_pct"])

    # Mixed-routing on S5c 3v3 (30 calls/side, same 5 seeds x 380 ordered pairs x lambda in {0.20, 0.40, 0.50})
    rng_mix = np.random.default_rng(seed + 303)
    mat_e_fh = reorder(mats_fh["energy_reg"])
    pure_g_e = np.diag(mat_e_fh)
    tau_mid_e = hp_thresholds(mat_e_fh)["tau_mid"]
    tau_q95_e = float(np.quantile(pure_g_e, 0.95))
    cells_list = sorted(g_first[tids[0]].keys())

    # Pre-summarize enrollment cells
    enroll_sum = {t: {c: an.summarize_cell_samples(g_first[t][c]) for c in cells_list} for t in tids}
    pair_is_same_fam = np.array(
        [family_by_tid[m] == family_by_tid[r] for _s in range(5) for m in tids for r in tids if r != m],
        dtype=bool,
    )
    mixed_s5c = {}
    for lam in (0.20, 0.40, 0.50):
        mix_scores = []
        for _s in range(5):
            for m in tids:
                for r in tids:
                    if r == m:
                        continue
                    cell_vals = []
                    for c in cells_list:
                        rows_m = g_second[m][c]
                        rows_r = g_second[r][c]
                        k_len = min(len(rows_m), len(rows_r))
                        mask = rng_mix.random(k_len) < lam
                        mixed_rows = [rows_r[k] if mask[k] else rows_m[k] for k in range(k_len)]
                        cs_q = an.summarize_cell_samples(mixed_rows)
                        if enroll_sum[m][c]["n_valid"] and cs_q["n_valid"]:
                            cell_vals.append(an.compute_cell_distance(enroll_sum[m][c], cs_q)["energy_reg"])
                    mix_scores.append(sum(cell_vals) / len(cell_vals))
        ms = np.array(mix_scores, dtype=np.float64)
        roc = an.compute_roc_eer(pure_g_e.tolist(), ms.tolist())
        roc_fam = an.compute_roc_eer(pure_g_e.tolist(), ms[pair_is_same_fam].tolist())
        mixed_s5c[f"{lam:.2f}"] = {
            "auc": round(roc["auc_raw"], 4),
            "eer_pct": round(100.0 * roc["eer_linear_raw"], 2),
            "det_at_tau_mid_pct": round(100.0 * float(np.mean(ms > tau_mid_e)), 2),
            "det_at_q95_fpr5_pct": round(100.0 * float(np.mean(ms > tau_q95_e)), 2),
            "within_family_auc": round(roc_fam["auc_raw"], 4),
            "within_family_det_q95_pct": round(100.0 * float(np.mean(ms[pair_is_same_fam] > tau_q95_e)), 2),
        }

    # Bonus 9-Day Longitudinal OpenRouter Transfer: S3a (2026-11-11) -> S5c (2026-11-20)
    s3_rows, _, _ = load_jsonl_dedup(S3_COLOR_PATH)
    g_s3_6 = hp_group([r for r in s3_rows if int(r["rep"]) < 6])
    g_s3_15 = hp_group([r for r in s3_rows if int(r["rep"]) < 15])
    g_s5c_all = hp_group(rows)

    ids_l6, mats_l6, _ = hp_matrix(g_s3_6, g_s5c_all)
    ids_l15, mats_l15, _ = hp_matrix(g_s3_15, g_s5c_all)
    idx_l6 = [ids_l6.index(t) for t in tids]
    def reord(m: np.ndarray, ix: list[int]) -> np.ndarray:
        return m[np.ix_(ix, ix)]

    mat_mmd_l6 = color_mmd_u_matrix(g_s3_6, g_s5c_all)

    # Compute exact elapsed days between S3a and S5c
    import datetime as dt
    ts_s3 = [dt.datetime.fromisoformat(r["timestamp_utc"].replace("Z", "+00:00")).timestamp() for r in s3_rows]
    ts_s5 = [dt.datetime.fromisoformat(r["timestamp_utc"].replace("Z", "+00:00")).timestamp() for r in rows]
    elapsed_days = (statistics.median(ts_s5) - statistics.median(ts_s3)) / 86400.0

    valid_cnt = sum(1 for r in rows if (r.get("parsed") or {}).get("status") == "valid")
    return {
        "health": {
            "unique_trials": len(rows),
            "http_200_count": sum(1 for r in rows if r.get("http_status") == 200),
            "valid_count": valid_cnt,
            "valid_pct": round(100.0 * valid_cnt / max(1, len(rows)), 2),
            "moderation_blocks_total": sum(1 for r in rows if r.get("blocked_by_moderation")),
        },
        "verification_3v3_30calls": {
            "first_vs_second_half": {
                "energy_reg": eval_dist_matrix(reorder(mats_fh["energy_reg"]), pos, neg_all, neg_fam),
                "hybrid": eval_dist_matrix(reorder(mats_fh["hybrid"]), pos, neg_all, neg_fam),
                "color_mmd_u": eval_dist_matrix(mat_mmd_fh, pos, neg_all, neg_fam),
            },
            "odd_vs_even": {
                "energy_reg": eval_dist_matrix(reorder(mats_oe["energy_reg"]), pos, neg_all, neg_fam),
                "hybrid": eval_dist_matrix(reorder(mats_oe["hybrid"]), pos, neg_all, neg_fam),
                "color_mmd_u": eval_dist_matrix(mat_mmd_oe, pos, neg_all, neg_fam),
            },
            "jitter8_10seeds_mean_eer_pct": {
                "energy_reg": round(float(np.mean(jit_e_eers)), 2),
                "color_mmd_u": round(float(np.mean(jit_mmd_eers)), 2),
            },
        },
        "mixed_routing_3v3_30calls": {
            "tau_mid": round(tau_mid_e, 5),
            "clean_frr_at_tau_mid_pct": round(100.0 * float(np.mean(pure_g_e > tau_mid_e)), 2),
            "by_lambda": mixed_s5c,
        },
        "longitudinal_s3_to_s5c": {
            "elapsed_days_median": round(elapsed_days, 2),
            "6v6": {
                "energy_reg": eval_dist_matrix(reord(mats_l6["energy_reg"], idx_l6), pos, neg_all, neg_fam),
                "hybrid": eval_dist_matrix(reord(mats_l6["hybrid"], idx_l6), pos, neg_all, neg_fam),
                "color_mmd_u": eval_dist_matrix(mat_mmd_l6, pos, neg_all, neg_fam),
            },
            "15v6": {
                "energy_reg": eval_dist_matrix(reord(mats_l15["energy_reg"], idx_l6), pos, neg_all, neg_fam),
                "hybrid": eval_dist_matrix(reord(mats_l15["hybrid"], idx_l6), pos, neg_all, neg_fam),
            },
        },
        "overhead": {
            "3v3_30calls": summarize_overhead(rows, tids, pricing_by_tid, rep_filter=lambda r: r in (3, 4, 5)),
        },
    }


def main() -> None:
    targets = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))["targets"]
    tids = [t["id"] for t in targets]
    family_by_tid = {t["id"]: t["family"] for t in targets}

    pricing_cfg = json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    pricing_by_tid = {
        r["target_id"]: (float(r["pricing"]["prompt"]), float(r["pricing"]["completion"]))
        for r in pricing_cfg["rates"]
    }

    rows_a, lines_a, sha_a = load_jsonl_dedup(DATA_DIR / "s5a_llmmap.jsonl")
    rows_b, lines_b, sha_b = load_jsonl_dedup(DATA_DIR / "s5b_gao_longform.jsonl")
    rows_c, lines_c, sha_c = load_jsonl_dedup(DATA_DIR / "s5c_hueprint_anchor.jsonl")
    llmmap_inf = json.loads((RES_DIR / "s5a_llmmap_inference.json").read_text(encoding="utf-8"))

    res_a = analyze_s5a(rows_a, tids, family_by_tid, pricing_by_tid, llmmap_inf)
    res_b = analyze_s5b(rows_b, tids, family_by_tid, pricing_by_tid)
    res_c = analyze_s5c(rows_c, tids, family_by_tid, pricing_by_tid)

    total_actual_usd = round(
        summarize_overhead(rows_a, tids, pricing_by_tid)["usd_actual_total_20models"]
        + summarize_overhead(rows_b, tids, pricing_by_tid)["usd_actual_total_20models"]
        + summarize_overhead(rows_c, tids, pricing_by_tid)["usd_actual_total_20models"],
        4,
    )

    out = {
        "study": "S5: Head-to-Head Competitor Benchmark on 20 Locked OpenRouter Models (2026-11-20)",
        "cohort_size": len(tids),
        "total_unique_calls": len(rows_a) + len(rows_b) + len(rows_c),
        "total_actual_catalog_usd_all_arms": total_actual_usd,
        "inputs": {
            "s5a_llmmap.jsonl": {"unique_trials": len(rows_a), "raw_lines": lines_a, "sha256": sha_a},
            "s5b_gao_longform.jsonl": {"unique_trials": len(rows_b), "raw_lines": lines_b, "sha256": sha_b},
            "s5c_hueprint_anchor.jsonl": {"unique_trials": len(rows_c), "raw_lines": lines_c, "sha256": sha_c},
        },
        "S5a_LLMmap_OpenSet": res_a,
        "S5b_Gao_LongForm": res_b,
        "S5c_HuePrint_Anchor": res_c,
    }

    RES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RES_DIR / "s5_results.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Compact console report
    print("=" * 72)
    print(f"Study S5 Complete: {out['total_unique_calls']} unique calls (~${total_actual_usd:.3f} catalog USD)")
    print("=" * 72)
    print("\n--- S5a: LLMmap (USENIX Security 2025, Official Open-Set) ---")
    print("Health:", json.dumps(res_a["health"], indent=2))
    print("1v1 (8 calls, mean 3 disjoint):", {k: v for k, v in res_a["verification"]["1v1_8calls_mean_3disjoint"].items() if k != "splits"})
    print("1v1 (8 calls, rep 0v3):", res_a["verification"]["1v1_8calls_rep0v3"])
    print("3v3 (24 calls, rep 012v345):", res_a["verification"]["3v3_24calls_rep012v345"])
    print("Mixed routing:", json.dumps(res_a["mixed_routing"]["by_lambda"], indent=2))
    print("Overhead:", json.dumps(res_a["overhead"], indent=2))
    print("CPU scoring median ms:", res_a["cpu_scoring_median_ms"])

    print("\n--- S5b: Gao et al. (ICLR 2025, Native Long-Form mmd_hamming) ---")
    print("Health:", res_b["health"])
    for k, v in res_b["verification_mmd_hamming"].items():
        print(f"  {k}: {v}")
    print("  4-gram 3v3 / 5v5:", res_b["verification_mmd_4gram"]["K10_3v3_30calls"]["eer_pct"], "/", res_b["verification_mmd_4gram"]["K10_5v5_50calls"]["eer_pct"])
    print("  Permutation p<=0.05:", res_b["permutation_p005"])
    print("  Mixed routing:", json.dumps(res_b["mixed_routing"], indent=2))
    print("  Overhead:", json.dumps(res_b["overhead"], indent=2))

    print("\n--- S5c: Same-Day HuePrint Anchor (3v3 = 30 calls/side) ---")
    print("Health:", res_c["health"])
    print("  First vs second half:", res_c["verification_3v3_30calls"]["first_vs_second_half"])
    print("  Odd vs even:", res_c["verification_3v3_30calls"]["odd_vs_even"])
    print("  Jitter +-8:", res_c["verification_3v3_30calls"]["jitter8_10seeds_mean_eer_pct"])
    print("  Mixed routing:", json.dumps(res_c["mixed_routing_3v3_30calls"], indent=2))
    print("  9-Day Longitudinal S3->S5c:", json.dumps(res_c["longitudinal_s3_to_s5c"], indent=2))
    print("  Overhead:", res_c["overhead"])


if __name__ == "__main__":
    main()
