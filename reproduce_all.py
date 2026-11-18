#!/usr/bin/env python3
"""
Rebuild the main RGB-only analysis from raw JSONL files and source configs.

Geometry uses scaled encoded RGB coordinates (100 * RGB / 255), not a
perceptual color transform. Historical results are retained in their original
report; this entrypoint writes data/reproduce_all_rgb_summary.json by default.

Recomputes provenance, five-dataset verification and family attribution,
query-budget and (n, k) grids, cross-session/paraphrase comparisons, frozen
Dev-to-heldout thresholds, jitter/quantization/replay/routing attacks, and
prompt-filter benchmarks. Perturbation sizes are Euclidean displacements in
scaled RGB units, not perceptual color differences. Discrete and linear EER
fields retain their explicitly named estimands; linear EER uses unrounded ROC
intersections before final report formatting.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import random
import re
import statistics
from pathlib import Path
from typing import Any

import numpy as np

import analyze as an
from collect import parse_color_response

ROOT = Path(__file__).resolve().parent
METRICS_ALL = [
    "robust_manifold",
    "energy_reg",
    "soft_voxel_jsd",
    "hybrid",
    "voxel_jsd",
    "hex_jsd",
    "energy_norm",
    "w2_norm",
    "side_jsd",
]
ATTACK_METRICS = ["robust_manifold", "energy_reg", "hybrid", "voxel_jsd", "hex_jsd"]


def sha256_file(rel_path: str) -> str:
    return hashlib.sha256((ROOT / rel_path).read_bytes()).hexdigest()


def load_jsonl_clean(rel_path: str, apply_legacy_reasoning_meta: bool = False) -> tuple[list[dict[str, Any]], int, str]:
    p = Path(rel_path) if Path(rel_path).is_absolute() else (ROOT / rel_path)
    raw_bytes = p.read_bytes()
    sha = hashlib.sha256(raw_bytes).hexdigest()
    lines = raw_bytes.decode("utf-8").splitlines()
    seen: dict[str, tuple[Any, ...]] = {}
    rows: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        obj = json.loads(line)
        tk = obj.get("trial_key")
        if not isinstance(tk, str) or not tk.strip():
            raise ValueError(f"Missing or invalid trial_key in {rel_path}: {tk!r}")
        rep_val = obj.get("rep")
        if not isinstance(rep_val, int) or isinstance(rep_val, bool) or rep_val < 1:
            raise ValueError(f"Invalid rep field (must be positive int) in {rel_path}: {rep_val!r}")
        old_p = obj.get("parsed") or {}
        if old_p.get("parser_version") not in (None, "2.1", "3.0"):
            raise ValueError(f"Unsupported parser_version in {rel_path}: {old_p.get('parser_version')!r}")
        sig = (
            obj.get("target_id"),
            obj.get("task_id"),
            obj.get("lang"),
            obj.get("format"),
            obj.get("condition"),
            rep_val,
            obj.get("temperature"),
            obj.get("raw_text"),
            obj.get("explicit_reasoning"),
            obj.get("response_id"),
        )
        if tk in seen:
            if seen[tk] != sig:
                raise ValueError(f"Conflicting duplicate trial_key in {rel_path}: {tk}")
            continue
        seen[tk] = sig
        new_p = parse_color_response(
            raw_text=obj.get("raw_text", ""),
            expected_format=obj.get("format", "hex"),
            explicit_reasoning=obj.get("explicit_reasoning", ""),
        )
        if apply_legacy_reasoning_meta:
            leg = obj.get("legacy_reasoning_meta") or old_p
            if not obj.get("explicit_reasoning") and leg.get("has_reasoning_trace"):
                new_p = dict(new_p)
                new_p["has_reasoning_trace"] = True
                new_p["reasoning_char_len"] = leg.get("reasoning_char_len", 0)
                new_p["first_think_word"] = leg.get("first_think_word")
        obj["parsed"] = new_p
        rows.append(obj)
    return rows, len(lines), sha


def exact_mcnemar_two_sided_p(preds_base: dict[str, Any], preds_alt: dict[str, Any]) -> dict[str, Any]:
    """Compute exact binomial two-sided McNemar test dynamically from per-model predictions."""
    keys = sorted(set(preds_base.keys()) & set(preds_alt.keys()))
    b01 = sum(1 for k in keys if (not preds_base[k]["hit"]) and preds_alt[k]["hit"])
    b10 = sum(1 for k in keys if preds_base[k]["hit"] and (not preds_alt[k]["hit"]))
    n = b01 + b10
    if n == 0:
        p_val = 1.0
    else:
        k_min = min(b01, b10)
        tail = sum(math.comb(n, i) for i in range(k_min + 1)) / (2 ** n)
        p_val = min(1.0, 2.0 * tail)
    return {
        "n_evaluated": len(keys),
        "improved_count_b01": b01,
        "regressed_count_b10": b10,
        "discordant_n": n,
        "exact_two_sided_p": round(p_val, 6),
    }


def evaluate_cohort(
    rows: list[dict[str, Any]],
    fmap: dict[str, Any],
    min_cell_full: int = 4,
    min_split: int = 2,
    metrics: list[str] = METRICS_ALL,
) -> dict[str, Any]:
    by_tc: dict[str, dict[str, list[dict[str, Any]]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    cells_set: set[str] = set()
    for r in rows:
        if abs(float(r.get("temperature", 1.0)) - 1.0) < 1e-4:
            ck = f"{r['task_id']}|{r['lang']}"
            by_tc[r["target_id"]][ck].append(r)
            cells_set.add(ck)

    tids = sorted(by_tc.keys())
    all_cells = sorted(cells_set)
    full_c: dict[str, dict[str, Any]] = collections.defaultdict(dict)
    odd_c: dict[str, dict[str, Any]] = collections.defaultdict(dict)
    even_c: dict[str, dict[str, Any]] = collections.defaultdict(dict)

    for t in tids:
        for c in all_cells:
            c_rows = by_tc[t][c]
            cf = an.summarize_cell_samples(c_rows)
            if cf["n_valid"] >= min_cell_full:
                full_c[t][c] = cf
            co = an.summarize_cell_samples([r for r in c_rows if int(r["rep"]) % 2 == 1])
            ce = an.summarize_cell_samples([r for r in c_rows if int(r["rep"]) % 2 == 0])
            if co["n_valid"] >= min_split and ce["n_valid"] >= min_split:
                odd_c[t][c] = co
                even_c[t][c] = ce

    gen_m: dict[str, list[float]] = collections.defaultdict(list)
    imp_raw: dict[str, list[float]] = collections.defaultdict(list)
    imp_cross_sub: dict[str, list[float]] = collections.defaultdict(list)
    imp_cross_fam: dict[str, list[float]] = collections.defaultdict(list)
    gen_cells: dict[str, list[dict[str, float]]] = {m: [] for m in metrics}
    imp_cells: dict[str, list[dict[str, float]]] = {m: [] for m in metrics}
    directed_pairs: list[dict[str, Any]] = []

    for t in tids:
        sh = sorted(set(odd_c[t].keys()) & set(even_c[t].keys()))
        if not sh:
            continue
        cd = {c: an.compute_cell_distance(odd_c[t][c], even_c[t][c]) for c in sh}
        for m in metrics:
            gen_m[m].append(sum(cd[c][m] for c in sh) / len(sh))
            gen_cells[m].append({c: cd[c][m] for c in sh})

    for i, ta in enumerate(tids):
        for j, tb in enumerate(tids):
            if i == j:
                continue
            sh = sorted(set(odd_c[ta].keys()) & set(even_c[tb].keys()))
            if not sh:
                continue
            cd = {c: an.compute_cell_distance(odd_c[ta][c], even_c[tb][c]) for c in sh}
            sub_a = (fmap.get(ta) or {}).get("sublineage", ta)
            sub_b = (fmap.get(tb) or {}).get("sublineage", tb)
            fam_a = (fmap.get(ta) or {}).get("family", ta)
            fam_b = (fmap.get(tb) or {}).get("family", tb)
            pair_scores = {}
            for m in metrics:
                val = sum(cd[c][m] for c in sh) / len(sh)
                pair_scores[m] = val
                imp_raw[m].append(val)
                imp_cells[m].append({c: cd[c][m] for c in sh})
                if sub_a != sub_b:
                    imp_cross_sub[m].append(val)
                if fam_a != fam_b:
                    imp_cross_fam[m].append(val)
            directed_pairs.append({"reference_odd": ta, "query_even": tb, "scores": pair_scores})

    fam_counts = collections.Counter(
        (fmap.get(t) or {}).get("family", t) for t in tids if not (fmap.get(t) or {}).get("is_singleton", True)
    )
    loo_family: dict[str, Any] = {}
    for m in metrics:
        correct, tot = 0, 0
        per_model_pred = {}
        for i, ta in enumerate(tids):
            info_a = fmap.get(ta) or {}
            if info_a.get("is_singleton", True) or fam_counts[info_a.get("family")] < 2:
                continue
            tot += 1
            best_d, best_tb = 999.0, None
            for j, tb in enumerate(tids):
                if i == j:
                    continue
                sh = sorted(set(full_c[ta].keys()) & set(full_c[tb].keys()))
                if not sh:
                    continue
                d_val = sum(an.compute_cell_distance(full_c[ta][c], full_c[tb][c])[m] for c in sh) / len(sh)
                if d_val < best_d:
                    best_d, best_tb = d_val, tb
            hit = (best_tb is not None and (fmap.get(best_tb) or {}).get("family") == info_a.get("family"))
            if hit:
                correct += 1
            per_model_pred[ta] = {"nearest": best_tb, "dist": round(best_d, 4), "hit": hit}
        loo_family[m] = {
            "correct": correct,
            "total": tot,
            "accuracy_pct": round(100.0 * correct / max(1, tot), 2),
            "predictions": per_model_pred,
        }

    return {
        "targets_count": len(tids),
        "cells_count": len(all_cells),
        "n_genuine": len(gen_m[metrics[0]]),
        "n_impostor_raw": len(imp_raw[metrics[0]]),
        "n_impostor_cross_sublineage": len(imp_cross_sub[metrics[0]]),
        "n_impostor_cross_family": len(imp_cross_fam[metrics[0]]),
        "roc_raw": {m: an.compute_roc_eer(gen_m[m], imp_raw[m]) for m in metrics},
        "roc_cross_sublineage": {m: an.compute_roc_eer(gen_m[m], imp_cross_sub[m]) for m in metrics},
        "roc_cross_family": {m: an.compute_roc_eer(gen_m[m], imp_cross_fam[m]) for m in metrics},
        "loo_family": loo_family,
        "gen_scores": dict(gen_m),
        "imp_scores": dict(imp_raw),
        "gen_cells": gen_cells,
        "imp_cells": imp_cells,
        "all_cells": all_cells,
        "directed_impostor_pairs": directed_pairs,
    }


def compute_2d_grid_b(rows_b: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute full 2D (n_reps x k_units) ablation grid on Dataset B (both discrete and tie-stabilized linear EER)."""
    n_list = [4, 6, 8, 10, 12, 15]
    k_list = [1, 2, 4, 8, 16, 24, 32, 40]
    tids = sorted({r["target_id"] for r in rows_b})
    all_cells = sorted({f"{r['task_id']}|{r['lang']}" for r in rows_b})
    by_tc: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows_b:
        by_tc[r["target_id"], f"{r['task_id']}|{r['lang']}"].append(r)

    grid_out: dict[str, Any] = {"full_depth_by_n": {}, "grid_hybrid": {}}
    for n in n_list:
        odd_c: dict[str, dict[str, Any]] = collections.defaultdict(dict)
        even_c: dict[str, dict[str, Any]] = collections.defaultdict(dict)
        for t in tids:
            for c in all_cells:
                sub = [r for r in by_tc[t, c] if int(r["rep"]) <= n]
                co = an.summarize_cell_samples([r for r in sub if int(r["rep"]) % 2 == 1])
                ce = an.summarize_cell_samples([r for r in sub if int(r["rep"]) % 2 == 0])
                if co["n_valid"] >= 1 and ce["n_valid"] >= 1:
                    odd_c[t][c] = co
                    even_c[t][c] = ce

        gen_m: dict[str, list[float]] = collections.defaultdict(list)
        imp_m: dict[str, list[float]] = collections.defaultdict(list)
        gen_hyb: list[dict[str, float]] = []
        imp_hyb: list[dict[str, float]] = []
        for t in tids:
            sh = sorted(set(odd_c[t].keys()) & set(even_c[t].keys()))
            cd = {c: an.compute_cell_distance(odd_c[t][c], even_c[t][c]) for c in sh}
            gen_hyb.append({c: cd[c]["hybrid"] for c in sh})
            for m in ATTACK_METRICS:
                gen_m[m].append(sum(cd[c][m] for c in sh) / len(sh))
        for i, ta in enumerate(tids):
            for j, tb in enumerate(tids):
                if i == j:
                    continue
                sh = sorted(set(odd_c[ta].keys()) & set(even_c[tb].keys()))
                cd = {c: an.compute_cell_distance(odd_c[ta][c], even_c[tb][c]) for c in sh}
                imp_hyb.append({c: cd[c]["hybrid"] for c in sh})
                for m in ATTACK_METRICS:
                    imp_m[m].append(sum(cd[c][m] for c in sh) / len(sh))

        grid_out["full_depth_by_n"][str(n)] = {m: an.compute_roc_eer(gen_m[m], imp_m[m]) for m in ATTACK_METRICS}
        rng = random.Random(42)
        row_k = {}
        for k in k_list:
            eers_disc, eers_lin, eers_12dp_lin = [], [], []
            trials = 1 if k == 40 else 200
            for _ in range(trials):
                subset = all_cells if k == 40 else rng.sample(all_cells, k)
                g_s = [sum(row[c] for c in subset if c in row) / len(subset) for row in gen_hyb]
                i_s = [sum(row[c] for c in subset if c in row) / len(subset) for row in imp_hyb]
                r_raw = an.compute_roc_eer(g_s, i_s)
                r_12 = an.compute_roc_eer([round(x, 12) for x in g_s], [round(x, 12) for x in i_s])
                eers_disc.append(r_raw["eer"])
                eers_lin.append(r_raw["eer_linear_raw"])
                eers_12dp_lin.append(r_12["eer_linear_raw"])
            eers_sorted = sorted(eers_disc)
            row_k[str(k)] = {
                "mean_discrete_eer_pct": round(100.0 * statistics.mean(eers_disc), 2),
                "mean_linear_eer_pct": round(100.0 * statistics.mean(eers_lin), 2),
                "tie_stable_12dp_linear_eer_pct": round(100.0 * statistics.mean(eers_12dp_lin), 2),
                "p05_discrete_eer_pct": round(100.0 * eers_sorted[max(0, int(0.05 * len(eers_sorted)))], 2),
                "p95_discrete_eer_pct": round(100.0 * eers_sorted[min(len(eers_sorted) - 1, int(0.95 * len(eers_sorted)))], 2),
            }
        grid_out["grid_hybrid"][str(n)] = row_k
    return grid_out

