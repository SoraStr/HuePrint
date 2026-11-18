#!/usr/bin/env python3
"""
Deterministic Analyzer for Route-A Live-API Expansion Suite (`extensions/live_validation_20261111/`).

Recomputes historical observations using direct RGB geometry and writes separate
RGB results; archived results and their integrity manifest are preserved.

Evaluates four live supplementary studies:
  S1: Real T+21d (~520h / 3-Week) Longitudinal Drift & Cross-Gateway (Cloudflare <-> OpenRouter) Verification (14 models)
  S2: Multi-Provider Open-Weight Backend Disentanglement (6 open-weight models x 3 pinned providers = 18 endpoints across 12 backends)
  S3: Strict Hyperparameter-Locked Apple-to-Apple Parity (20 models across 8 families, uniform T=1.0, max_tokens=64, n=30 [15v15], HuePrint vs Bruckner)
  S4: Implicit Frontend UI/CSS & JSON Stealth Probes + Gateway Input/Output Filter Bypass Evaluation (20 models, S4a CSS/JSON + S4b v5-implicit)
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import analyze as an  # noqa: E402
from reproduce_all import exact_mcnemar_two_sided_p, load_jsonl_clean  # noqa: E402

METRICS_CORE = ["robust_manifold", "energy_reg", "hybrid", "soft_voxel_jsd", "voxel_jsd", "hex_jsd", "side_jsd"]
DEFAULT_DEV_SUMMARY = ROOT / "data/reproduce_all_rgb_summary.json"


def parse_iso_ts(s: str) -> float:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def summarize_dataset_health(rel_path: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, n_lines, sha = load_jsonl_clean(rel_path, apply_legacy_reasoning_meta=False)
    valid_cnt = sum(1 for r in rows if r["parsed"]["status"] == "valid")
    strict_tok_cnt = sum(
        1 for r in rows
        if r["parsed"]["status"] == "valid" and (r["parsed"].get("syntax") or {}).get("strict_single_token_format")
    )
    in_toks = [int((r.get("usage") or {}).get("input_tokens") or 0) for r in rows]
    out_toks = [int((r.get("usage") or {}).get("output_tokens") or 0) for r in rows]
    lats = sorted(float(r.get("latency_ms") or 0.0) for r in rows)
    by_target: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        by_target[r["target_id"]].append(r)

    per_target_valid = {
        tid: round(100.0 * sum(1 for x in trows if x["parsed"]["status"] == "valid") / len(trows), 2)
        for tid, trows in sorted(by_target.items())
    }
    return rows, {
        "path": rel_path,
        "sha256": sha,
        "raw_lines": n_lines,
        "unique_trials": len(rows),
        "n_targets": len(by_target),
        "valid_count": valid_cnt,
        "valid_pct": round(100.0 * valid_cnt / max(1, len(rows)), 2),
        "strict_bare_token_pct_of_valid": round(100.0 * strict_tok_cnt / max(1, valid_cnt), 2),
        "total_input_tokens": sum(in_toks),
        "total_output_tokens": sum(out_toks),
        "mean_output_tokens": round(float(np.mean(out_toks)) if out_toks else 0.0, 2),
        "latency_p50_ms": round(lats[len(lats) // 2], 1) if lats else 0.0,
        "latency_p95_ms": round(lats[min(len(lats) - 1, int(0.95 * len(lats)))], 1) if lats else 0.0,
        "per_target_valid_pct": per_target_valid,
    }


def build_cell_map(
    rows: list[dict[str, Any]],
    target_map: dict[str, str] | None = None,
    rep_filter=None,
    min_valid: int = 1,
) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        if abs(float(r.get("temperature", 1.0)) - 1.0) > 1e-4:
            continue
        if rep_filter is not None and not rep_filter(int(r["rep"])):
            continue
        tid = target_map.get(r["target_id"], r["target_id"]) if target_map else r["target_id"]
        ck = f"{r['task_id']}|{r['lang']}"
        grouped[tid][ck].append(r)

    out: dict[str, dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    for tid, cmap in grouped.items():
        for ck, s_list in cmap.items():
            cs = an.summarize_cell_samples(s_list)
            if cs["n_valid"] >= min_valid:
                out[tid][ck] = cs
    return out


def eval_verification_matrix(
    enroll_map: dict[str, dict[str, dict[str, Any]]],
    query_map: dict[str, dict[str, dict[str, Any]]],
    tids: list[str],
    metrics: list[str] = METRICS_CORE,
    frozen_thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    res: dict[str, Any] = {}
    for m in metrics:
        gen_scores: list[float] = []
        imp_scores: list[float] = []
        top1_hits = 0
        preds: dict[str, dict[str, Any]] = {}
        for q_tid in tids:
            cand_scores: list[tuple[float, str]] = []
            for e_tid in tids:
                sh = sorted(set(enroll_map[e_tid].keys()) & set(query_map[q_tid].keys()))
                if not sh:
                    continue
                d_val = sum(an.compute_cell_distance(enroll_map[e_tid][c], query_map[q_tid][c])[m] for c in sh) / len(sh)
                cand_scores.append((d_val, e_tid))
                if e_tid == q_tid:
                    gen_scores.append(d_val)
                else:
                    imp_scores.append(d_val)
            cand_scores.sort(key=lambda x: x[0])
            best_tid = cand_scores[0][1] if cand_scores else ""
            hit = (best_tid == q_tid)
            if hit:
                top1_hits += 1
            preds[q_tid] = {"pred": best_tid, "hit": hit, "score": cand_scores[0][0] if cand_scores else None}

        roc = an.compute_roc_eer(gen_scores, imp_scores)
        entry: dict[str, Any] = {
            "n_models": len(tids),
            "top1_hits": top1_hits,
            "top1_pct": round(100.0 * top1_hits / max(1, len(tids)), 2),
            "auc": round(roc["auc_raw"], 6),
            "auc_raw": roc["auc_raw"],
            "eer_linear_pct": round(100.0 * roc["eer_linear_raw"], 2),
            "eer_linear_raw": roc["eer_linear_raw"],
            "eer_discrete_pct": round(100.0 * roc["eer_raw"], 2),
            "eer_discrete_raw": roc["eer_raw"],
            "genuine_mean": round(float(np.mean(gen_scores)), 4) if gen_scores else None,
            "impostor_mean": round(float(np.mean(imp_scores)), 4) if imp_scores else None,
            "separability_gap": round(float(np.mean(imp_scores) - np.mean(gen_scores)), 4) if gen_scores and imp_scores else None,
            "predictions": preds,
        }
        if frozen_thresholds and m in frozen_thresholds:
            tau = frozen_thresholds[m]
            frr = 100.0 * sum(1 for g in gen_scores if g > tau) / max(1, len(gen_scores))
            far = 100.0 * sum(1 for im in imp_scores if im <= tau) / max(1, len(imp_scores))
            entry["frozen_tau"] = round(tau, 6)
            entry["frozen_frr_pct"] = round(frr, 2)
            entry["frozen_far_pct"] = round(far, 2)
            entry["frozen_balanced_err_pct"] = round(0.5 * (frr + far), 2)
        res[m] = entry
    return res


def analyze_s1_longitudinal_and_cross_gateway(
    rows_s1a: list[dict[str, Any]],
    rows_s1b: list[dict[str, Any]],
    dev_summary_path: Path = DEFAULT_DEV_SUMMARY,
) -> dict[str, Any]:
    dev_summary_path = Path(dev_summary_path).resolve()
    summary_main = json.loads(dev_summary_path.read_text(encoding="utf-8"))
    if summary_main.get("analysis_protocol") != an.ANALYSIS_PROTOCOL:
        raise ValueError(f"Development thresholds use a different analysis protocol: {dev_summary_path}")
    rows_b, _, _ = load_jsonl_clean("data/exp_40u15r.jsonl", apply_legacy_reasoning_meta=False)
    rows_e, _, _ = load_jsonl_clean("data/exp_heldout_confirm.jsonl", apply_legacy_reasoning_meta=False)

    # Frozen B-20x6 midpoint thresholds from Dataset B
    frozen_tau_b20 = {
        m: summary_main["dataset_E_heldout_confirmation"]["frozen_transfer_from_dev_B"][m]["frozen_dev_midpoint_tau_raw"]
        for m in ["robust_manifold", "energy_reg", "hybrid", "voxel_jsd", "hex_jsd"]
    }

    s1b_cfg = json.loads((EXT_DIR / "configs/targets.s1_or_crossgateway.json").read_text(encoding="utf-8"))["targets"]
    or_to_cf = {t["id"]: t["paired_cf_id"] for t in s1b_cfg}
    tids_14 = sorted({r["target_id"] for r in rows_s1a})
    tids_dev10 = sorted({r["target_id"] for r in rows_b} & set(tids_14))
    tids_held4 = sorted(set(tids_14) - set(tids_dev10))

    # Build T+0 enrollment from Dataset B (en/zh, rep<=6) + Dataset E (en/zh, rep<=6)
    rows_t0 = [
        r for r in (rows_b + rows_e)
        if r["target_id"] in set(tids_14) and r["lang"] in ("en", "zh") and int(r["rep"]) <= 6
    ]

    # Exact wall-clock gap between T+0 and T+21d per model
    gaps_days: dict[str, float] = {}
    for tid in tids_14:
        ts0 = [parse_iso_ts(r["timestamp_utc"]) for r in rows_t0 if r["target_id"] == tid]
        ts1 = [parse_iso_ts(r["timestamp_utc"]) for r in rows_s1a if r["target_id"] == tid]
        if ts0 and ts1:
            gaps_days[tid] = round((statistics.median(ts1) - statistics.median(ts0)) / 86400.0, 2)

    t0_full = build_cell_map(rows_t0, min_valid=2)
    t0_odd = build_cell_map(rows_t0, rep_filter=lambda r: r % 2 == 1, min_valid=1)

    cf21_full = build_cell_map(rows_s1a, min_valid=2)
    cf21_odd = build_cell_map(rows_s1a, rep_filter=lambda r: r % 2 == 1, min_valid=1)
    cf21_even = build_cell_map(rows_s1a, rep_filter=lambda r: r % 2 == 0, min_valid=1)

    or21_full = build_cell_map(rows_s1b, target_map=or_to_cf, min_valid=2)
    or21_odd = build_cell_map(rows_s1b, target_map=or_to_cf, rep_filter=lambda r: r % 2 == 1, min_valid=1)
    or21_even = build_cell_map(rows_s1b, target_map=or_to_cf, rep_filter=lambda r: r % 2 == 0, min_valid=1)

    # Strip verbose predictions dict from summary tables where compact output is preferred
    def compact(mat: dict[str, Any]) -> dict[str, Any]:
        return {m: {k: v for k, v in d.items() if k != "predictions"} for m, d in mat.items()}

    return {
        "frozen_threshold_source": str(dev_summary_path.relative_to(ROOT)) if dev_summary_path.is_relative_to(ROOT) else dev_summary_path.name,
        "frozen_threshold_source_sha256": hashlib.sha256(dev_summary_path.read_bytes()).hexdigest(),
        "n_paired_models": len(tids_14),
        "dev10_models": tids_dev10,
        "heldout4_models": tids_held4,
        "elapsed_days_per_model": gaps_days,
        "elapsed_days_min_median_max": [
            round(min(gaps_days.values()), 2),
            round(statistics.median(gaps_days.values()), 2),
            round(max(gaps_days.values()), 2),
        ],
        "same_session_cf_t21d_3v3": compact(eval_verification_matrix(cf21_odd, cf21_even, tids_14, frozen_thresholds=frozen_tau_b20)),
        "same_session_or_t21d_3v3": compact(eval_verification_matrix(or21_odd, or21_even, tids_14, frozen_thresholds=frozen_tau_b20)),
        "longitudinal_t0_to_t21d_cf_6v6_all14": compact(eval_verification_matrix(t0_full, cf21_full, tids_14, frozen_thresholds=frozen_tau_b20)),
        "longitudinal_t0_to_t21d_cf_6v6_dev10": compact(eval_verification_matrix(t0_full, cf21_full, tids_dev10, frozen_thresholds=frozen_tau_b20)),
        "longitudinal_t0_to_t21d_cf_6v6_heldout4": compact(eval_verification_matrix(t0_full, cf21_full, tids_held4, frozen_thresholds=frozen_tau_b20)),
        "longitudinal_t0_to_t21d_cf_3v3_all14": compact(eval_verification_matrix(t0_odd, cf21_even, tids_14, frozen_thresholds=frozen_tau_b20)),
        "cross_gateway_same_day_cf21_to_or21_6v6_all14": compact(eval_verification_matrix(cf21_full, or21_full, tids_14, frozen_thresholds=frozen_tau_b20)),
        "cross_gateway_and_t21d_cf0_to_or21_6v6_all14": compact(eval_verification_matrix(t0_full, or21_full, tids_14, frozen_thresholds=frozen_tau_b20)),
        "cross_gateway_and_t21d_cf0_to_or21_3v3_all14": compact(eval_verification_matrix(t0_odd, or21_even, tids_14, frozen_thresholds=frozen_tau_b20)),
    }


def analyze_s2_multiprovider(rows_s2: list[dict[str, Any]]) -> dict[str, Any]:
    s2_cfg = json.loads((EXT_DIR / "configs/targets.s2_multiprovider.json").read_text(encoding="utf-8"))["targets"]
    meta_by_id = {t["id"]: t for t in s2_cfg}
    tids_18 = sorted(meta_by_id.keys())

    # Check provider pinning fidelity
    pin_matches = 0
    pin_total = 0
    observed_provs: dict[str, dict[str, int]] = collections.defaultdict(collections.Counter)
    for r in rows_s2:
        tid = r["target_id"]
        exp_p = meta_by_id[tid]["pinned_provider"].lower()
        act_p = str(r.get("provider") or "").lower()
        observed_provs[tid][str(r.get("provider"))] += 1
        pin_total += 1
        if exp_p in act_p or act_p in exp_p:
            pin_matches += 1

    full_map = build_cell_map(rows_s2, min_valid=2)
    odd_map = build_cell_map(rows_s2, rep_filter=lambda r: r % 2 == 1, min_valid=1)
    even_map = build_cell_map(rows_s2, rep_filter=lambda r: r % 2 == 0, min_valid=1)

    metrics_out: dict[str, Any] = {}
    per_weight_group_cross_prov: dict[str, dict[str, float]] = collections.defaultdict(dict)

    for m in METRICS_CORE:
        intra_ep_3v3: list[float] = []
        cross_prov_same_wt_6v6: list[float] = []
        cross_prov_same_wt_3v3: list[float] = []
        diff_wt_6v6: list[float] = []
        diff_wt_3v3: list[float] = []

        for tid in tids_18:
            sh_oe = sorted(set(odd_map[tid].keys()) & set(even_map[tid].keys()))
            if sh_oe:
                intra_ep_3v3.append(sum(an.compute_cell_distance(odd_map[tid][c], even_map[tid][c])[m] for c in sh_oe) / len(sh_oe))

        # Cross-provider model identification: query tid against the remaining 17 endpoints, or rank among endpoints on OTHER providers
        cross_prov_top1_hits_6v6 = 0
        cross_prov_top1_hits_3v3 = 0
        cross_prov_queries = 0

        wt_pair_vals: dict[str, list[float]] = collections.defaultdict(list)
        for q_tid in tids_18:
            q_wt = meta_by_id[q_tid]["weight_group"]
            q_prov = meta_by_id[q_tid]["pinned_provider"]

            cands_6v6: list[tuple[float, str]] = []
            cands_3v3: list[tuple[float, str]] = []
            for e_tid in tids_18:
                if e_tid == q_tid:
                    continue
                e_wt = meta_by_id[e_tid]["weight_group"]
                sh6 = sorted(set(full_map[e_tid].keys()) & set(full_map[q_tid].keys()))
                sh3 = sorted(set(odd_map[e_tid].keys()) & set(even_map[q_tid].keys()))
                if sh6:
                    d6 = sum(an.compute_cell_distance(full_map[e_tid][c], full_map[q_tid][c])[m] for c in sh6) / len(sh6)
                    cands_6v6.append((d6, e_wt))
                    if e_wt == q_wt:
                        cross_prov_same_wt_6v6.append(d6)
                        wt_pair_vals[q_wt].append(d6)
                    else:
                        diff_wt_6v6.append(d6)
                if sh3:
                    d3 = sum(an.compute_cell_distance(odd_map[e_tid][c], even_map[q_tid][c])[m] for c in sh3) / len(sh3)
                    cands_3v3.append((d3, e_wt))
                    if e_wt == q_wt:
                        cross_prov_same_wt_3v3.append(d3)
                    else:
                        diff_wt_3v3.append(d3)

            cross_prov_queries += 1
            cands_6v6.sort(key=lambda x: x[0])
            cands_3v3.sort(key=lambda x: x[0])
            if cands_6v6 and cands_6v6[0][1] == q_wt:
                cross_prov_top1_hits_6v6 += 1
            if cands_3v3 and cands_3v3[0][1] == q_wt:
                cross_prov_top1_hits_3v3 += 1

        roc_6v6 = an.compute_roc_eer(cross_prov_same_wt_6v6, diff_wt_6v6)
        roc_3v3 = an.compute_roc_eer(cross_prov_same_wt_3v3, diff_wt_3v3)
        for wg, vals in wt_pair_vals.items():
            per_weight_group_cross_prov[wg][m] = round(float(np.mean(vals)), 4)

        metrics_out[m] = {
            "tier1_intra_endpoint_3v3_mean": round(float(np.mean(intra_ep_3v3)), 4),
            "tier2_same_weights_cross_provider_6v6_mean": round(float(np.mean(cross_prov_same_wt_6v6)), 4),
            "tier2_same_weights_cross_provider_3v3_mean": round(float(np.mean(cross_prov_same_wt_3v3)), 4),
            "tier3_diff_weights_6v6_mean": round(float(np.mean(diff_wt_6v6)), 4),
            "tier3_diff_weights_3v3_mean": round(float(np.mean(diff_wt_3v3)), 4),
            "provider_drift_ratio_over_intermodel_gap_6v6": round(
                max(0.0, float(np.mean(cross_prov_same_wt_6v6) - np.mean(intra_ep_3v3)))
                / max(1e-6, float(np.mean(diff_wt_6v6) - np.mean(intra_ep_3v3))),
                4,
            ),
            "cross_provider_1nn_weight_hits_6v6": f"{cross_prov_top1_hits_6v6}/{cross_prov_queries}",
            "cross_provider_1nn_weight_pct_6v6": round(100.0 * cross_prov_top1_hits_6v6 / max(1, cross_prov_queries), 2),
            "cross_provider_1nn_weight_hits_3v3": f"{cross_prov_top1_hits_3v3}/{cross_prov_queries}",
            "cross_provider_1nn_weight_pct_3v3": round(100.0 * cross_prov_top1_hits_3v3 / max(1, cross_prov_queries), 2),
            "cross_provider_auc_6v6": round(roc_6v6["auc_raw"], 6),
            "cross_provider_auc_raw_6v6": roc_6v6["auc_raw"],
            "cross_provider_eer_linear_pct_6v6": round(100.0 * roc_6v6["eer_linear_raw"], 2),
            "cross_provider_eer_linear_raw_6v6": roc_6v6["eer_linear_raw"],
            "cross_provider_auc_3v3": round(roc_3v3["auc_raw"], 6),
            "cross_provider_auc_raw_3v3": roc_3v3["auc_raw"],
            "cross_provider_eer_linear_pct_3v3": round(100.0 * roc_3v3["eer_linear_raw"], 2),
            "cross_provider_eer_linear_raw_3v3": roc_3v3["eer_linear_raw"],
        }

    # Also evaluate within-model provider distinguishability (3v3 odd->even across the 3 providers of each model)
    within_wt_prov_top1: dict[str, str] = {}
    for m in ["hex_jsd", "hybrid", "energy_reg", "robust_manifold"]:
        hits = 0
        tot = 0
        for wg in sorted({t["weight_group"] for t in s2_cfg}):
            sub_tids = sorted(t["id"] for t in s2_cfg if t["weight_group"] == wg)
            for q_tid in sub_tids:
                cands = []
                for e_tid in sub_tids:
                    sh = sorted(set(odd_map[e_tid].keys()) & set(even_map[q_tid].keys()))
                    d = sum(an.compute_cell_distance(odd_map[e_tid][c], even_map[q_tid][c])[m] for c in sh) / len(sh)
                    cands.append((d, e_tid))
                cands.sort(key=lambda x: x[0])
                tot += 1
                if cands[0][1] == q_tid:
                    hits += 1
        within_wt_prov_top1[m] = f"{hits}/{tot} ({100.0 * hits / max(1, tot):.1f}%)"

    return {
        "n_endpoints": len(tids_18),
        "n_weight_groups": 6,
        "n_distinct_providers": len({t["pinned_provider"] for t in s2_cfg}),
        "provider_pin_fidelity_pct": round(100.0 * pin_matches / max(1, pin_total), 2),
        "observed_providers_by_endpoint": {k: dict(v) for k, v in sorted(observed_provs.items())},
        "metrics": metrics_out,
        "per_weight_group_cross_provider_6v6_mean": dict(sorted(per_weight_group_cross_prov.items())),
        "within_weight_group_provider_top1_3v3": within_wt_prov_top1,
    }


def analyze_s3_locked_parity(
    rows_hue: list[dict[str, Any]],
    rows_brk: list[dict[str, Any]],
) -> dict[str, Any]:
    tids_20 = sorted({r["target_id"] for r in rows_hue})
    hue_tasks = sorted({f"{r['task_id']}|{r['lang']}" for r in rows_hue})
    brk_tasks = sorted({f"{r['task_id']}|{r['lang']}" for r in rows_brk})

    # Verify strict T=1.0 sent across all trials
    temp_sent_hue_ok = sum(1 for r in rows_hue if r.get("temperature_sent") == 1.0)
    temp_sent_brk_ok = sum(1 for r in rows_brk if r.get("temperature_sent") == 1.0)

    # Diversity per task cell across 20 models x 30 reps = 600 calls
    hue_uniq = []
    for ck in hue_tasks:
        u = {r["parsed"]["canonical_hex"] for r in rows_hue if f"{r['task_id']}|{r['lang']}" == ck and r["parsed"]["status"] == "valid"}
        hue_uniq.append(len(u))
    brk_uniq = []
    for ck in brk_tasks:
        u = {r["parsed"]["canonical_hex"] for r in rows_brk if f"{r['task_id']}|{r['lang']}" == ck and r["parsed"]["status"] == "valid"}
        brk_uniq.append(len(u))

    # Group raw samples by (tid, ck) sorted by rep
    hue_grouped: dict[str, dict[str, list[dict[str, Any]]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows_hue:
        hue_grouped[r["target_id"]][f"{r['task_id']}|{r['lang']}"].append(r)
    brk_grouped: dict[str, dict[str, list[dict[str, Any]]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows_brk:
        brk_grouped[r["target_id"]][f"{r['task_id']}|{r['lang']}"].append(r)

    # Grid over r_split in {3, 5, 10, 15} (total n = 6, 10, 20, 30) and K in {1, 2, 4, 6, 8, 10}
    rng = np.random.default_rng(20261111)
    grid_out: dict[str, Any] = {}
    full_parity_n30_k10: dict[str, Any] = {}

    for r_split in (3, 5, 10, 15):
        max_rep = 2 * r_split
        # Build odd/even cell maps for HuePrint and Bruckner at this r_split
        h_odd: dict[str, dict[str, Any]] = collections.defaultdict(dict)
        h_even: dict[str, dict[str, Any]] = collections.defaultdict(dict)
        b_odd: dict[str, dict[str, Any]] = collections.defaultdict(dict)
        b_even: dict[str, dict[str, Any]] = collections.defaultdict(dict)

        for tid in tids_20:
            for ck in hue_tasks:
                sub = [x for x in hue_grouped[tid][ck] if int(x["rep"]) <= max_rep]
                co = an.summarize_cell_samples([x for x in sub if int(x["rep"]) % 2 == 1])
                ce = an.summarize_cell_samples([x for x in sub if int(x["rep"]) % 2 == 0])
                if co["n_valid"] >= 1 and ce["n_valid"] >= 1:
                    h_odd[tid][ck] = co
                    h_even[tid][ck] = ce
            for ck in brk_tasks:
                sub = [x for x in brk_grouped[tid][ck] if int(x["rep"]) <= max_rep]
                co = an.summarize_cell_samples([x for x in sub if int(x["rep"]) % 2 == 1])
                ce = an.summarize_cell_samples([x for x in sub if int(x["rep"]) % 2 == 0])
                if co["n_valid"] >= 1 and ce["n_valid"] >= 1:
                    b_odd[tid][ck] = co
                    b_even[tid][ck] = ce

        # Precompute cell-level distances for all (e_tid, q_tid) pairs
        h_pair_cells: dict[tuple[str, str], dict[str, dict[str, float]]] = {}
        b_pair_cells: dict[tuple[str, str], dict[str, float]] = {}
        for e_tid in tids_20:
            for q_tid in tids_20:
                sh_h = sorted(set(h_odd[e_tid].keys()) & set(h_even[q_tid].keys()))
                h_pair_cells[(e_tid, q_tid)] = {c: an.compute_cell_distance(h_odd[e_tid][c], h_even[q_tid][c]) for c in sh_h}
                sh_b = sorted(set(b_odd[e_tid].keys()) & set(b_even[q_tid].keys()))
                b_pair_cells[(e_tid, q_tid)] = {
                    c: an.jsd_base2(b_odd[e_tid][c]["hex_counts"], b_even[q_tid][c]["hex_counts"]) for c in sh_b
                }

        grid_out[f"n{max_rep}_{r_split}v{r_split}"] = {}
        for k_tasks in (1, 2, 4, 6, 8, 10):
            n_draws = 1 if k_tasks == 10 else 40
            brk_eers, brk_aucs, brk_top1s = [], [], []
            hue_stats: dict[str, dict[str, list[float]]] = {
                m: {"eer_lin": [], "eer_disc": [], "auc": [], "top1": []}
                for m in ["robust_manifold", "energy_reg", "hybrid", "voxel_jsd", "hex_jsd"]
            }
            last_brk_preds = {}
            last_hue_preds: dict[str, dict[str, Any]] = {}

            for _ in range(n_draws):
                if k_tasks == 10:
                    sel_idx = list(range(10))
                else:
                    sel_idx = sorted(rng.choice(10, size=k_tasks, replace=False).tolist())
                sel_h = [hue_tasks[i] for i in sel_idx]
                sel_b = [brk_tasks[i] for i in sel_idx]

                # Bruckner evaluation on sel_b
                bg, bi = [], []
                b_hits = 0
                b_preds = {}
                for q_tid in tids_20:
                    cands = []
                    for e_tid in tids_20:
                        vals = [b_pair_cells[(e_tid, q_tid)][c] for c in sel_b if c in b_pair_cells[(e_tid, q_tid)]]
                        d = sum(vals) / len(vals) if vals else 1.0
                        cands.append((d, e_tid))
                        if e_tid == q_tid:
                            bg.append(d)
                        else:
                            bi.append(d)
                    cands.sort(key=lambda x: x[0])
                    hit = (cands[0][1] == q_tid)
                    if hit:
                        b_hits += 1
                    b_preds[q_tid] = {"hit": hit, "pred": cands[0][1]}
                broc = an.compute_roc_eer(bg, bi)
                brk_eers.append(100.0 * broc["eer_linear_raw"])
                brk_aucs.append(broc["auc_raw"])
                brk_top1s.append(100.0 * b_hits / len(tids_20))
                last_brk_preds = b_preds

                # HuePrint evaluation on sel_h
                for m in hue_stats:
                    hg, hi = [], []
                    h_hits = 0
                    h_preds = {}
                    for q_tid in tids_20:
                        cands = []
                        for e_tid in tids_20:
                            vals = [h_pair_cells[(e_tid, q_tid)][c][m] for c in sel_h if c in h_pair_cells[(e_tid, q_tid)]]
                            d = sum(vals) / len(vals) if vals else 1.0
                            cands.append((d, e_tid))
                            if e_tid == q_tid:
                                hg.append(d)
                            else:
                                hi.append(d)
                        cands.sort(key=lambda x: x[0])
                        hit = (cands[0][1] == q_tid)
                        if hit:
                            h_hits += 1
                        h_preds[q_tid] = {"hit": hit, "pred": cands[0][1]}
                    hroc = an.compute_roc_eer(hg, hi)
                    hue_stats[m]["eer_lin"].append(100.0 * hroc["eer_linear_raw"])
                    hue_stats[m]["eer_disc"].append(100.0 * hroc["eer_raw"])
                    hue_stats[m]["auc"].append(hroc["auc_raw"])
                    hue_stats[m]["top1"].append(100.0 * h_hits / len(tids_20))
                    last_hue_preds[m] = h_preds

            cell_entry = {
                "bruckner_jsd": {
                    "top1_pct": round(float(np.mean(brk_top1s)), 2),
                    "auc": round(float(np.mean(brk_aucs)), 6),
                    "auc_raw": float(np.mean(brk_aucs)),
                    "eer_linear_pct": round(float(np.mean(brk_eers)), 2),
                    "eer_linear_raw": float(np.mean(brk_eers)) / 100.0,
                },
                "hueprint": {
                    m: {
                        "top1_pct": round(float(np.mean(hue_stats[m]["top1"])), 2),
                        "auc": round(float(np.mean(hue_stats[m]["auc"])), 6),
                        "auc_raw": float(np.mean(hue_stats[m]["auc"])),
                        "eer_linear_pct": round(float(np.mean(hue_stats[m]["eer_lin"])), 2),
                        "eer_linear_raw": float(np.mean(hue_stats[m]["eer_lin"])) / 100.0,
                        "eer_discrete_pct": round(float(np.mean(hue_stats[m]["eer_disc"])), 2),
                        "eer_discrete_raw": float(np.mean(hue_stats[m]["eer_disc"])) / 100.0,
                    }
                    for m in hue_stats
                },
            }
            if k_tasks == 10 and r_split == 15:
                cell_entry["mcnemar_vs_bruckner"] = {
                    m: exact_mcnemar_two_sided_p(last_brk_preds, last_hue_preds[m])
                    for m in hue_stats
                }
                full_parity_n30_k10 = cell_entry
            grid_out[f"n{max_rep}_{r_split}v{r_split}"][f"K{k_tasks}"] = cell_entry

    # Also test +-8 RGB jitter resilience on the 20-model n=30 HuePrint cohort (15v15)
    jit_rng = np.random.default_rng(2026111199)
    h_odd_15 = build_cell_map(rows_hue, rep_filter=lambda r: r % 2 == 1, min_valid=1)
    even_jit_rows = []
    rgb_displacements = []
    for r in rows_hue:
        if int(r["rep"]) % 2 != 0 or r["parsed"]["status"] != "valid":
            continue
        rgb0 = r["parsed"]["rgb"]
        rgb1 = [max(0, min(255, int(rgb0[i]) + int(jit_rng.integers(-8, 9)))) for i in range(3)]
        rgb_displacements.append(float(np.linalg.norm(an.rgb_to_geometry(rgb1) - an.rgb_to_geometry(rgb0))))
        rc = dict(r)
        p_new = dict(r["parsed"])
        p_new["rgb"] = rgb1
        p_new["voxel_bin_8"] = f"{rgb1[0] // 32}_{rgb1[1] // 32}_{rgb1[2] // 32}"
        p_new["canonical_hex"] = f"#{rgb1[0]:02X}{rgb1[1]:02X}{rgb1[2]:02X}"
        rc["parsed"] = p_new
        even_jit_rows.append(rc)
    h_even_15_jit = build_cell_map(even_jit_rows, min_valid=1)
    jitter_20m_n30 = {
        "mean_scaled_rgb_displacement": round(float(np.mean(rgb_displacements)), 6),
        "displacement_units": "Euclidean distance in RGB scaled to [0, 100]^3",
        "rgb_scale": an.RGB_SCALE,
        "metrics": {
            m: {k: v for k, v in d.items() if k != "predictions"}
            for m, d in eval_verification_matrix(
                h_odd_15, h_even_15_jit, tids_20, metrics=["robust_manifold", "energy_reg", "hybrid", "voxel_jsd", "hex_jsd"]
            ).items()
        },
    }

    return {
        "n_models": len(tids_20),
        "temperature_sent_1_0_hueprint_pct": round(100.0 * temp_sent_hue_ok / max(1, len(rows_hue)), 2),
        "temperature_sent_1_0_bruckner_pct": round(100.0 * temp_sent_brk_ok / max(1, len(rows_brk)), 2),
        "inter_model_unique_outputs_per_task_600calls": {
            "bruckner_mean": round(float(np.mean(brk_uniq)), 2),
            "hueprint_mean": round(float(np.mean(hue_uniq)), 2),
            "diversity_ratio_hueprint_over_bruckner": round(float(np.mean(hue_uniq)) / max(1e-6, float(np.mean(brk_uniq))), 2),
        },
        "headline_n30_15v15_K10": full_parity_n30_k10,
        "parity_grid_r_by_K": grid_out,
        "jitter_pm8_on_20models_15v15": jitter_20m_n30,
    }


def analyze_s4_implicit_and_evasion(
    rows_s4_css: list[dict[str, Any]],
    rows_s3_hue: list[dict[str, Any]],
    rows_s4b_v5: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    tids_20 = sorted({r["target_id"] for r in rows_s4_css})

    # Load prompts to test input gateway filters
    p_exp = json.loads((ROOT / "config/prompts.json").read_text(encoding="utf-8"))
    p_brk = json.loads((ROOT / "config/prompts.bruckner_baseline.json").read_text(encoding="utf-8"))
    p_css = json.loads((ROOT / "config/prompts.implicit_css.json").read_text(encoding="utf-8"))
    p_v5 = json.loads((ROOT / "config/prompts.implicit_v5_exact.json").read_text(encoding="utf-8"))

    exp_texts = [f"{p_exp['system_prompts'][t['format']][lg]}\n{t['prompts'][lg]}" for t in p_exp["tasks"].values() for lg in ("en", "zh")]
    brk_texts = [f"{p_brk['system_prompts']['single_word'][lg]}\n{t['prompts'][lg]}" for t in p_brk["tasks"].values() for lg in ("en", "zh")]
    css_texts = [f"{p_css['system_prompts']['hex'][lg]}\n{t['prompts'][lg]}" for t in p_css["tasks"].values() for lg in ("en", "zh")]
    v5_texts = [f"{p_v5['system_prompts'][t['format']][lg]}\n{t['prompts'][lg]}" for t in p_v5["tasks"].values() for lg in ("en", "zh")]

    # Gateway input detectors:
    # 1. Literal format token detector (#RRGGBB or R,G,B)
    lit_re = re.compile(r"#RRGGBB|R\s*,\s*G\s*,\s*B", re.IGNORECASE)
    # 2. Explicit single-token directive detector (catches both explicit HuePrint & Bruckner "Answer with one word/number only" / "Respond with ONLY")
    directive_re = re.compile(
        r"(respond\s+with\s+only|reply\s+with\s+only|answer\s+with\s+one\s+(word|number|letter)\s+only"
        r"|no\s+words,?\s+no\s+explanation|仅回复|仅回答一个|不要包含任何(文字|解释))",
        re.IGNORECASE,
    )
    # 3. Output bare-token response filter: flags responses whose entire trimmed text is just a bare #RRGGBB or R,G,B literal (no CSS/JSON syntax)
    bare_out_re = re.compile(r"^\s*[`'\"]?(#[0-9a-fA-F]{6}|\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3})[`'\".]?\s*$")

    s3_bare_flagged = sum(1 for r in rows_s3_hue if bare_out_re.match(r.get("raw_text") or ""))
    s4_bare_flagged = sum(1 for r in rows_s4_css if bare_out_re.match(r.get("raw_text") or ""))
    s4_valid_and_bypassed = sum(
        1 for r in rows_s4_css
        if r["parsed"]["status"] == "valid" and not bare_out_re.match(r.get("raw_text") or "")
    )

    odd_css = build_cell_map(rows_s4_css, rep_filter=lambda r: r % 2 == 1, min_valid=1)
    even_css = build_cell_map(rows_s4_css, rep_filter=lambda r: r % 2 == 0, min_valid=1)
    verif_s4a = {
        m: {k: v for k, v in d.items() if k != "predictions"}
        for m, d in eval_verification_matrix(odd_css, even_css, tids_20).items()
    }

    out: dict[str, Any] = {
        "n_models": len(tids_20),
        "gateway_filter_evasion": {
            "input_literal_format_detector_flag_rate_pct": {
                "explicit_hueprint_20": round(100.0 * sum(1 for x in exp_texts if lit_re.search(x)) / len(exp_texts), 2),
                "implicit_css_json_16": round(100.0 * sum(1 for x in css_texts if lit_re.search(x)) / len(css_texts), 2),
                "implicit_v5_exact_16": round(100.0 * sum(1 for x in v5_texts if lit_re.search(x)) / len(v5_texts), 2),
            },
            "input_explicit_directive_detector_flag_rate_pct": {
                "explicit_hueprint_20": round(100.0 * sum(1 for x in exp_texts if directive_re.search(x)) / len(exp_texts), 2),
                "explicit_bruckner_20": round(100.0 * sum(1 for x in brk_texts if directive_re.search(x)) / len(brk_texts), 2),
                "implicit_css_json_16": round(100.0 * sum(1 for x in css_texts if directive_re.search(x)) / len(css_texts), 2),
                "implicit_v5_exact_16": round(100.0 * sum(1 for x in v5_texts if directive_re.search(x)) / len(v5_texts), 2),
            },
            "output_bare_color_detector_flag_rate_pct": {
                "s3_explicit_hueprint_responses": round(100.0 * s3_bare_flagged / max(1, len(rows_s3_hue)), 2),
                "s4a_implicit_css_json_responses": round(100.0 * s4_bare_flagged / max(1, len(rows_s4_css)), 2),
            },
            "s4a_implicit_css_json_input_bypass_pct": round(
                100.0 * sum(1 for x in css_texts if not lit_re.search(x) and not directive_re.search(x)) / len(css_texts), 2
            ),
            "s4a_implicit_css_json_output_bypass_pct": round(100.0 * (1.0 - s4_bare_flagged / max(1, len(rows_s4_css))), 2),
            "s4a_joint_valid_and_unflagged_yield_pct": round(100.0 * s4_valid_and_bypassed / max(1, len(rows_s4_css)), 2),
        },
        "s4a_within_implicit_css_5v5_verification": verif_s4a,
    }

    if rows_s4b_v5:
        odd_v5 = build_cell_map(rows_s4b_v5, rep_filter=lambda r: r % 2 == 1, min_valid=1)
        even_v5 = build_cell_map(rows_s4b_v5, rep_filter=lambda r: r % 2 == 0, min_valid=1)
        full_v5_en = build_cell_map([r for r in rows_s4b_v5 if r["lang"] == "en"], min_valid=2)
        s3_en_rep6 = build_cell_map([r for r in rows_s3_hue if int(r["rep"]) <= 6], min_valid=2)
        out["s4b_within_v5_implicit_3v3_verification"] = {
            m: {k: v for k, v in d.items() if k != "predictions"}
            for m, d in eval_verification_matrix(odd_v5, even_v5, tids_20).items()
        }
        out["s4b_cross_phrasing_s3_explicit_to_s4b_implicit_en8_6v6"] = {
            m: {k: v for k, v in d.items() if k != "predictions"}
            for m, d in eval_verification_matrix(s3_en_rep6, full_v5_en, tids_20).items()
        }

    return out


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=EXT_DIR / "lv_rgb_results.json",
        help="Destination for the recomputed RGB results; archived results are protected.",
    )
    parser.add_argument(
        "--dev-summary", type=Path, default=DEFAULT_DEV_SUMMARY,
        help="RGB development report supplying frozen thresholds under the same analysis protocol.",
    )
    parser.add_argument(
        "--manifest", type=Path,
        help="Destination for a separate input/source/output SHA-256 manifest.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    out_path = args.output.resolve()
    manifest_path = (
        args.manifest.resolve() if args.manifest else out_path.with_name(
            "lv_rgb_integrity_manifest.json" if out_path.name == "lv_rgb_results.json"
            else f"{out_path.stem}_manifest.json"
        )
    )
    dev_summary_path = args.dev_summary.resolve()
    protected_outputs = {
        (EXT_DIR / "lv_results.json").resolve(),
        (EXT_DIR / "integrity_manifest.json").resolve(),
        (EXT_DIR / "REPORT.md").resolve(),
    }
    if out_path in protected_outputs or manifest_path in protected_outputs:
        parser.error("Archived results and integrity_manifest.json must not be overwritten.")
    if out_path == manifest_path or dev_summary_path in {out_path, manifest_path}:
        parser.error("Result, manifest, and development summary paths must be distinct.")
    summary_main = json.loads(dev_summary_path.read_text(encoding="utf-8"))
    if summary_main.get("analysis_protocol") != an.ANALYSIS_PROTOCOL:
        parser.error("The development summary must use the current RGB analysis protocol.")
    datasets = {
        "s1a_cf_t21d": "extensions/live_validation_20261111/data/s1a_cf_t21d.jsonl",
        "s1b_or_crossgateway": "extensions/live_validation_20261111/data/s1b_or_crossgateway.jsonl",
        "s2_multiprovider": "extensions/live_validation_20261111/data/s2_multiprovider.jsonl",
        "s3a_hueprint_locked64_n30": "extensions/live_validation_20261111/data/s3a_hueprint_locked64_n30.jsonl",
        "s3b_bruckner_locked64_n30": "extensions/live_validation_20261111/data/s3b_bruckner_locked64_n30.jsonl",
        "s4_implicit_css": "extensions/live_validation_20261111/data/s4_implicit_css.jsonl",
    }
    s4b_rel = "extensions/live_validation_20261111/data/s4b_implicit_v5_exact.jsonl"
    if (ROOT / s4b_rel).is_file():
        datasets["s4b_implicit_v5_exact"] = s4b_rel

    # Record the actual dependencies and reject destinations that would overwrite them.
    manifest_inputs = {ROOT / rel for rel in datasets.values()}
    manifest_inputs.update(EXT_DIR.joinpath("configs").glob("*.json"))
    manifest_inputs.update({
        Path(__file__).resolve(), ROOT / "analyze.py", ROOT / "collect.py", ROOT / "reproduce_all.py",
        ROOT / "data/exp_40u15r.jsonl", ROOT / "data/exp_heldout_confirm.jsonl",
        ROOT / "config/prompts.json", ROOT / "config/prompts.bruckner_baseline.json",
        ROOT / "config/prompts.implicit_css.json", ROOT / "config/prompts.implicit_v5_exact.json",
        dev_summary_path,
    })
    input_paths = {p.resolve() for p in manifest_inputs}
    if out_path in input_paths or manifest_path in input_paths:
        parser.error("Result and manifest destinations must not overwrite analysis inputs or sources.")

    loaded: dict[str, list[dict[str, Any]]] = {}
    health: dict[str, Any] = {}
    for key, rel in datasets.items():
        rows, h = summarize_dataset_health(rel)
        loaded[key] = rows
        health[key] = h

    latest_ts = max((r.get("timestamp_utc", r.get("ts_utc", "")) for rows in loaded.values() for r in rows), default="")
    results = {
        "analysis_protocol_version": "lv_rgb_v2.0_20261111",
        "analysis_protocol": dict(an.ANALYSIS_PROTOCOL),
        "latest_trial_utc": latest_ts,
        "total_live_trials": sum(h["unique_trials"] for h in health.values()),
        "dataset_health": health,
        "S1_longitudinal_t21d_and_cross_gateway": analyze_s1_longitudinal_and_cross_gateway(
            loaded["s1a_cf_t21d"], loaded["s1b_or_crossgateway"], dev_summary_path
        ),
        "S2_multiprovider_disentanglement": analyze_s2_multiprovider(loaded["s2_multiprovider"]),
        "S3_locked_hyperparameter_parity_n30": analyze_s3_locked_parity(
            loaded["s3a_hueprint_locked64_n30"], loaded["s3b_bruckner_locked64_n30"]
        ),
        "S4_implicit_stealth_and_filter_evasion": analyze_s4_implicit_and_evasion(
            loaded["s4_implicit_css"],
            loaded["s3a_hueprint_locked64_n30"],
            loaded.get("s4b_implicit_v5_exact"),
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Hash actual inputs and current analysis sources, without rewriting the archive.
    manifest_inputs.add(out_path)
    manifest_hashes = {}
    for p in sorted(manifest_inputs):
        rel = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name
        if rel in manifest_hashes:
            raise ValueError(f"Manifest path label is ambiguous: {rel}")
        manifest_hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"analysis_protocol": dict(an.ANALYSIS_PROTOCOL), "total_files": len(manifest_hashes), "sha256": manifest_hashes}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[lv_analyze] Wrote {out_path} ({results['total_live_trials']} total live trials)")


if __name__ == "__main__":
    main()
