#!/usr/bin/env python3
"""Offline S3 completion-cap audit, subset reconciliation, and exact rational discrete MMD-U baselines.

Computes from immutable raw JSONL logs (with zero hardcoded numbers and zero network calls):
1. Line-by-line S3 completion-cap (`finish_reason == "length"`, `usage.output_tokens`) vs
   parse-validity audit across `s3a_hueprint_locked64_n30.jsonl` and `s3b_bruckner_locked64_n30.jsonl`.
2. Exact discrete one-hot MMD-U (`T / [h^2(h-1)]` via exact integer/Fraction arithmetic,
   eliminating ~1e-16 floating-point tie splitting in ROC linear EER) across:
   - Table 3 & Fig. 5(a) S3 grid (`N in {6, 10, 20, 30}`, `K in {1, 2, 4, 6, 8, 10}`, clean & 10-seed jitter8),
   - B-20x6 and D matched 40-subset shallow curve (`N=6`, `K in {1, 2, 4, 6, 8, 10}`, clean & 10-seed jitter8)
     and full 20-cell battery (`K=20, N=6`),
   - Formatting-decontaminated canonical `#RRGGBB` vs normalized single-word MMD-U on S3,
   - S1 cross-gateway (6v6) and S2 cross-provider (6v6, 3v3) MMD-U controls.

Verifies SHA-256 protected inputs in `results/integrity_manifest.json` and writes
derived outputs under `results/diagnostics/`.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze as an
from hueprint_audit.baselines import (
    aggregate_exact_mmd_u,
    categorical_permutations,
    cell_subsets,
    exact_mmd_stats,
    exact_mmd_u_cell,
    exact_mmd_u_permutations,
)
from hueprint_audit.core import (
    JITTER_SEEDS,
    SEED,
    cell_scores,
    group,
    jitter_group,
    load,
    pvalue_stats,
    seed_for,
    split,
    stats,
    summarize,
)
from hueprint_audit.experiments import FILES, b20, make_s1

ANALYSIS_DIR = ROOT / "results" / "diagnostics"
DEFAULT_OUT = ANALYSIS_DIR / "subset_mmd_diagnostics.json"
DEFAULT_EXACT_MMD_OUT = ANALYSIS_DIR / "exact_mmd_baselines.json"
PROTECTED_MANIFEST = ROOT / "results" / "integrity_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def offline_guard(event: str, args) -> None:
    if event in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.sendto", "subprocess.Popen"):
        raise RuntimeError("Offline-only analysis blocked event: " + event)


def verify_protected() -> int:
    raw_m = json.loads(PROTECTED_MANIFEST.read_text(encoding="utf-8")); manifest = raw_m["files"] if "files" in raw_m else raw_m
    for rel, expected in manifest.items():
        actual = sha256(ROOT / rel)
        if actual != expected:
            raise RuntimeError(f"Protected file mutated: {rel}")
    return len(manifest)


def audit_s3_raw_logs() -> dict:
    s3_paths = {
        "S3_color": ROOT / "extensions" / "live_validation_20261111" / "data" / "s3a_hueprint_locked64_n30.jsonl",
        "S3_word": ROOT / "extensions" / "live_validation_20261111" / "data" / "s3b_bruckner_locked64_n30.jsonl",
    }
    per_arm = {}
    total_calls = 0
    total_valid = 0
    total_length = 0
    total_length_valid = 0
    for arm, path in s3_paths.items():
        finish_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        length_records = []
        stop_gt_64 = 0
        stop_eq_64 = 0
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_no, raw_line in enumerate(lines, 1):
            rec = json.loads(raw_line)
            fr = str(rec.get("finish_reason"))
            st = str((rec.get("parsed") or {}).get("status"))
            out_tok = (rec.get("usage") or {}).get("output_tokens")
            finish_counts[fr] = finish_counts.get(fr, 0) + 1
            status_counts[st] = status_counts.get(st, 0) + 1
            if fr == "length":
                length_records.append({
                    "line": line_no,
                    "target_id": rec.get("target_id"),
                    "cell": f"{rec.get('task_id')}|{rec.get('lang')}",
                    "rep": rec.get("rep"),
                    "finish_reason": fr,
                    "output_tokens": out_tok,
                    "parsed_status": st,
                })
            elif fr == "stop" and out_tok is not None:
                if out_tok == 64:
                    stop_eq_64 += 1
                elif out_tok > 64:
                    stop_gt_64 += 1
        n_arm = len(lines)
        n_val = status_counts.get("valid", 0)
        n_len = len(length_records)
        n_len_val = sum(1 for r in length_records if r["parsed_status"] == "valid")
        per_arm[arm] = {
            "total_calls": n_arm,
            "valid_parsed": n_val,
            "non_valid_parsed": n_arm - n_val,
            "finish_reason_counts": finish_counts,
            "parsed_status_counts": status_counts,
            "length_limit_count": n_len,
            "length_limit_valid_parsed": n_len_val,
            "length_limit_records": length_records,
            "stop_with_output_tokens_eq_64": stop_eq_64,
            "stop_with_output_tokens_gt_64_thinking_billed": stop_gt_64,
        }
        total_calls += n_arm
        total_valid += n_val
        total_length += n_len
        total_length_valid += n_len_val
    return {
        "total_calls": total_calls,
        "total_valid_parsed": total_valid,
        "total_non_valid_parsed": total_calls - total_valid,
        "total_length_limit_count": total_length,
        "total_length_limit_valid_parsed": total_length_valid,
        "total_length_limit_non_valid_parsed": total_length - total_length_valid,
        "arms": per_arm,
    }


def evaluate_cohort(rows: list[dict], n_total: int, is_color: bool) -> dict:
    chosen = [r for r in rows if r["rep"] <= n_total]
    ref = group([r for r in chosen if r["rep"] % 2])
    qry = group([r for r in chosen if not r["rep"] % 2])
    ids = sorted(set(ref) & set(qry))
    cells = sorted(set.intersection(*(set(ref[t]) & set(qry[t]) for t in ids)))
    m = len(ids)
    k_cells = len(cells)

    raw_mmd_exact = [[Fraction(0, 1) for _ in range(m)] for _ in range(m)]
    can_mmd_exact = [[Fraction(0, 1) for _ in range(m)] for _ in range(m)]
    mat_raw_tv = np.zeros((m, m))
    mat_canon_jsd = np.zeros((m, m))
    mat_energy_reg = np.zeros((m, m)) if is_color else None

    sum_ref = summarize(ref) if is_color else None
    sum_qry = summarize(qry) if is_color else None

    for i, tid in enumerate(ids):
        for j, uid in enumerate(ids):
            raw_mmd_sum = Fraction(0, 1)
            can_mmd_sum = Fraction(0, 1)
            raw_tv_cells, can_jsd_cells, ereg_cells = [], [], []
            for ck in cells:
                xr = [r.get("raw_text") or "" for r in ref[tid][ck]]
                yr = [r.get("raw_text") or "" for r in qry[uid][ck]]
                raw_mmd_sum += exact_mmd_u_cell(xr, yr)
                p_raw = categorical_permutations(xr, yr, 1, 1)
                raw_tv_cells.append(float(p_raw["string_tv"][0]))

                xc = [
                    (r.get("parsed") or {}).get("canonical_hex") or f"__INV_REF_{idx}__"
                    for idx, r in enumerate(ref[tid][ck])
                ]
                yc = [
                    (r.get("parsed") or {}).get("canonical_hex") or f"__INV_QRY_{idx}__"
                    for idx, r in enumerate(qry[uid][ck])
                ]
                can_mmd_sum += exact_mmd_u_cell(xc, yc)

                ca, cb = {}, {}
                for val in xc:
                    if not val.startswith("__INV_"):
                        ca[val] = ca.get(val, 0) + 1
                for val in yc:
                    if not val.startswith("__INV_"):
                        cb[val] = cb.get(val, 0) + 1
                can_jsd_cells.append(float(an.jsd_base2(ca, cb)))

                if is_color and sum_ref is not None and sum_qry is not None:
                    if sum_ref[tid][ck]["n_valid"] > 0 and sum_qry[uid][ck]["n_valid"] > 0:
                        ereg_cells.append(float(cell_scores(sum_ref[tid][ck], sum_qry[uid][ck])["energy_reg"]))

            raw_mmd_exact[i][j] = raw_mmd_sum / k_cells
            can_mmd_exact[i][j] = can_mmd_sum / k_cells
            mat_raw_tv[i, j] = float(np.mean(raw_tv_cells))
            mat_canon_jsd[i, j] = float(np.mean(can_jsd_cells))
            if is_color and mat_energy_reg is not None:
                mat_energy_reg[i, j] = float(np.mean(ereg_cells))

    out = {
        "n_models": m,
        "n_cells": k_cells,
        "n_total_per_cell": n_total,
        "calls_per_side": k_cells * (n_total // 2),
        "raw_mmd_u": exact_mmd_stats(raw_mmd_exact),
        "raw_tv": stats(mat_raw_tv),
        "canonical_mmd_u": exact_mmd_stats(can_mmd_exact),
        "canonical_jsd": stats(mat_canon_jsd),
    }
    if is_color and mat_energy_reg is not None:
        out["energy_reg"] = stats(mat_energy_reg)
    return out


def compute_exact_mmd_baselines(permutations: int = 999) -> dict:
    data = {k: load(FILES[k]) for k in ("B", "D", "E", "S1_CF21", "S1_OR21", "S2", "S3_color", "S3_word")}
    plans = [
        ("S3_color", data["S3_color"], (6, 10, 20, 30)),
        ("S3_word", data["S3_word"], (6, 10, 20, 30)),
        ("B20x6", b20(data["B"]), (6,)),
        ("D", data["D"], (6,)),
    ]
    k_grid = (1, 2, 4, 6, 8, 10)
    grid_rows = []
    for name, source, ns in plans:
        is_color = name in ("S3_color", "B20x6")
        for n in ns:
            chosen = [r for r in source if r["rep"] <= n]
            a = group([r for r in chosen if r["rep"] % 2])
            clean = group([r for r in chosen if not r["rep"] % 2])
            for jitter_seed in (None, *JITTER_SEEDS) if is_color else (None,):
                b = clean if jitter_seed is None else jitter_group(clean, 8, jitter_seed, raw=True)
                ids = sorted(set(a) & set(b))
                cells = sorted(set.intersection(*(set(a[t]) & set(b[t]) for t in ids)))
                nids, ncells = len(ids), len(cells)
                mmd_num = np.zeros((nids, nids, ncells, permutations + 1), dtype=np.int64)
                mmd_den = np.zeros((nids, nids, ncells), dtype=np.int64)
                for i, tid in enumerate(ids):
                    for j, uid in enumerate(ids):
                        for ci, ck in enumerate(cells):
                            x = [r.get("raw_text") or "" for r in a[tid][ck]]
                            y = [r.get("raw_text") or "" for r in b[uid][ck]]
                            num, den, _, _ = exact_mmd_u_permutations(
                                x, y, permutations, seed_for(SEED, "strings", tid, uid, ck, len(x), len(y))
                            )
                            mmd_num[i, j, ci] = num
                            mmd_den[i, j, ci] = den
                condition = "clean" if jitter_seed is None else "jitter8"
                for k in k_grid:
                    subsets = cell_subsets(ncells, k)
                    subset_vals = []
                    for sub in subsets:
                        ix = list(sub)
                        obs_exact, obs_float, pval = aggregate_exact_mmd_u(mmd_num, mmd_den, ix)
                        s = exact_mmd_stats(obs_exact, obs_float)
                        ps = pvalue_stats(pval)
                        subset_vals.append({
                            **s,
                            "p_auc": ps["p_score_roc"]["auc"],
                            "p_eer": ps["p_score_roc"]["eer"],
                            "same_model_rejection_rate": ps["same_model_rejection_rate"],
                            "different_model_rejection_rate": ps["different_model_rejection_rate"],
                        })
                    keys = sorted(subset_vals[0])
                    avg = {key: float(np.mean([v[key] for v in subset_vals])) for key in keys}
                    grid_rows.append({
                        "dataset": name,
                        "n_total_per_cell": n,
                        "n_reference": n // 2,
                        "n_query": n // 2,
                        "K": k,
                        "reference_calls": k * (n // 2),
                        "query_calls": k * (n // 2),
                        "condition": condition,
                        "seed": jitter_seed,
                        "metric": "string_mmd_u",
                        "subset_draws": len(subsets),
                        "permutations": permutations,
                        **avg,
                        "eer_subset_p05": float(np.quantile([v["eer"] for v in subset_vals], 0.05)),
                        "eer_subset_p95": float(np.quantile([v["eer"] for v in subset_vals], 0.95)),
                    })

    cf0, cf21, or21 = make_s1(data)
    s2_meta = {
        r["id"]: r
        for r in json.loads(
            (ROOT / "extensions" / "live_validation_20261111" / "configs" / "targets.s2_multiprovider.json").read_text(encoding="utf-8")
        )["targets"]
    }
    cg_plans = [
        ("S1_CF0_CF21_6v6", cf0, cf21),
        ("S1_CF21_OR21_6v6", cf21, or21),
        ("S1_CF0_OR21_6v6", cf0, or21),
        ("S2_cross_provider_6v6", group(data["S2"]), group(data["S2"])),
        ("S2_cross_provider_3v3", *split(data["S2"])),
    ]
    cg_rows = []
    for scenario, a, b in cg_plans:
        ids = sorted(set(a) & set(b))
        cells = sorted(set.intersection(*(set(a[t]) & set(b[t]) for t in ids)))
        nids, ncells = len(ids), len(cells)
        mmd_num = np.zeros((nids, nids, ncells, permutations + 1), dtype=np.int64)
        mmd_den = np.zeros((nids, nids, ncells), dtype=np.int64)
        for i, tid in enumerate(ids):
            for j, uid in enumerate(ids):
                for ci, ck in enumerate(cells):
                    x = [r.get("raw_text") or "" for r in a[tid][ck]]
                    y = [r.get("raw_text") or "" for r in b[uid][ck]]
                    num, den, _, _ = exact_mmd_u_permutations(
                        x, y, permutations, seed_for(SEED, "strings", tid, uid, ck, len(x), len(y))
                    )
                    mmd_num[i, j, ci] = num
                    mmd_den[i, j, ci] = den
        pos = np.eye(nids, dtype=bool)
        neg = ~pos
        if scenario.startswith("S2"):
            pos = np.array([[t != u and s2_meta[t]["weight_group"] == s2_meta[u]["weight_group"] for u in ids] for t in ids])
            neg = np.array([[s2_meta[t]["weight_group"] != s2_meta[u]["weight_group"] for u in ids] for t in ids])
        obs_exact, obs_float, pval = aggregate_exact_mmd_u(mmd_num, mmd_den, list(range(ncells)))
        s = exact_mmd_stats(obs_exact, obs_float, pos, neg)
        s.pop("top1")
        cg_rows.append({
            "scenario": scenario,
            "metric": "string_mmd_u",
            "cells": ncells,
            "permutations": permutations,
            **s,
            "same_model_rejection_rate": float((pval[pos] <= 0.05).mean()),
            "different_model_rejection_rate": float((pval[neg] <= 0.05).mean()),
        })

    return {
        "protocol": "Exact rational discrete one-hot MMD-U (T / [h^2(h-1)] for equal per-cell sizes h, exact common denominator otherwise), preserving identical odd/even splits, invalid-string retention, probe subsets, and jitter seeds without mutating frozen benchmark baselines.",
        "results": grid_rows,
        "cross_gateway_and_provider_mmd_u": cg_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--exact-mmd-output", type=Path, default=None)
    args = parser.parse_args()
    if args.output.is_dir() or args.output.suffix != ".json":
        diag_out = args.output / "subset_mmd_diagnostics.json"
        exact_out = args.exact_mmd_output or (args.output / "exact_mmd_baselines.json")
    else:
        diag_out = args.output
        exact_out = args.exact_mmd_output or (args.output.parent / "exact_mmd_baselines.json")

    n_protected = verify_protected()
    sys.addaudithook(offline_guard)
    s3_trunc = audit_s3_raw_logs()
    exact_mmd_bundle = compute_exact_mmd_baselines(permutations=999)
    exact_rows = exact_mmd_bundle["results"]
    base_json = json.loads((ROOT / "results" / "benchmark" / "baseline_results.json").read_text(encoding="utf-8"))["results"]

    def subset_k10(ds: str, n: int, metric: str, condition: str = "clean") -> dict:
        source_rows = exact_rows if metric == "string_mmd_u" else base_json
        rows = [
            r for r in source_rows
            if (r["dataset"], r["n_total_per_cell"], r["metric"], r["K"], r["condition"]) == (ds, n, metric, 10, condition)
        ]
        assert rows, (ds, n, metric, condition)
        return {
            "eer": float(statistics.mean(r["eer"] for r in rows)),
            "auc": float(statistics.mean(r["auc"] for r in rows)),
            "subset_draws": rows[0]["subset_draws"],
        }

    b20_rows = b20(load(ROOT / "data" / "exp_40u15r.jsonl"))
    d_rows = load(ROOT / "data" / "exp_bruckner_baseline.jsonl")
    s3_color_rows = load(ROOT / "extensions" / "live_validation_20261111" / "data" / "s3a_hueprint_locked64_n30.jsonl")
    s3_word_rows = load(ROOT / "extensions" / "live_validation_20261111" / "data" / "s3b_bruckner_locked64_n30.jsonl")

    report = {
        "suite": "subset_mmd_v1",
        "protected_files_verified": n_protected,
        "s3_truncation_audit": s3_trunc,
        "b20x6_vs_d_budget_reconciliation": {
            "k10_40subsets_30calls_per_side": {
                "B20x6_color_mmd_u": subset_k10("B20x6", 6, "string_mmd_u"),
                "B20x6_color_mmd_u_jitter8": subset_k10("B20x6", 6, "string_mmd_u", "jitter8"),
                "B20x6_energy_reg": subset_k10("B20x6", 6, "energy_reg"),
                "B20x6_energy_reg_jitter8": subset_k10("B20x6", 6, "energy_reg", "jitter8"),
                "B20x6_hex_jsd": subset_k10("B20x6", 6, "hex_jsd"),
                "D_word_mmd_u": subset_k10("D", 6, "string_mmd_u"),
                "D_word_jsd": subset_k10("D", 6, "word_jsd"),
            },
            "k20_full_battery_60calls_per_side": {
                "B20x6": evaluate_cohort(b20_rows, 6, is_color=True),
                "D": evaluate_cohort(d_rows, 6, is_color=False),
            },
        },
        "s3_canonical_vs_raw_decontamination": {
            f"N={n}": {
                "S3_color": evaluate_cohort(s3_color_rows, n, is_color=True),
                "S3_word": evaluate_cohort(s3_word_rows, n, is_color=False),
            }
            for n in (6, 10, 20, 30)
        },
        "cross_gateway_and_provider_mmd_u": exact_mmd_bundle["cross_gateway_and_provider_mmd_u"],
    }

    verify_protected()
    exact_out.parent.mkdir(parents=True, exist_ok=True)
    exact_out.write_text(json.dumps(exact_mmd_bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    diag_out.parent.mkdir(parents=True, exist_ok=True)
    diag_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "saved_diagnostics": str(diag_out.resolve().relative_to(ROOT)) if diag_out.resolve().is_relative_to(ROOT) else str(diag_out),
        "saved_exact_mmd": str(exact_out.resolve().relative_to(ROOT)) if exact_out.resolve().is_relative_to(ROOT) else str(exact_out),
        "protected_verified": n_protected,
        "s3_length_limited_calls": s3_trunc["total_length_limit_count"],
        "s3_length_limited_valid_parsed": s3_trunc["total_length_limit_valid_parsed"],
        "s3_total_valid_parsed": s3_trunc["total_valid_parsed"],
        "B20x6_K10_40subsets_mmd_eer": report["b20x6_vs_d_budget_reconciliation"]["k10_40subsets_30calls_per_side"]["B20x6_color_mmd_u"]["eer"],
        "D_K10_40subsets_mmd_eer": report["b20x6_vs_d_budget_reconciliation"]["k10_40subsets_30calls_per_side"]["D_word_mmd_u"]["eer"],
        "S3_N6_raw_mmd_color_vs_word": [
            report["s3_canonical_vs_raw_decontamination"]["N=6"]["S3_color"]["raw_mmd_u"]["eer"],
            report["s3_canonical_vs_raw_decontamination"]["N=6"]["S3_word"]["raw_mmd_u"]["eer"],
        ],
        "S3_N6_canon_mmd_color_vs_word": [
            report["s3_canonical_vs_raw_decontamination"]["N=6"]["S3_color"]["canonical_mmd_u"]["eer"],
            report["s3_canonical_vs_raw_decontamination"]["N=6"]["S3_word"]["canonical_mmd_u"]["eer"],
        ],
        "S3_N30_raw_mmd_color_vs_word": [
            report["s3_canonical_vs_raw_decontamination"]["N=30"]["S3_color"]["raw_mmd_u"]["eer"],
            report["s3_canonical_vs_raw_decontamination"]["N=30"]["S3_word"]["raw_mmd_u"]["eer"],
        ],
        "S3_N30_canon_mmd_color_vs_word": [
            report["s3_canonical_vs_raw_decontamination"]["N=30"]["S3_color"]["canonical_mmd_u"]["eer"],
            report["s3_canonical_vs_raw_decontamination"]["N=30"]["S3_word"]["canonical_mmd_u"]["eer"],
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