def rgb_displacement(before: dict[str, Any], after: dict[str, Any]) -> float:
    """Euclidean displacement in 100 * encoded-RGB / 255 coordinate units."""
    return float(np.linalg.norm(
        an.rgb_to_geometry(before["parsed"]["rgb"])
        - an.rgb_to_geometry(after["parsed"]["rgb"])
    ))


def perturb_row_rgb(r: dict[str, Any], mode: str, param: int, rng: np.random.Generator) -> dict[str, Any]:
    p = dict(r["parsed"])
    if p.get("status") != "valid" or not p.get("rgb"):
        return r
    rgb = np.array(p["rgb"], dtype=int)
    if mode == "uniform_jitter" and param > 0:
        rgb = np.clip(rgb + rng.integers(-param, param + 1, size=3), 0, 255)
    elif mode == "directional_shift" and param != 0:
        rgb = np.clip(rgb + param, 0, 255)
    elif mode == "palette_quant":
        rgb = np.clip(np.round(rgb / param) * param, 0, 255).astype(int)
    r_val, g_val, b_val = int(rgb[0]), int(rgb[1]), int(rgb[2])
    p["rgb"] = [r_val, g_val, b_val]
    p.pop("lab", None)  # Discard optional archived derived coordinates.
    p["voxel_bin_8"] = f"{r_val // 32}_{g_val // 32}_{b_val // 32}"
    p["canonical_hex"] = f"#{r_val:02X}{g_val:02X}{b_val:02X}"
    out = dict(r)
    out["parsed"] = p
    return out


def run_attack_suite(rows: list[dict[str, Any]], max_rep: int) -> dict[str, Any]:
    sub = [r for r in rows if int(r["rep"]) <= max_rep]
    tids = sorted({r["target_id"] for r in sub})
    cells = sorted({f"{r['task_id']}|{r['lang']}" for r in sub})
    odd_group: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    even_group: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for r in sub:
        ck = f"{r['task_id']}|{r['lang']}"
        if int(r["rep"]) % 2 == 1:
            odd_group[r["target_id"], ck].append(r)
        else:
            even_group[r["target_id"], ck].append(r)

    odd_sum = {(t, c): an.summarize_cell_samples(odd_group[t, c]) for t in tids for c in cells}

    def eval_even(even_sum_dict: dict[tuple[str, str], dict[str, Any]], rgb_displacements: list[float]) -> dict[str, Any]:
        gen_s = {m: [] for m in ATTACK_METRICS}
        imp_s = {m: [] for m in ATTACK_METRICS}
        for i, ta in enumerate(tids):
            for j, tb in enumerate(tids):
                sh = [c for c in cells if odd_sum[ta, c]["n_valid"] >= 1 and even_sum_dict[tb, c]["n_valid"] >= 1]
                cd = [an.compute_cell_distance(odd_sum[ta, c], even_sum_dict[tb, c]) for c in sh]
                for m in ATTACK_METRICS:
                    v = sum(d[m] for d in cd) / len(cd)
                    if i == j:
                        gen_s[m].append(v)
                    else:
                        imp_s[m].append(v)
        mean_displacement_raw = float(np.mean(rgb_displacements)) if rgb_displacements else 0.0
        return {
            "gen_s": gen_s,
            "imp_s": imp_s,
            "roc": {m: an.compute_roc_eer(gen_s[m], imp_s[m]) for m in ATTACK_METRICS},
            "mean_scaled_rgb_displacement": round(mean_displacement_raw, 2),
            "mean_scaled_rgb_displacement_raw": mean_displacement_raw,
        }

    even_clean = {(t, c): an.summarize_cell_samples(even_group[t, c]) for t in tids for c in cells}
    clean_res = eval_even(even_clean, [])
    clean_tau = {}
    for m in ATTACK_METRICS:
        g_arr = np.asarray(clean_res["gen_s"][m])
        i_arr = np.asarray(clean_res["imp_s"][m])
        clean_tau[m] = {
            "midpoint": float(0.5 * np.max(g_arr) + 0.5 * np.min(i_arr)),
            "u0": float(np.nextafter(np.min(i_arr), -np.inf)),
        }

    def score_against_clean_tau(res_obj: dict[str, Any], seed_id: int | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {
            "mean_scaled_rgb_displacement": res_obj["mean_scaled_rgb_displacement"],
            "mean_scaled_rgb_displacement_raw": res_obj["mean_scaled_rgb_displacement_raw"],
            "metrics": {},
            "metrics_unrounded": {},
        }
        if seed_id is not None:
            out["seed"] = seed_id
        for m in ATTACK_METRICS:
            g_arr = np.asarray(res_obj["gen_s"][m])
            i_arr = np.asarray(res_obj["imp_s"][m])
            mid = clean_tau[m]["midpoint"]
            u0 = clean_tau[m]["u0"]
            eer_lin_pct_raw = 100.0 * float(res_obj["roc"][m]["eer_linear_raw"])
            auc_raw = float(res_obj["roc"][m]["auc_raw"])
            frr_mid_raw = 100.0 * float(np.mean(g_arr > mid))
            far_mid_raw = 100.0 * float(np.mean(i_arr <= mid))
            frr_u0_raw = 100.0 * float(np.mean(g_arr > u0))
            out["metrics_unrounded"][m] = {
                "eer_linear_pct_raw": eer_lin_pct_raw,
                "auc_raw": auc_raw,
                "frr_midpoint_pct_raw": frr_mid_raw,
                "far_midpoint_pct_raw": far_mid_raw,
                "frr_u0_pct_raw": frr_u0_raw,
            }
            out["metrics"][m] = {
                "eer_linear_pct": round(eer_lin_pct_raw, 2),
                "auc": round(auc_raw, 6),
                "frr_midpoint_pct": round(frr_mid_raw, 2),
                "far_midpoint_pct": round(far_mid_raw, 2),
                "frr_u0_pct": round(frr_u0_raw, 2),
            }
        return out

    suite_out: dict[str, Any] = {
        "analysis_protocol": dict(an.ANALYSIS_PROTOCOL),
        "displacement_units": "Euclidean distance in 100 * encoded RGB / 255 coordinates",
        "clean_thresholds": clean_tau,
        "uniform_jitter": {},
        "directional_shift": {},
        "palette_quant": {},
    }

    for amp in [1, 2, 4, 8, 15, 31]:
        seed_runs = []
        for s in range(10):
            seed_val = 20261021 + s
            rng = np.random.default_rng(seed_val)
            ev_dict = {}
            displacements = []
            for t in tids:
                for c in cells:
                    pert = []
                    for r in even_group[t, c]:
                        pr = perturb_row_rgb(r, "uniform_jitter", amp, rng)
                        pert.append(pr)
                        if r["parsed"]["status"] == "valid":
                            displacements.append(rgb_displacement(r, pr))
                    ev_dict[t, c] = an.summarize_cell_samples(pert)
            seed_runs.append(score_against_clean_tau(eval_even(ev_dict, displacements), seed_id=seed_val))
        mean_displacement_raw = float(np.mean([x["mean_scaled_rgb_displacement_raw"] for x in seed_runs]))
        unrounded_mean = {}
        amp_entry: dict[str, Any] = {
            "mean_scaled_rgb_displacement": round(mean_displacement_raw, 2),
            "mean_scaled_rgb_displacement_raw": mean_displacement_raw,
        }
        for m in ATTACK_METRICS:
            m_eer_raw = float(np.mean([x["metrics_unrounded"][m]["eer_linear_pct_raw"] for x in seed_runs]))
            m_auc_raw = float(np.mean([x["metrics_unrounded"][m]["auc_raw"] for x in seed_runs]))
            m_frr_mid_raw = float(np.mean([x["metrics_unrounded"][m]["frr_midpoint_pct_raw"] for x in seed_runs]))
            m_far_mid_raw = float(np.mean([x["metrics_unrounded"][m]["far_midpoint_pct_raw"] for x in seed_runs]))
            m_frr_u0_raw = float(np.mean([x["metrics_unrounded"][m]["frr_u0_pct_raw"] for x in seed_runs]))
            unrounded_mean[m] = {
                "eer_linear_pct_raw": m_eer_raw,
                "auc_raw": m_auc_raw,
                "frr_midpoint_pct_raw": m_frr_mid_raw,
                "far_midpoint_pct_raw": m_far_mid_raw,
                "frr_u0_pct_raw": m_frr_u0_raw,
            }
            amp_entry[m] = {
                "eer_linear_pct": round(m_eer_raw, 2),
                "auc": round(m_auc_raw, 6),
                "frr_midpoint_pct": round(m_frr_mid_raw, 2),
                "far_midpoint_pct": round(m_far_mid_raw, 2),
                "frr_u0_pct": round(m_frr_u0_raw, 2),
            }
        amp_entry["unrounded_mean"] = unrounded_mean
        amp_entry["seed_runs"] = seed_runs
        suite_out["uniform_jitter"][f"±{amp}"] = amp_entry

    for shift in [-31, -15, -8, 8, 15, 31]:
        rng = np.random.default_rng(0)
        ev_dict = {}
        displacements = []
        for t in tids:
            for c in cells:
                pert = [perturb_row_rgb(r, "directional_shift", shift, rng) for r in even_group[t, c]]
                for r, pr in zip(even_group[t, c], pert):
                    if r["parsed"]["status"] == "valid":
                        displacements.append(rgb_displacement(r, pr))
                ev_dict[t, c] = an.summarize_cell_samples(pert)
        suite_out["directional_shift"][f"{shift:+d}"] = score_against_clean_tau(eval_even(ev_dict, displacements))

    for q_step in [17, 32]:
        rng = np.random.default_rng(0)
        ev_dict = {}
        displacements = []
        for t in tids:
            for c in cells:
                pert = [perturb_row_rgb(r, "palette_quant", q_step, rng) for r in even_group[t, c]]
                for r, pr in zip(even_group[t, c], pert):
                    if r["parsed"]["status"] == "valid":
                        displacements.append(rgb_displacement(r, pr))
                ev_dict[t, c] = an.summarize_cell_samples(pert)
        suite_out["palette_quant"][f"step_{q_step}"] = score_against_clean_tau(eval_even(ev_dict, displacements))

    # White-Box Public-Reference Replay Suite:
    # (a) Constant centroid-table replay (blocked by entropy screen)
    # (b) Cyclic odd-sample replay (preserves empirical entropy -> passes pure color & entropy screen under public reference!)
    # (c) Empirical distribution resampling replay (preserves empirical entropy -> passes under public reference!)
    centroid_ev, cyclic_ev, resample_ev = {}, {}, {}
    ref_mean_ent, centroid_ent, cyclic_ent = {}, {}, {}
    rng_rep = np.random.default_rng(20261021)
    for t in tids:
        r_ents, c_ents, cyc_ents = [], [], []
        for c in cells:
            odd_valid = [r for r in odd_group[t, c] if r["parsed"]["status"] == "valid"]
            if odd_valid:
                valid_rgbs = [r["parsed"]["rgb"] for r in odd_valid]
                mean_rgb = np.round(np.mean(valid_rgbs, axis=0)).astype(int)
                r_val, g_val, b_val = int(mean_rgb[0]), int(mean_rgb[1]), int(mean_rgb[2])
                cent_rows, cyc_rows, res_rows = [], [], []
                for idx_e, r in enumerate(even_group[t, c]):
                    # Centroid row
                    sr = dict(r)
                    sp = dict(r["parsed"])
                    sp.pop("lab", None)
                    sp.update({
                        "status": "valid",
                        "rgb": [r_val, g_val, b_val],
                        "voxel_bin_8": f"{r_val // 32}_{g_val // 32}_{b_val // 32}",
                        "canonical_hex": f"#{r_val:02X}{g_val:02X}{b_val:02X}",
                    })
                    sr["parsed"] = sp
                    cent_rows.append(sr)
                    # Cyclic odd replay row
                    cyc_rows.append(odd_valid[idx_e % len(odd_valid)])
                    # Empirical resampled row
                    res_rows.append(odd_valid[int(rng_rep.integers(0, len(odd_valid)))])
                centroid_ev[t, c] = an.summarize_cell_samples(cent_rows)
                cyclic_ev[t, c] = an.summarize_cell_samples(cyc_rows)
                resample_ev[t, c] = an.summarize_cell_samples(res_rows)
                r_ents.append(an.shannon_entropy_bits(odd_sum[t, c]["hex_counts"]))
                c_ents.append(an.shannon_entropy_bits(centroid_ev[t, c]["hex_counts"]))
                cyc_ents.append(an.shannon_entropy_bits(cyclic_ev[t, c]["hex_counts"]))
            else:
                centroid_ev[t, c] = even_clean[t, c]
                cyclic_ev[t, c] = even_clean[t, c]
                resample_ev[t, c] = even_clean[t, c]
        ref_mean_ent[t] = float(np.mean(r_ents)) if r_ents else 0.0
        centroid_ent[t] = float(np.mean(c_ents)) if c_ents else 0.0
        cyclic_ent[t] = float(np.mean(cyc_ents)) if cyc_ents else 0.0

    centroid_res = eval_even(centroid_ev, [])
    cyclic_res = eval_even(cyclic_ev, [])
    resample_res = eval_even(resample_ev, [])
    suite_out["whitebox_reference_replay"] = {
        "centroid_table_replay": {
            "raw_acceptance_rate_at_midpoint_pct": {
                m: round(100.0 * float(np.mean(np.asarray(centroid_res["gen_s"][m]) <= clean_tau[m]["midpoint"])), 2)
                for m in ATTACK_METRICS
            },
            "with_entropy_collapse_screen_acceptance_pct": round(
                100.0 * float(np.mean([
                    1.0 if (
                        centroid_res["gen_s"]["robust_manifold"][idx] <= clean_tau["robust_manifold"]["midpoint"]
                        and not (ref_mean_ent[t] > 0.30 and centroid_ent[t] < 0.25 * ref_mean_ent[t])
                    ) else 0.0
                    for idx, t in enumerate(tids)
                ])), 2
            ),
        },
        "cyclic_odd_sample_replay": {
            "raw_acceptance_rate_at_midpoint_pct": {
                m: round(100.0 * float(np.mean(np.asarray(cyclic_res["gen_s"][m]) <= clean_tau[m]["midpoint"])), 2)
                for m in ATTACK_METRICS
            },
            "with_entropy_collapse_screen_acceptance_pct": round(
                100.0 * float(np.mean([
                    1.0 if (
                        cyclic_res["gen_s"]["robust_manifold"][idx] <= clean_tau["robust_manifold"]["midpoint"]
                        and not (ref_mean_ent[t] > 0.30 and cyclic_ent[t] < 0.25 * ref_mean_ent[t])
                    ) else 0.0
                    for idx, t in enumerate(tids)
                ])), 2
            ),
        },
        "empirical_distribution_resampling_replay": {
            "raw_acceptance_rate_at_midpoint_pct": {
                m: round(100.0 * float(np.mean(np.asarray(resample_res["gen_s"][m]) <= clean_tau[m]["midpoint"])), 2)
                for m in ATTACK_METRICS
            },
        },
    }

    # Selective True-Model Routing Attack (p_honest in {10%, 25%, 50%})
    suite_out["selective_routing_impostor_far_pct"] = {}
    rng_rt = np.random.default_rng(20261021)
    for p_honest in [0.10, 0.25, 0.50]:
        far_by_m = {m: [] for m in ATTACK_METRICS}
        realized_fracs = []
        for i, ta in enumerate(tids):
            for j, tb in enumerate(tids):
                if i == j:
                    continue
                mixed_dists = {m: [] for m in ATTACK_METRICS}
                honest_calls, total_calls = 0, 0
                for c in cells:
                    ev_a = even_group[ta, c]
                    ev_b = even_group[tb, c]
                    n_len = min(len(ev_a), len(ev_b))
                    if n_len == 0 or odd_sum[ta, c]["n_valid"] < 1:
                        continue
                    flags = [rng_rt.random() < p_honest for _ in range(n_len)]
                    honest_calls += sum(1 for fl in flags if fl)
                    total_calls += n_len
                    mixed_rows = [ev_a[idx] if flags[idx] else ev_b[idx] for idx in range(n_len)]
                    msum = an.summarize_cell_samples(mixed_rows)
                    if msum["n_valid"] < 1:
                        continue
                    cd = an.compute_cell_distance(odd_sum[ta, c], msum)
                    for m in ATTACK_METRICS:
                        mixed_dists[m].append(cd[m])
                if total_calls > 0:
                    realized_fracs.append(honest_calls / total_calls)
                for m in ATTACK_METRICS:
                    if mixed_dists[m]:
                        score = sum(mixed_dists[m]) / len(mixed_dists[m])
                        far_by_m[m].append(1.0 if score <= clean_tau[m]["midpoint"] else 0.0)
        suite_out["selective_routing_impostor_far_pct"][f"honest_{int(100*p_honest)}pct"] = {
            "realized_honest_fraction_min_max": [round(min(realized_fracs), 4), round(max(realized_fracs), 4)],
            "impostor_far_pct": {
                m: round(100.0 * float(np.mean(far_by_m[m])), 2) for m in ATTACK_METRICS
            },
        }

    return suite_out


def evaluate_prompt_filter_benchmark() -> dict[str, Any]:
    """
    Evaluate T2 prompt-filtering rules across:
      - Positive Set 1: 40 explicit prompts from config/prompts.json + 16 paraphrased prompts from config/prompts.paraphrase.json (56 total)
      - Positive Set 2: 16 implicit CSS/theme color prompts that omit literal '#RRGGBB' and 'R,G,B' strings
      - Negative Set: 100 benign developer/UI/CSS/general user prompts (including legitimate frontend questions)
    """
    p0_cfg = json.loads((ROOT / "config/prompts.json").read_text(encoding="utf-8"))
    para_cfg = json.loads((ROOT / "config/prompts.paraphrase.json").read_text(encoding="utf-8"))
    explicit_pos = [
        txt for t in p0_cfg["tasks"].values() for txt in t["prompts"].values()
    ] + [
        txt for t in para_cfg["tasks"].values() for txt in t["prompts"].values()
    ]

    implicit_pos = [
        "Write a 6-character CSS hex color value for your favorite shade, prefixed with a hash symbol.",
        "Output a web color code (hash followed by six hex digits) representing a deep ocean.",
        "Give me a warm sunset shade as a standard 6-digit HTML hex string.",
        "What color represents calmness? Answer only with a CSS hex literal.",
        "Provide a forest green shade as a 6-character hexadecimal color literal.",
        "Pick a random shade and return only its 6-digit CSS hex string.",
        "Name a midnight sky shade as a standard HTML hex color literal.",
        "Give three comma-separated 8-bit channel values (0 to 255) for your favorite color.",
        "请输出一个代表你最喜欢颜色的6位网页十六进制色号（带井号）。",
        "给出一个代表深海颜色的6位HTML十六进制色值。",
        "用标准6位CSS十六进制颜色代码表示温暖的日落色。",
        "什么颜色最代表平静？仅回复带井号的6位十六进制色号。",
        "给出一种森林绿的6位网页十六进制颜色值。",
        "随机选一种颜色，仅输出其带井号的6位十六进制色值。",
        "用带井号的6位十六进制颜色代码表示午夜星空。",
        "用三个逗号分隔的0到255整数表示你最喜欢的颜色通道值。",
    ]

    benign_negatives = [
        # 40 benign frontend/CSS/design developer requests
        "How do I center a div vertically and horizontally using CSS flexbox?",
        "Convert the hex color #FF5733 to R,G,B decimal values in JavaScript.",
        "Why is my CSS linear-gradient(#000000, #FFFFFF) showing banding on OLED screens?",
        "Write a Python function to parse #RRGGBB strings into (R, G, B) tuples.",
        "What is the WCAG contrast ratio between #1E90FF and #FFFFFF for button text?",
        "Fix this Tailwind CSS navbar so the dark mode background uses slate-900.",
        "In Matplotlib, how do I set the scatter plot color to an R,G,B tuple?",
        "Explain the difference between sRGB and Display P3 color spaces in web browsers.",
        "Generate a 5-color accessible palette in #RRGGBB format for a fintech dashboard.",
        "My SVG icon fill='#3B82F6' is not changing on hover in React.",
        "Write a regex that validates #RRGGBB and #RGB hex color codes in TypeScript.",
        "How do I animate background-color from R,G,B (0, 0, 0) to (255, 255, 255) in CSS?",
        "What is the standard hex code for DodgerBlue in the W3C CSS specification?",
        "Convert an image buffer from BGR to R,G,B layout using OpenCV in Python.",
        "Why does Safari render my #RRGGBB border slightly darker than Chrome?",
        "Create a CSS variable theme with primary, secondary, and accent colors.",
        "How to read pixel R,G,B values from an HTML5 canvas context?",
        "Debug this GLSL fragment shader that outputs vec4(R, G, B, 1.0).",
        "What color scheme works best for a medical records web application?",
        "How do I configure VS Code syntax highlighting colors in settings.json?",
        "请帮我写一段解析 #RRGGBB 颜色代码并转换为 R,G,B 数组的 JS 函数。",
        "CSS 中如何把背景颜色设置为半透明的蓝色？",
        "为什么我的网页在深色模式下字体颜色对比度不够？",
        "用 Python PIL 读取图片每个像素的 R,G,B 数值并计算直方图。",
        "Tailwind CSS 里的 blue-500 对应的 #RRGGBB 色号是多少？",
        "如何在 ECharts 折线图里自定义渐变色？",
        "写一个正则表达式匹配文本中所有的 #RRGGBB 颜色值。",
        "iOS SwiftUI 中如何用 R,G,B 初始化一个 Color 对象？",
        "推荐一套适合科技感大屏可视化的深海蓝配色方案。",
        "为什么 Photoshop 导出的 PNG 颜色和浏览器里显示的 #RRGGBB 不一致？",
        "How can I extract the dominant color from a JPEG image in Node.js?",
        "Write a bash script to replace all occurrences of #000000 with #111827 in CSS files.",
        "What is the difference between hsl(), rgb(), and #RRGGBB in modern CSS?",
        "How to implement a color picker component in Vue 3?",
        "Why does my terminal tmux status bar ignore 24-bit R,G,B escape sequences?",
        "Convert CIE L*a*b* coordinates back to sRGB in NumPy.",
        "How do I style a disabled button in Material UI?",
        "What are the brand guideline hex colors for GitHub dark mode?",
        "Explain gamma correction in 8-bit R,G,B framebuffers.",
        "How to set box-shadow opacity without affecting child elements?",
        # 60 general coding, math, writing, and knowledge queries
        "Explain the intuition behind the Singular Value Decomposition (SVD).",
        "Write an async Python client with exponential backoff using asyncio.",
        "What are the main causes of inflation in post-pandemic supply chains?",
        "Summarize the key differences between PostgreSQL MVCC and SQLite WAL mode.",
        "How do I configure Nginx as a reverse proxy with WebSocket support?",
        "Write a unit test in pytest that mocks urllib.request.urlopen.",
        "Translate the following abstract into academic English.",
        "What is the time complexity of building a suffix automaton?",
        "Explain how Jensen-Shannon divergence differs from Kullback-Leibler divergence.",
        "How to resolve a git rebase conflict when binary files are modified?",
        "Write a SQL query to compute a 7-day rolling average of active users.",
        "What is the role of LayerNorm in pre-norm Transformer architectures?",
        "How do I profile CPU cache misses on macOS Apple Silicon?",
        "Draft a concise email requesting an extension on a conference camera-ready deadline.",
        "Why does floating-point addition violate associativity in IEEE 754?",
        "Explain the difference between TCP congestion control algorithms CUBIC and BBR.",
        "How to serialize a NumPy array into JSON without losing precision?",
        "What is the exact binomial test and when should McNemar's test be used?",
        "Write a Rust function to compute the SHA-256 digest of a file stream.",
        "How does speculative decoding accelerate autoregressive LLM inference?",
        "Explain KV-cache prefix caching in vLLM and its impact on TTFT latency.",
        "What are the security implications of CORS wildcard origins with credentials?",
        "How to prove that the Gaussian Bures-Wasserstein distance is a true metric?",
        "Write a Dockerfile for a minimal Python 3.12 production service.",
        "What is the difference between FP8 E4M3 and E5M2 quantization formats?",
        "How do I set up SSH agent forwarding safely across jump hosts?",
        "Explain the concept of focal points (Schelling points) in game theory.",
        "Write a regular expression to match balanced parentheses up to depth 2.",
        "What causes vanishing gradients in deep recurrent neural networks?",
        "How to compute the Equal Error Rate (EER) from a set of genuine and impostor scores?",
        "请解释 Transformer 模型中旋转位置编码（RoPE）的数学原理。",
        "如何在 Linux 下排查进程内存泄漏问题？",
        "写一个二分查找算法并证明其边界条件不会死循环。",
        "为什么高并发场景下数据库连接池会耗尽？如何调优？",
        "简述 HTTPS TLS 1.3 握手过程相比 TLS 1.2 的改进。",
        "如何用 Python 统计一篇文章中出现频率最高的前 10 个单词？",
        "解释分布式系统中的 CAP 定理与 BASE 理论。",
        "在 PyTorch 中如何使用 DistributedDataParallel 进行多卡训练？",
        "写一段 SQL 查询找出每个部门薪水第二高的员工。",
        "什么是零知识证明？它在区块链隐私保护中如何应用？",
        "Explain how B-trees minimize disk I/O in relational database indexes.",
        "How do I strip ANSI escape codes from log files in Python?",
        "What is the difference between a mutex and a binary semaphore?",
        "Write a function to sample uniformly from the surface of a 3D unit sphere.",
        "How does the Benjamini-Hochberg procedure control the false discovery rate?",
        "Explain why Reed-Solomon codes are used in QR codes and RAID 6.",
        "How do I debug a segmentation fault using lldb on macOS?",
        "What are the advantages of Cholesky decomposition over LU decomposition?",
        "Write a Python generator that yields Fibonacci numbers indefinitely.",
        "How does Content Security Policy (CSP) mitigate XSS attacks?",
        "Explain the difference between L1 and L2 regularization in linear models.",
        "How to configure systemd service restart policies on Ubuntu?",
        "What is the coupon collector's problem and its expected value?",
        "Write a clean implementation of Dijkstra's shortest path algorithm.",
        "How does FlashAttention reduce HBM memory traffic on GPUs?",
        "Explain the difference between covariance and correlation matrices.",
        "How to check if a directed graph contains a cycle using DFS?",
        "What is the Cramer-Rao lower bound in parameter estimation?",
        "Write a shell command to find all files larger than 100MB modified in the last 7 days.",
        "Explain how consistent hashing minimizes key redistribution in distributed caches.",
    ]

    lit_re = re.compile(r"#RRGGBB|R\s*,\s*G\s*,\s*B", re.IGNORECASE)
    broad_re = re.compile(r"(hex|color|colour|rgb|#[0-9a-f]{6}|十六进制|颜色|色号|色值)", re.IGNORECASE)

    def eval_rule(pat: re.Pattern[str]) -> dict[str, Any]:
        tp_exp = sum(1 for x in explicit_pos if pat.search(x))
        tp_imp = sum(1 for x in implicit_pos if pat.search(x))
        fp_neg = sum(1 for x in benign_negatives if pat.search(x))
        return {
            "tpr_explicit_prompts_pct": round(100.0 * tp_exp / len(explicit_pos), 2),
            "tpr_implicit_prompts_pct": round(100.0 * tp_imp / len(implicit_pos), 2),
            "fpr_benign_all_100_pct": round(100.0 * fp_neg / len(benign_negatives), 2),
            "fpr_benign_frontend_40_pct": round(100.0 * sum(1 for x in benign_negatives[:40] if pat.search(x)) / 40.0, 2),
            "counts": {
                "explicit_pos": f"{tp_exp}/{len(explicit_pos)}",
                "implicit_pos": f"{tp_imp}/{len(implicit_pos)}",
                "benign_neg_flagged": f"{fp_neg}/{len(benign_negatives)}",
            },
        }

    return {
        "rule_1_literal_format_regex": eval_rule(lit_re),
        "rule_2_broad_color_keyword_regex": eval_rule(broad_re),
    }


def evaluate_cross_session_a_to_e(
    rows_a_fresh: list[dict[str, Any]],
    rows_e: list[dict[str, Any]],
    fmap: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate independent cross-session verification from Dataset A (t=0h) to Dataset E (t=+6.5h)
    across the 10 shared targets and 8 shared (task_id, lang) cells.
    """
    from datetime import datetime

    tids = sorted({r["target_id"] for r in rows_e})
    tset = set(tids)
    cells_a = {f"{r['task_id']}|{r['lang']}" for r in rows_a_fresh if r["target_id"] in tset}
    cells_e = {f"{r['task_id']}|{r['lang']}" for r in rows_e}
    shared_cells = sorted(cells_a & cells_e)

    a_sub = [r for r in rows_a_fresh if r["target_id"] in tset and f"{r['task_id']}|{r['lang']}" in shared_cells]
    e_sub = [r for r in rows_e if r["target_id"] in tset and f"{r['task_id']}|{r['lang']}" in shared_cells]

    def parse_ts(s: str) -> float:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()

    ts_a_by_t = {t: statistics.median([parse_ts(r["timestamp_utc"]) for r in a_sub if r["target_id"] == t]) for t in tids}
    ts_e_by_t = {t: statistics.median([parse_ts(r["timestamp_utc"]) for r in e_sub if r["target_id"] == t]) for t in tids}
    gaps_hr = [(ts_e_by_t[t] - ts_a_by_t[t]) / 3600.0 for t in tids]

    eval_metrics = ["hybrid", "robust_manifold", "energy_reg", "voxel_jsd", "hex_jsd", "w2_norm"]

    def eval_pair_groups(
        ref_rows: list[dict[str, Any]],
        qry_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        rg: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
        qg: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
        for r in ref_rows:
            rg[r["target_id"], f"{r['task_id']}|{r['lang']}"].append(r)
        for r in qry_rows:
            qg[r["target_id"], f"{r['task_id']}|{r['lang']}"].append(r)
        rsum = {(t, c): an.summarize_cell_samples(rg[t, c]) for t in tids for c in shared_cells}
        qsum = {(t, c): an.summarize_cell_samples(qg[t, c]) for t in tids for c in shared_cells}

        out_m: dict[str, Any] = {}
        for m in eval_metrics:
            gen_s, imp_s = [], []
            top1_exact, top1_fam = 0, 0
            for ta in tids:
                dists = []
                for tb in tids:
                    sh = [c for c in shared_cells if rsum[tb, c]["n_valid"] >= 1 and qsum[ta, c]["n_valid"] >= 1]
                    val = sum(an.compute_cell_distance(rsum[tb, c], qsum[ta, c])[m] for c in sh) / len(sh)
                    dists.append((val, tb))
                    if ta == tb:
                        gen_s.append(val)
                    else:
                        imp_s.append(val)
                dists.sort()
                best_ref = dists[0][1]
                if best_ref == ta:
                    top1_exact += 1
                if fmap[best_ref]["family"] == fmap[ta]["family"]:
                    top1_fam += 1
            roc_m = an.compute_roc_eer(gen_s, imp_s)
            out_m[m] = {
                "top1_checkpoint": f"{top1_exact}/{len(tids)}",
                "top1_family": f"{top1_fam}/{len(tids)}",
                "auc": roc_m["auc"],
                "eer_discrete_pct": round(100.0 * roc_m["eer_raw"], 2),
                "eer_linear_pct": round(100.0 * roc_m["eer_linear_raw"], 2),
            }
        return out_m

    a_odd = [r for r in a_sub if int(r["rep"]) % 2 == 1]
    e_odd = [r for r in e_sub if int(r["rep"]) % 2 == 1]
    e_even = [r for r in e_sub if int(r["rep"]) % 2 == 0]

    return {
        "n_shared_models": len(tids),
        "n_shared_cells": len(shared_cells),
        "shared_cells": shared_cells,
        "session_A_utc_min_max": [min(r["timestamp_utc"] for r in a_sub), max(r["timestamp_utc"] for r in a_sub)],
        "session_E_utc_min_max": [min(r["timestamp_utc"] for r in e_sub), max(r["timestamp_utc"] for r in e_sub)],
        "inter_session_gap_hours_min_median_max": [
            round(min(gaps_hr), 2),
            round(statistics.median(gaps_hr), 2),
            round(max(gaps_hr), 2),
        ],
        "same_session_E_8cells_split_3v3": eval_pair_groups(e_odd, e_even),
        "cross_session_3v3_Aodd_to_Eeven": eval_pair_groups(a_odd, e_even),
        "cross_session_6v6_Afull_to_Efull": eval_pair_groups(a_sub, e_sub),
    }


def evaluate_out_of_sample_jitter_e(
    rows_e: list[dict[str, Any]],
    frozen_transfer_results: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate out-of-sample RGB uniform jitter on held-out Dataset E (20U x 6R)
    under both E's ROC separability and strictly frozen Dev B-20x6 thresholds.
    """
    tids = sorted({r["target_id"] for r in rows_e})
    cells = sorted({f"{r['task_id']}|{r['lang']}" for r in rows_e})
    odd_group: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    even_group: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows_e:
        ck = f"{r['task_id']}|{r['lang']}"
        if int(r["rep"]) % 2 == 1:
            odd_group[r["target_id"], ck].append(r)
        else:
            even_group[r["target_id"], ck].append(r)
    odd_sum = {(t, c): an.summarize_cell_samples(odd_group[t, c]) for t in tids for c in cells}

    out: dict[str, Any] = {}
    for amp in [0, 1, 2, 4, 8]:
        n_seeds = 1 if amp == 0 else 10
        per_m_acc: dict[str, dict[str, list[float]]] = {
            m: {"auc": [], "eer_lin": [], "frr_mid": [], "far_mid": [], "frr_eer": [], "far_eer": []}
            for m in ATTACK_METRICS
        }
        all_displacements: list[float] = []
        for s in range(n_seeds):
            rng = np.random.default_rng(20261021 + s)
            ev_sum = {}
            for t in tids:
                for c in cells:
                    if amp == 0:
                        pert = even_group[t, c]
                    else:
                        pert = []
                        for r in even_group[t, c]:
                            pr = perturb_row_rgb(r, "uniform_jitter", amp, rng)
                            pert.append(pr)
                            if r["parsed"]["status"] == "valid":
                                all_displacements.append(rgb_displacement(r, pr))
                    ev_sum[t, c] = an.summarize_cell_samples(pert)
            for m in ATTACK_METRICS:
                gen_s, imp_s = [], []
                for i, ta in enumerate(tids):
                    for j, tb in enumerate(tids):
                        sh = [c for c in cells if odd_sum[ta, c]["n_valid"] >= 1 and ev_sum[tb, c]["n_valid"] >= 1]
                        v = sum(an.compute_cell_distance(odd_sum[ta, c], ev_sum[tb, c])[m] for c in sh) / len(sh)
                        if i == j:
                            gen_s.append(v)
                        else:
                            imp_s.append(v)
                roc_m = an.compute_roc_eer(gen_s, imp_s)
                g_arr = np.asarray(gen_s)
                i_arr = np.asarray(imp_s)
                f_mid = float(frozen_transfer_results[m]["frozen_dev_midpoint_tau_raw"])
                f_eer = float(frozen_transfer_results[m]["frozen_dev_eer_tau_raw"])
                per_m_acc[m]["auc"].append(float(roc_m["auc_raw"]))
                per_m_acc[m]["eer_lin"].append(100.0 * float(roc_m["eer_linear_raw"]))
                per_m_acc[m]["frr_mid"].append(100.0 * float(np.mean(g_arr > f_mid)))
                per_m_acc[m]["far_mid"].append(100.0 * float(np.mean(i_arr <= f_mid)))
                per_m_acc[m]["frr_eer"].append(100.0 * float(np.mean(g_arr > f_eer)))
                per_m_acc[m]["far_eer"].append(100.0 * float(np.mean(i_arr <= f_eer)))
        out[f"±{amp}"] = {
            "displacement_units": "Euclidean distance in 100 * encoded RGB / 255 coordinates",
            "mean_scaled_rgb_displacement_raw": float(np.mean(all_displacements)) if all_displacements else 0.0,
            "mean_scaled_rgb_displacement": round(float(np.mean(all_displacements)), 2) if all_displacements else 0.0,
            "metrics": {
                m: {
                    "heldout_auc": round(float(np.mean(per_m_acc[m]["auc"])), 4),
                    "heldout_eer_linear_pct": round(float(np.mean(per_m_acc[m]["eer_lin"])), 2),
                    "test_frr_at_frozen_mid_pct": round(float(np.mean(per_m_acc[m]["frr_mid"])), 2),
                    "test_far_at_frozen_mid_pct": round(float(np.mean(per_m_acc[m]["far_mid"])), 2),
                    "test_frr_at_frozen_eer_tau_pct": round(float(np.mean(per_m_acc[m]["frr_eer"])), 2),
                    "test_far_at_frozen_eer_tau_pct": round(float(np.mean(per_m_acc[m]["far_eer"])), 2),
                }
                for m in ATTACK_METRICS
            },
        }
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/reproduce_all_rgb_summary.json",
        help="Write the recomputed RGB report here (default: data/reproduce_all_rgb_summary.json).",
    )
    args = parser.parse_args(argv)
    out_file = args.output if args.output.is_absolute() else ROOT / args.output
    if out_file.resolve() == (ROOT / "data/reproduce_all_summary.json").resolve():
        parser.error("The historical Lab report is reserved; choose a new RGB output path.")
    fmap = json.loads((ROOT / "config/family_map.json").read_text(encoding="utf-8"))["families"]

    rows_a_leg, lines_a, sha_a = load_jsonl_clean("data/census_40models.jsonl", apply_legacy_reasoning_meta=True)
    rows_a_fresh, _, _ = load_jsonl_clean("data/census_40models.jsonl", apply_legacy_reasoning_meta=False)
    rows_b, lines_b, sha_b = load_jsonl_clean("data/exp_40u15r.jsonl")
    rows_c, lines_c, sha_c = load_jsonl_clean("data/exp_paraphrase.jsonl")
    rows_d, lines_d, sha_d = load_jsonl_clean("data/exp_bruckner_baseline.jsonl")
    rows_e, lines_e, sha_e = load_jsonl_clean("data/exp_heldout_confirm.jsonl")

    # Count exact identical records vs trial_key overlaps across datasets
    set_a_full = {(r["trial_key"], r["timestamp_utc"], r["raw_text"]) for r in rows_a_leg}
    set_b_full = {(r["trial_key"], r["timestamp_utc"], r["raw_text"]) for r in rows_b}
    set_e_full = {(r["trial_key"], r["timestamp_utc"], r["raw_text"]) for r in rows_e}
    overlap_ab_identical = len(set_a_full & set_b_full)
    overlap_be_targets = len({r["target_id"] for r in rows_b} & {r["target_id"] for r in rows_e})
    overlap_ae_targets = len({r["target_id"] for r in rows_a_leg} & {r["target_id"] for r in rows_e})
    overlap_ae_identical = len(set_a_full & set_e_full)

    total_lines = lines_a + lines_b + lines_c + lines_d + lines_e
    unique_records = len(rows_a_leg) + len(rows_b) - overlap_ab_identical + len(rows_c) + len(rows_d) + len(rows_e)

    # 1. Dataset A (56 models, 8U x 6R): evaluate both with legacy_reasoning_meta and pure fresh_raw_only
    res_a_leg = evaluate_cohort(rows_a_leg, fmap, min_cell_full=4, min_split=2)
    res_a_fresh = evaluate_cohort(rows_a_fresh, fmap, min_cell_full=4, min_split=2)

    # 2. Dataset B (10 Dev models, 40U x 15R) + Full 2D (n, k) Grid
    res_b_full = evaluate_cohort(rows_b, fmap, min_cell_full=10, min_split=5)
    grid_2d_b = compute_2d_grid_b(rows_b)

    # 3. Dataset C (10 Dev models, Cross-Paraphrase P0 -> P1, P2, P1+P2)
    base_tasks = ["hex_favorite", "rgb_favorite", "hex_ocean", "hex_warm"]
    cells_8 = [f"{t}|{l}" for t in base_tasks for l in ("en", "zh")]
    p0_8 = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows_b:
        ck = f"{r['task_id']}|{r['lang']}"
        if ck in cells_8 and int(r["rep"]) <= 8:
            p0_8[r["target_id"]][ck].append(r)
    p1_g = collections.defaultdict(lambda: collections.defaultdict(list))
    p2_g = collections.defaultdict(lambda: collections.defaultdict(list))
    p12_g = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows_c:
        t_id = r["target_id"]
        ck = f"{r['task_id'][3:]}|{r['lang']}"
        if r["task_id"].startswith("p1_"):
            p1_g[t_id][ck].append(r)
        else:
            p2_g[t_id][ck].append(r)
        p12_g[t_id][ck].append(r)

    dev_tids = sorted(p0_8.keys())
    S_p0 = {t: {c: an.summarize_cell_samples(p0_8[t][c]) for c in cells_8} for t in dev_tids}
    paraphrase_matrix = {}
    for p_label, p_dict in [("P1", p1_g), ("P2", p2_g), ("P1_P2_pooled", p12_g)]:
        S_pr = {t: {c: an.summarize_cell_samples(p_dict[t][c]) for c in cells_8} for t in dev_tids}
        paraphrase_matrix[p_label] = {}
        for m in ["hybrid", "robust_manifold", "energy_reg", "voxel_jsd", "hex_jsd", "w2_norm"]:
            gen_v, imp_v = [], []
            top1_exact, top1_fam = 0, 0
            for ta in dev_tids:
                dists = []
                for tb in dev_tids:
                    cd = [an.compute_cell_distance(S_p0[tb][c], S_pr[ta][c])[m] for c in cells_8]
                    val = sum(cd) / len(cd)
                    dists.append((val, tb))
                    if ta == tb:
                        gen_v.append(val)
                    else:
                        imp_v.append(val)
                dists.sort()
                best_ref = dists[0][1]
                if best_ref == ta:
                    top1_exact += 1
                if fmap[best_ref]["family"] == fmap[ta]["family"]:
                    top1_fam += 1
            roc_m = an.compute_roc_eer(gen_v, imp_v)
            paraphrase_matrix[p_label][m] = {
                "top1_checkpoint": f"{top1_exact}/{len(dev_tids)}",
                "top1_family": f"{top1_fam}/{len(dev_tids)}",
                "auc": roc_m["auc"],
                "eer_linear_pct": round(100.0 * roc_m["eer_linear_raw"], 2),
            }

    for self_label, prefix_str in [("P1_self_odd_even", "p1_"), ("P2_self_odd_even", "p2_")]:
        sub_self = [r for r in rows_c if r["task_id"].startswith(prefix_str)]
        res_self = evaluate_cohort(sub_self, fmap, min_cell_full=2, min_split=1)
        paraphrase_matrix[self_label] = {
            m: {
                "auc": res_self["roc_raw"][m]["auc"],
                "eer_discrete_pct": round(100.0 * res_self["roc_raw"][m]["eer_raw"], 2),
                "eer_linear_pct": round(100.0 * res_self["roc_raw"][m]["eer_linear_raw"], 2),
                "loo_family": f"{res_self['loo_family'][m]['correct']}/{res_self['loo_family'][m]['total']} ({res_self['loo_family'][m]['accuracy_pct']}%)",
            }
            for m in ["hybrid", "robust_manifold", "energy_reg", "voxel_jsd", "hex_jsd", "w2_norm"]
        }

    # 4. Dataset D vs Dataset B-20x6 Subset (Paired Request-Budget & Reported-Token Comparison)
    rows_b_20x6 = [r for r in rows_b if r["lang"] in ("en", "zh") and int(r["rep"]) <= 6]
    tok_d_in = sum((r.get("usage") or {}).get("input_tokens") or 0 for r in rows_d)
    tok_d_out = sum((r.get("usage") or {}).get("output_tokens") or 0 for r in rows_d)
    tok_b_in = sum((r.get("usage") or {}).get("input_tokens") or 0 for r in rows_b_20x6)
    tok_b_out = sum((r.get("usage") or {}).get("output_tokens") or 0 for r in rows_b_20x6)

    res_d = evaluate_cohort(rows_d, fmap, min_cell_full=2, min_split=1, metrics=["hex_jsd"])
    res_b_20x6 = evaluate_cohort(rows_b_20x6, fmap, min_cell_full=2, min_split=1)

    # Dynamic McNemar test computation from per-model LOO predictions
    mcnemar_stats = {
        m: exact_mcnemar_two_sided_p(res_d["loo_family"]["hex_jsd"]["predictions"], res_b_20x6["loo_family"][m]["predictions"])
        for m in ATTACK_METRICS
    }

    # Per-cell query (even-half) token cost lookup for actual drawn-subset cost calculation
    even_tok_d: dict[tuple[str, str], int] = collections.defaultdict(int)
    for r in rows_d:
        if int(r["rep"]) % 2 == 0:
            u = r.get("usage") or {}
            even_tok_d[r["target_id"], f"{r['task_id']}|{r['lang']}"] += (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0)
    even_tok_b: dict[tuple[str, str], int] = collections.defaultdict(int)
    for r in rows_b_20x6:
        if int(r["rep"]) % 2 == 0:
            u = r.get("usage") or {}
            even_tok_b[r["target_id"], f"{r['task_id']}|{r['lang']}"] += (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0)

    k_vals_20 = [1, 2, 4, 8, 12, 16, 20]
    curve_d = an.compute_query_budget_curve(res_d["gen_cells"]["hex_jsd"], res_d["imp_cells"]["hex_jsd"], res_d["all_cells"], k_vals_20, n_resamples=200, seed=42)
    curves_b_20x6 = {
        m: an.compute_query_budget_curve(res_b_20x6["gen_cells"][m], res_b_20x6["imp_cells"][m], res_b_20x6["all_cells"], k_vals_20, n_resamples=200, seed=42)
        for m in ATTACK_METRICS
    }

    mean_tok_per_cell_half_d = (tok_d_in + tok_d_out) / (10.0 * 20.0 * 2.0)
    mean_tok_per_cell_half_b = (tok_b_in + tok_b_out) / (10.0 * 20.0 * 2.0)
    token_cost_curve = {}
    rng_eer_d = random.Random(42)
    rng_eer_b = random.Random(42)
    for k in k_vals_20:
        rng_d = random.Random(42)
        d_cells = res_d["all_cells"]
        d_sub_toks = [
            sum(even_tok_d[t, c] for c in (d_cells if k == 20 else rng_d.sample(d_cells, k)))
            for _ in range(1 if k == 20 else 200)
            for t in dev_tids
        ]
        d_shared_subs = [d_cells if k == 20 else rng_eer_d.sample(d_cells, k) for _ in range(1 if k == 20 else 200)]
        d_eer_matched_toks = [sum(even_tok_d[t, c] for c in sub) for sub in d_shared_subs for t in dev_tids]

        rng_b = random.Random(42)
        b_cells = res_b_20x6["all_cells"]
        b_sub_toks = [
            sum(even_tok_b[t, c] for c in (b_cells if k == 20 else rng_b.sample(b_cells, k)))
            for _ in range(1 if k == 20 else 200)
            for t in dev_tids
        ]
        b_shared_subs = [b_cells if k == 20 else rng_eer_b.sample(b_cells, k) for _ in range(1 if k == 20 else 200)]
        b_eer_matched_toks = [sum(even_tok_b[t, c] for c in sub) for sub in b_shared_subs for t in dev_tids]

        token_cost_curve[str(k)] = {
            "bruckner_tokens_per_audit_formula": round(k * mean_tok_per_cell_half_d, 1),
            "bruckner_drawn_query_tokens_mean": round(float(np.mean(d_sub_toks)), 2),
            "bruckner_drawn_query_tokens_min_max": [int(min(d_sub_toks)), int(max(d_sub_toks))],
            "bruckner_eer_matched_query_tokens_mean": round(float(np.mean(d_eer_matched_toks)), 2),
            "bruckner_eer_matched_query_tokens_min_max": [int(min(d_eer_matched_toks)), int(max(d_eer_matched_toks))],
            "bruckner_discrete_eer_pct": curve_d[k]["mean_eer_pct"],
            "color_tokens_per_audit_formula": round(k * mean_tok_per_cell_half_b, 1),
            "color_drawn_query_tokens_mean": round(float(np.mean(b_sub_toks)), 2),
            "color_drawn_query_tokens_min_max": [int(min(b_sub_toks)), int(max(b_sub_toks))],
            "color_eer_matched_query_tokens_mean": round(float(np.mean(b_eer_matched_toks)), 2),
            "color_eer_matched_query_tokens_min_max": [int(min(b_eer_matched_toks)), int(max(b_eer_matched_toks))],
            "color_hex_jsd_discrete_eer_pct": curves_b_20x6["hex_jsd"][k]["mean_eer_pct"],
            "color_voxel_jsd_discrete_eer_pct": curves_b_20x6["voxel_jsd"][k]["mean_eer_pct"],
            "energy_reg_discrete_eer_pct": curves_b_20x6["energy_reg"][k]["mean_eer_pct"],
            "hybrid_discrete_eer_pct": curves_b_20x6["hybrid"][k]["mean_eer_pct"],
            "robust_manifold_discrete_eer_pct": curves_b_20x6["robust_manifold"][k]["mean_eer_pct"],
        }

    # Unique canonical outputs per cell across the 10 Dev models (quantifying stereotype collision vs. hex de-collapsing)
    uniq_d_by_cell: dict[str, set[str]] = collections.defaultdict(set)
    for r in rows_d:
        if r["parsed"]["status"] == "valid" and r["parsed"].get("canonical_hex"):
            uniq_d_by_cell[f"{r['task_id']}|{r['lang']}"].add(str(r["parsed"]["canonical_hex"]))
    uniq_b_by_cell: dict[str, set[str]] = collections.defaultdict(set)
    for r in rows_b_20x6:
        if r["parsed"]["status"] == "valid" and r["parsed"].get("canonical_hex"):
            uniq_b_by_cell[f"{r['task_id']}|{r['lang']}"].add(str(r["parsed"]["canonical_hex"]))
    mean_uniq_d = round(sum(len(v) for v in uniq_d_by_cell.values()) / max(1, len(uniq_d_by_cell)), 2)
    mean_uniq_b = round(sum(len(v) for v in uniq_b_by_cell.values()) / max(1, len(uniq_b_by_cell)), 2)

    # 5. Confirmation Dataset E (10 non-B models, fresh sampling) + Combined 20-Model Negative-Pair Breakdown
    res_e_heldout = evaluate_cohort(rows_e, fmap, min_cell_full=2, min_split=1)
    res_be_combined20 = evaluate_cohort(rows_b_20x6 + rows_e, fmap, min_cell_full=2, min_split=1)
    dev_set_ids = set(dev_tids)

    frozen_transfer_results = {}
    for m in ["robust_manifold", "energy_reg", "soft_voxel_jsd", "hybrid", "voxel_jsd", "hex_jsd"]:
        dev_g = np.asarray(res_b_20x6["gen_scores"][m])
        dev_i = np.asarray(res_b_20x6["imp_scores"][m])
        frozen_mid = float(0.5 * np.max(dev_g) + 0.5 * np.min(dev_i))
        frozen_tau_eer = float(res_b_20x6["roc_raw"][m]["threshold_raw"])
        test_g = np.asarray(res_e_heldout["gen_scores"][m])
        test_i = np.asarray(res_e_heldout["imp_scores"][m])

        neg_groups = {}
        for g_name, pred in [
            ("BB", lambda x, y: x in dev_set_ids and y in dev_set_ids),
            ("EE", lambda x, y: x not in dev_set_ids and y not in dev_set_ids),
            ("B_ref_E_query", lambda x, y: x in dev_set_ids and y not in dev_set_ids),
            ("E_ref_B_query", lambda x, y: x not in dev_set_ids and y in dev_set_ids),
            ("all_380", lambda x, y: True),
        ]:
            sub_p = [p for p in res_be_combined20["directed_impostor_pairs"] if pred(p["reference_odd"], p["query_even"])]
            fa = [p for p in sub_p if p["scores"][m] <= frozen_mid]
            neg_groups[g_name] = {
                "false_accepts": len(fa),
                "n_pairs": len(sub_p),
                "far_pct": round(100.0 * len(fa) / max(1, len(sub_p)), 2),
            }

        frozen_transfer_results[m] = {
            "heldout_auc": res_e_heldout["roc_raw"][m]["auc"],
            "heldout_eer_linear_pct": round(100.0 * res_e_heldout["roc_raw"][m]["eer_linear_raw"], 2),
            "heldout_loo_family": f"{res_e_heldout['loo_family'][m]['correct']}/{res_e_heldout['loo_family'][m]['total']} ({res_e_heldout['loo_family'][m]['accuracy_pct']}%)",
            "frozen_dev_midpoint_tau": round(frozen_mid, 6),
            "frozen_dev_midpoint_tau_raw": frozen_mid,
            "test_frr_at_frozen_mid_pct": round(100.0 * float(np.mean(test_g > frozen_mid)), 2),
            "test_far_at_frozen_mid_pct": round(100.0 * float(np.mean(test_i <= frozen_mid)), 2),
            "frozen_dev_eer_tau_raw": frozen_tau_eer,
            "test_frr_at_frozen_eer_tau_pct": round(100.0 * float(np.mean(test_g > frozen_tau_eer)), 2),
            "test_far_at_frozen_eer_tau_pct": round(100.0 * float(np.mean(test_i <= frozen_tau_eer)), 2),
            "negative_pair_groups_at_frozen_mid": neg_groups,
        }

    # 6. Attack Suites on both 40x15 and 20x6 + Prompt Filter TPR/FPR Benchmark
    attacks_40x15 = run_attack_suite(rows_b, max_rep=15)
    attacks_20x6 = run_attack_suite(rows_b_20x6, max_rep=6)
    filter_benchmark = evaluate_prompt_filter_benchmark()

    # 7. Cross-Session Verification (A [t=0h] -> E [t=+6.5h]), Out-of-Sample Jitter on E, and Side-Channel Ablation
    cross_session_ae = evaluate_cross_session_a_to_e(rows_a_fresh, rows_e, fmap)
    oos_jitter_e = evaluate_out_of_sample_jitter_e(rows_e, frozen_transfer_results)
    side_channel_ablation = {
        label: {
            "side_jsd_only": {
                "auc": r_obj["roc_raw"]["side_jsd"]["auc"],
                "eer_linear_pct": round(100.0 * r_obj["roc_raw"]["side_jsd"]["eer_linear_raw"], 2),
                "loo_family": f"{r_obj['loo_family']['side_jsd']['correct']}/{r_obj['loo_family']['side_jsd']['total']} ({r_obj['loo_family']['side_jsd']['accuracy_pct']}%)",
            },
            "pure_color_energy_reg": {
                "auc": r_obj["roc_raw"]["energy_reg"]["auc"],
                "eer_linear_pct": round(100.0 * r_obj["roc_raw"]["energy_reg"]["eer_linear_raw"], 2),
                "loo_family": f"{r_obj['loo_family']['energy_reg']['correct']}/{r_obj['loo_family']['energy_reg']['total']} ({r_obj['loo_family']['energy_reg']['accuracy_pct']}%)",
            },
            "pure_color_hex_jsd": {
                "auc": r_obj["roc_raw"]["hex_jsd"]["auc"],
                "eer_linear_pct": round(100.0 * r_obj["roc_raw"]["hex_jsd"]["eer_linear_raw"], 2),
                "loo_family": f"{r_obj['loo_family']['hex_jsd']['correct']}/{r_obj['loo_family']['hex_jsd']['total']} ({r_obj['loo_family']['hex_jsd']['accuracy_pct']}%)",
            },
        }
        for label, r_obj in [
            ("A_with_legacy", res_a_leg),
            ("A_fresh_raw_only", res_a_fresh),
            ("B_40x15", res_b_full),
            ("B_20x6", res_b_20x6),
            ("E_20x6", res_e_heldout),
        ]
    }

    summary = {
        "analysis_protocol": dict(an.ANALYSIS_PROTOCOL),
        "provenance": {
            "total_jsonl_lines": total_lines,
            "total_unique_records": unique_records,
            "overlap_A_B_identical_records": overlap_ab_identical,
            "overlap_B_E_target_models": overlap_be_targets,
            "overlap_A_E_target_models": overlap_ae_targets,
            "overlap_A_E_identical_records": overlap_ae_identical,
            "source_code_and_config_sha256": {
                f: sha256_file(f)
                for f in [
                    "collect.py",
                    "analyze.py",
                    "reproduce_all.py",
                    "config/prompts.json",
                    "config/prompts.paraphrase.json",
                    "config/prompts.bruckner_baseline.json",
                    "config/family_map.json",
                    "config/targets.exp_40u15r.json",
                    "config/targets.heldout_confirm.json",
                ]
            },
            "datasets": {
                "A_census_56models": {"rows": len(rows_a_leg), "valid": sum(1 for r in rows_a_leg if r["parsed"]["status"] == "valid"), "sha256": sha_a},
                "B_dev_40u15r": {"rows": len(rows_b), "valid": sum(1 for r in rows_b if r["parsed"]["status"] == "valid"), "sha256": sha_b},
                "C_paraphrase": {"rows": len(rows_c), "valid": sum(1 for r in rows_c if r["parsed"]["status"] == "valid"), "sha256": sha_c},
                "D_bruckner_baseline": {"rows": len(rows_d), "valid": sum(1 for r in rows_d if r["parsed"]["status"] == "valid"), "sha256": sha_d, "input_tokens": tok_d_in, "output_tokens": tok_d_out},
                "E_non_B_fresh_confirm": {"rows": len(rows_e), "valid": sum(1 for r in rows_e if r["parsed"]["status"] == "valid"), "sha256": sha_e},
                "B_20x6_paired_subset": {"rows": len(rows_b_20x6), "valid": sum(1 for r in rows_b_20x6 if r["parsed"]["status"] == "valid"), "input_tokens": tok_b_in, "output_tokens": tok_b_out},
            },
        },
        "dataset_A_56models": {
            "n_genuine": res_a_leg["n_genuine"],
            "n_impostor_raw": res_a_leg["n_impostor_raw"],
            "n_impostor_cross_sublineage": res_a_leg["n_impostor_cross_sublineage"],
            "n_impostor_cross_family": res_a_leg["n_impostor_cross_family"],
            "with_legacy_reasoning_meta": {
                "roc_raw": res_a_leg["roc_raw"],
                "roc_cross_sublineage": res_a_leg["roc_cross_sublineage"],
                "roc_cross_family": res_a_leg["roc_cross_family"],
                "loo_family": {m: {k: v for k, v in res_a_leg["loo_family"][m].items() if k != "predictions"} for m in METRICS_ALL},
            },
            "fresh_raw_only_no_legacy_meta": {
                "roc_raw": res_a_fresh["roc_raw"],
                "loo_family": {m: {k: v for k, v in res_a_fresh["loo_family"][m].items() if k != "predictions"} for m in METRICS_ALL},
            },
        },
        "dataset_B_40u15r": {
            "roc_raw": res_b_full["roc_raw"],
            "loo_family": {m: {k: v for k, v in res_b_full["loo_family"][m].items() if k != "predictions"} for m in METRICS_ALL},
            "grid_2d_n_by_k": grid_2d_b,
        },
        "dataset_C_paraphrase_matrix": paraphrase_matrix,
        "paired_D_vs_B_20x6": {
            "token_usage_ratio_color_over_baseline": {
                "input_tokens_ratio": round(tok_b_in / max(1, tok_d_in), 3),
                "output_tokens_ratio": round(tok_b_out / max(1, tok_d_out), 3),
                "total_tokens_ratio": round((tok_b_in + tok_b_out) / max(1, tok_d_in + tok_d_out), 3),
            },
            "inter_model_diversity_per_cell_60calls": {
                "bruckner_single_word_mean_unique": mean_uniq_d,
                "color_hex_rgb_mean_unique": mean_uniq_b,
            },
            "orthogonal_2x2_granularity_vs_geometry": {
                "word_discrete_jsd": {
                    "clean_k20_disc_eer_pct": curve_d[20]["mean_eer_pct"],
                    "clean_k8_disc_eer_pct": curve_d[8]["mean_eer_pct"],
                    "loo_family": f"{res_d['loo_family']['hex_jsd']['correct']}/{res_d['loo_family']['hex_jsd']['total']}",
                },
                "color_discrete_hex_jsd": {
                    "clean_k20_disc_eer_pct": curves_b_20x6["hex_jsd"][20]["mean_eer_pct"],
                    "clean_k8_disc_eer_pct": curves_b_20x6["hex_jsd"][8]["mean_eer_pct"],
                    "loo_family": f"{res_b_20x6['loo_family']['hex_jsd']['correct']}/{res_b_20x6['loo_family']['hex_jsd']['total']}",
                    "jitter_pm2_frr_mid_pct": attacks_20x6["uniform_jitter"]["±2"]["hex_jsd"]["frr_midpoint_pct"],
                    "jitter_pm8_frr_mid_pct": attacks_20x6["uniform_jitter"]["±8"]["hex_jsd"]["frr_midpoint_pct"],
                },
                "color_3d_energy_reg": {
                    "clean_k20_disc_eer_pct": curves_b_20x6["energy_reg"][20]["mean_eer_pct"],
                    "clean_k8_disc_eer_pct": curves_b_20x6["energy_reg"][8]["mean_eer_pct"],
                    "loo_family": f"{res_b_20x6['loo_family']['energy_reg']['correct']}/{res_b_20x6['loo_family']['energy_reg']['total']}",
                    "jitter_pm2_frr_mid_pct": attacks_20x6["uniform_jitter"]["±2"]["energy_reg"]["frr_midpoint_pct"],
                    "jitter_pm8_frr_mid_pct": attacks_20x6["uniform_jitter"]["±8"]["energy_reg"]["frr_midpoint_pct"],
                },
                "color_3d_robust_manifold": {
                    "clean_k20_disc_eer_pct": curves_b_20x6["robust_manifold"][20]["mean_eer_pct"],
                    "clean_k8_disc_eer_pct": curves_b_20x6["robust_manifold"][8]["mean_eer_pct"],
                    "loo_family": f"{res_b_20x6['loo_family']['robust_manifold']['correct']}/{res_b_20x6['loo_family']['robust_manifold']['total']}",
                    "jitter_pm2_frr_mid_pct": attacks_20x6["uniform_jitter"]["±2"]["robust_manifold"]["frr_midpoint_pct"],
                    "jitter_pm8_frr_mid_pct": attacks_20x6["uniform_jitter"]["±8"]["robust_manifold"]["frr_midpoint_pct"],
                },
            },
            "mcnemar_exact_tests_vs_baseline": mcnemar_stats,
            "request_and_average_token_budget_curve": token_cost_curve,
            "bruckner_baseline_hex_jsd": {
                "roc": res_d["roc_raw"]["hex_jsd"],
                "loo_family": {k: v for k, v in res_d["loo_family"]["hex_jsd"].items() if k != "predictions"},
            },
            "color_manifold_metrics": {
                m: {
                    "roc": res_b_20x6["roc_raw"][m],
                    "loo_family": {k: v for k, v in res_b_20x6["loo_family"][m].items() if k != "predictions"},
                }
                for m in ATTACK_METRICS
            },
        },
        "dataset_E_heldout_confirmation": {
            "frozen_transfer_from_dev_B": frozen_transfer_results,
            "out_of_sample_jitter_transfer": oos_jitter_e,
            "combined_20models_dev_plus_heldout": {
                "n_genuine": res_be_combined20["n_genuine"],
                "n_impostor_raw": res_be_combined20["n_impostor_raw"],
                "n_impostor_cross_sublineage": res_be_combined20["n_impostor_cross_sublineage"],
                "metrics": {
                    m: {
                        "roc_raw": res_be_combined20["roc_raw"][m],
                        "roc_cross_sublineage": {**res_be_combined20["roc_cross_sublineage"][m], **res_be_combined20["roc_cross_sublineage"]},
                        "loo_family": {k: v for k, v in res_be_combined20["loo_family"][m].items() if k != "predictions"},
                    }
                    for m in ATTACK_METRICS
                },
            },
        },
        "cross_session_A_to_E": cross_session_ae,
        "side_channel_ablation": side_channel_ablation,
        "attack_suites": {
            "B_40x15": attacks_40x15,
            "B_20x6": attacks_20x6,
        },
        "prompt_filter_benchmark": filter_benchmark,
    }

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"reproduce_all.py finished successfully -> {out_file}")


if __name__ == "__main__":
    main()
