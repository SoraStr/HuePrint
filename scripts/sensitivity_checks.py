#!/usr/bin/env python3
"""Offline sensitivity, post-hoc format parity, pair-eligibility, and unified stability checks.

Recomputes from the 12 frozen corpus JSONL logs and archived configs without API calls:
1. Post-hoc S3 2-color-probe exact rational MMD-U comparison (hex_random, hex_favorite vs.
   brk_rand_color, brk_fav_color across 20 endpoints, 3v3 and 15v15, raw strings retained).
2. Dataset A (56 endpoints, 8x6) archived within-endpoint eligibility vs. deployment-realizable
   side-independent pair eligibility (min 2 valid parses per side on shared cells).
3. Study S1 nine standard endpoints (no reasoning.effort override) on CF0 -> CF21 under
   frozen B3v3 raw regularized-energy threshold (1/72 = 1.39% FAR vs. 1/52 open-set slice).
4. Study S4a and S1 (CF0 -> OR21) side-channel ablations (metadata-only removal vs. metadata
   plus numeric_only->upper merge).
5. Mixed-routing analytical two-point-mass RGB100 verification (distance 100, delta_0 = 15,
   lambda = 0.2: 4% unnormalized numerator vs. 23/175 = 13.14% regularized population score).
6. Unified F(d, h) = (d - h) / (d + delta_0) Lipschitz perturbation checks (2*eps/delta_0
   single-sided, 4*eps/delta_0 two-sided) across V, signed U, and clipped U ratios, including
   negative U values, zero-crossing clipping, and zero-distance clouds.
"""
from __future__ import annotations

import argparse
import collections
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze as an
from reproduce_all import load_jsonl_clean
from hueprint_audit import baselines, core, experiments
from perturbation_calibration_analysis import decontaminate_grouped, decontaminate_rows

DEFAULT_OUT = ROOT / "results" / "diagnostics" / "sensitivity_checks.json"
MANIFEST_PATH = ROOT / "results" / "integrity_manifest.json"
TABLE2_METRICS = (
    "energy_norm",
    "energy_reg",
    "hybrid",
    "hex_jsd",
    "robust_manifold",
    "voxel_jsd",
    "side_jsd",
)


def offline_guard(event: str, args) -> None:
    if event in (
        "socket.connect",
        "socket.connect_ex",
        "socket.getaddrinfo",
        "socket.sendto",
        "subprocess.Popen",
    ):
        raise RuntimeError("Offline-only analysis blocked event: " + event)


def verify_protected() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["files"]
    for rel, expected in manifest.items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Protected file mutated: {rel}")
    return len(manifest)


def compute_s3_two_color_posthoc(s3_color: list[dict], s3_word: list[dict]) -> dict:
    color_cells = ("hex_random|en", "hex_favorite|en")
    word_cells = ("brk_rand_color|en", "brk_fav_color|en")
    budgets = {}
    for n_total in (6, 30):
        half = n_total // 2
        arms = {}
        for arm_name, rows, cells in (
            ("color_hex", s3_color, color_cells),
            ("word_color", s3_word, word_cells),
        ):
            sub = [
                r for r in rows
                if int(r["rep"]) <= n_total and f"{r['task_id']}|{r['lang']}" in cells
            ]
            ref = core.group([r for r in sub if int(r["rep"]) % 2 == 1])
            qry = core.group([r for r in sub if int(r["rep"]) % 2 == 0])
            ids = sorted(set(ref) & set(qry))
            assert len(ids) == 20
            mat = [[Fraction(0, 1) for _ in range(len(ids))] for _ in range(len(ids))]
            for i, ti in enumerate(ids):
                for j, tj in enumerate(ids):
                    cell_sum = Fraction(0, 1)
                    for ck in cells:
                        x = [r.get("raw_text") or "" for r in ref[ti][ck]]
                        y = [r.get("raw_text") or "" for r in qry[tj][ck]]
                        assert len(x) == half and len(y) == half
                        cell_sum += baselines.exact_mmd_u_cell(x, y)
                    mat[i][j] = cell_sum / len(cells)
            st = baselines.exact_mmd_stats(mat)
            arms[arm_name] = {
                "cells": list(cells),
                "n_models": len(ids),
                "n_genuine": st["n_genuine"],
                "n_impostor": st["n_impostor"],
                "auc_raw": st["auc"],
                "auc_4dp": round(st["auc"], 4),
                "eer_linear_raw": st["eer"],
                "eer_linear_pct": round(100.0 * st["eer"], 2),
                "eer_discrete_raw": st["eer_discrete"],
                "eer_discrete_pct": round(100.0 * st["eer_discrete"], 2),
                "top1_raw": st["top1"],
                "genuine_mean": st["genuine_mean"],
                "impostor_mean": st["impostor_mean"],
            }
        budgets[f"N{n_total}_{half}v{half}"] = arms
    return {
        "protocol": (
            "Post-hoc 2-task matched-concept check on Study S3 raw responses (20 endpoints, "
            "20 genuine pairs, 380 directed impostor pairs, odd/even repetition split, exact "
            "rational one-hot MMD-U retaining empty and invalid strings, cell-averaged before ROC)."
        ),
        "budgets": budgets,
    }


def compute_dataset_a_pair_eligibility(rows_a_fresh: list[dict], fmap: dict) -> dict:
    by_tc: dict[str, dict[str, list[dict]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    cells_set = set()
    for r in rows_a_fresh:
        if abs(float(r.get("temperature", 1.0)) - 1.0) < 1e-4:
            ck = f"{r['task_id']}|{r['lang']}"
            by_tc[r["target_id"]][ck].append(r)
            cells_set.add(ck)

    tids = sorted(by_tc)
    all_cells = sorted(cells_set)
    odd_hist: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    even_hist: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    odd_ind: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    even_ind: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    asymmetric_endpoints = []

    for t in tids:
        only_odd, only_even = [], []
        for c in all_cells:
            rs = by_tc[t][c]
            co = an.summarize_cell_samples([r for r in rs if int(r["rep"]) % 2 == 1])
            ce = an.summarize_cell_samples([r for r in rs if int(r["rep"]) % 2 == 0])
            if co["n_valid"] >= 2 and ce["n_valid"] >= 2:
                odd_hist[t][c] = co
                even_hist[t][c] = ce
            if co["n_valid"] >= 2:
                odd_ind[t][c] = co
            if ce["n_valid"] >= 2:
                even_ind[t][c] = ce
            if (co["n_valid"] >= 2) != (ce["n_valid"] >= 2):
                (only_odd if co["n_valid"] >= 2 else only_even).append(
                    {"cell": c, "n_valid_odd": co["n_valid"], "n_valid_even": ce["n_valid"]}
                )
        if only_odd or only_even:
            asymmetric_endpoints.append({
                "target_id": t,
                "odd_only_ge2": only_odd,
                "even_only_ge2": only_even,
            })

    changed_genuine = 0
    changed_negatives = 0

    def eval_rule(odd_map: dict, even_map: dict) -> dict:
        gen = {m: [] for m in TABLE2_METRICS}
        imp_all = {m: [] for m in TABLE2_METRICS}
        imp_sub = {m: [] for m in TABLE2_METRICS}
        imp_fam = {m: [] for m in TABLE2_METRICS}
        min_cells = len(all_cells)
        for i, ta in enumerate(tids):
            for j, tb in enumerate(tids):
                sh = sorted(set(odd_map[ta]) & set(even_map[tb]))
                assert sh, (ta, tb)
                min_cells = min(min_cells, len(sh))
                cd = {c: an.compute_cell_distance(odd_map[ta][c], even_map[tb][c]) for c in sh}
                if i == j:
                    for m in TABLE2_METRICS:
                        gen[m].append(sum(cd[c][m] for c in sh) / len(sh))
                else:
                    sub_diff = (fmap.get(ta) or {}).get("sublineage", ta) != (fmap.get(tb) or {}).get("sublineage", tb)
                    fam_diff = (fmap.get(ta) or {}).get("family", ta) != (fmap.get(tb) or {}).get("family", tb)
                    for m in TABLE2_METRICS:
                        val = sum(cd[c][m] for c in sh) / len(sh)
                        imp_all[m].append(val)
                        if sub_diff:
                            imp_sub[m].append(val)
                        if fam_diff:
                            imp_fam[m].append(val)
        out_m = {}
        for m in TABLE2_METRICS:
            ra = an.compute_roc_eer(gen[m], imp_all[m])
            rs = an.compute_roc_eer(gen[m], imp_sub[m])
            rf = an.compute_roc_eer(gen[m], imp_fam[m])
            out_m[m] = {
                "auc_raw": ra["auc_raw"],
                "auc_4dp": round(ra["auc_raw"], 4),
                "eer_discrete_raw": ra["eer_raw"],
                "eer_discrete_pct": round(100.0 * ra["eer_raw"], 2),
                "eer_linear_raw": ra["eer_linear_raw"],
                "eer_linear_pct": round(100.0 * ra["eer_linear_raw"], 2),
                "cross_sublineage_eer_linear_raw": rs["eer_linear_raw"],
                "cross_sublineage_eer_linear_pct": round(100.0 * rs["eer_linear_raw"], 2),
                "cross_family_eer_linear_raw": rf["eer_linear_raw"],
                "cross_family_eer_linear_pct": round(100.0 * rf["eer_linear_raw"], 2),
            }
        return {
            "n_genuine": len(gen[TABLE2_METRICS[0]]),
            "n_impostor_all": len(imp_all[TABLE2_METRICS[0]]),
            "n_impostor_cross_sublineage": len(imp_sub[TABLE2_METRICS[0]]),
            "n_impostor_cross_family": len(imp_fam[TABLE2_METRICS[0]]),
            "min_shared_cells": min_cells,
            "metrics": out_m,
        }

    for i, ta in enumerate(tids):
        for j, tb in enumerate(tids):
            sh_h = sorted(set(odd_hist[ta]) & set(even_hist[tb]))
            sh_i = sorted(set(odd_ind[ta]) & set(even_ind[tb]))
            if sh_h != sh_i:
                if i == j:
                    changed_genuine += 1
                else:
                    changed_negatives += 1

    hist_res = eval_rule(odd_hist, even_hist)
    ind_res = eval_rule(odd_ind, even_ind)
    return {
        "changed_genuine_pairs": changed_genuine,
        "total_genuine_pairs": 56,
        "changed_directed_negative_pairs": changed_negatives,
        "total_directed_negative_pairs": 3080,
        "asymmetric_half_eligibility_endpoints": asymmetric_endpoints,
        "historical_both_halves_per_target": hist_res,
        "side_independent_pair_intersection": ind_res,
    }


def compute_s1_standard9_audit() -> dict:
    pa = json.loads((ROOT / "results" / "protocol_audit" / "protocol_hyperparameter_audit.json").read_text(encoding="utf-8"))
    comp = json.loads((ROOT / "results" / "benchmark" / "comparisons.json").read_text(encoding="utf-8"))
    cal = json.loads((ROOT / "results" / "benchmark" / "calibration_results.json").read_text(encoding="utf-8"))["operating_points"]
    tau_b3 = next(
        r["threshold"] for r in cal
        if r["scenario"] == "B3v3_development"
        and r["metric"] == "energy_reg"
        and r["variant"] == "raw"
        and r["threshold_kind"] == "tau_mid"
    )
    std9_ids = pa["s1_stratified"]["CF0_CF21"]["standard_9_no_reasoning_override"]["ids"]
    ids14 = comp["S1_CF0_CF21_6v6"]["ids"]
    mat14 = np.asarray(comp["S1_CF0_CF21_6v6"]["matrices"]["energy_reg"], dtype=float)
    ix = [ids14.index(t) for t in std9_ids]
    sub = mat14[np.ix_(ix, ix)]
    false_accepts = [
        {"reference": std9_ids[i], "query": std9_ids[j], "score": float(sub[i, j])}
        for i in range(len(std9_ids))
        for j in range(len(std9_ids))
        if i != j and sub[i, j] <= tau_b3
    ]
    false_rejects = [
        {"endpoint": std9_ids[i], "score": float(sub[i, i])}
        for i in range(len(std9_ids))
        if sub[i, i] > tau_b3
    ]
    st = core.stats(sub)
    op = core.operating(sub, tau_b3)
    return {
        "scenario": "S1_CF0_CF21_6v6",
        "subgroup": "standard_9_no_reasoning_override",
        "ids": std9_ids,
        "n_genuine": 9,
        "n_directed_impostors": 72,
        "frozen_b3v3_tau_mid_raw": tau_b3,
        "eer_linear_raw": st["eer"],
        "frr_raw": op["frr"],
        "far_raw": op["far"],
        "far_pct": round(100.0 * op["far"], 2),
        "false_rejects": false_rejects,
        "false_accepts": false_accepts,
    }


def compute_s4a_and_s1_side_ablations(data: dict) -> dict:
    def eval_split(r_dict: dict, q_dict: dict) -> dict:
        _, mats, _ = core.matrix(r_dict, q_dict)
        return {
            m: {k: float(core.stats(mats[m])[k]) for k in ("auc", "eer", "genuine_mean", "impostor_mean")}
            for m in ("side_jsd", "hybrid", "hybrid_reg", "energy_reg")
        }

    s4_orig = eval_split(*experiments.within(data["S4a"], min_split=1))
    s4_no_env = eval_split(
        *experiments.within(
            decontaminate_rows(data["S4a"], merge_numeric_case=False, strip_envelope_telemetry=True),
            min_split=1,
        )
    )
    s4_pure = eval_split(
        *experiments.within(
            decontaminate_rows(data["S4a"], merge_numeric_case=True, strip_envelope_telemetry=True),
            min_split=1,
        )
    )

    cf0_g, _, or21_g = experiments.make_s1(data)
    s1_orig = eval_split(cf0_g, or21_g)
    s1_no_env = eval_split(
        decontaminate_grouped(cf0_g, merge_numeric_case=False, strip_envelope_telemetry=True),
        decontaminate_grouped(or21_g, merge_numeric_case=False, strip_envelope_telemetry=True),
    )
    s1_pure = eval_split(
        decontaminate_grouped(cf0_g, merge_numeric_case=True, strip_envelope_telemetry=True),
        decontaminate_grouped(or21_g, merge_numeric_case=True, strip_envelope_telemetry=True),
    )
    return {
        "S4a_5v5_min1": {
            "archived": s4_orig,
            "content_only_no_envelope": s4_no_env,
            "pure_content_syntax": s4_pure,
        },
        "S1_CF0_to_OR21_6v6": {
            "archived": s1_orig,
            "content_only_no_envelope": s1_no_env,
            "pure_content_syntax": s1_pure,
        },
    }


def compute_mixed_routing_point_mass_example() -> dict:
    dist = Fraction(100, 1)
    delta0 = Fraction(15, 1)
    lam = Fraction(1, 5)  # 0.2
    e2_full = 2 * dist  # 200
    e2_mix = (lam ** 2) * e2_full  # 8
    d_p_q = (1 - lam) * 0 + lam * dist  # 20
    reg_full = e2_full / (2 * (dist + delta0))  # 100 / 115 = 20 / 23
    reg_mix = e2_mix / (2 * (d_p_q + delta0))  # 8 / 70 = 4 / 35
    reg_ratio = reg_mix / reg_full  # 23 / 175
    return {
        "point_separation_rgb100": float(dist),
        "delta0_rgb100": float(delta0),
        "lambda_fallback": float(lam),
        "unnormalized_e2_full": float(e2_full),
        "unnormalized_e2_mix": float(e2_mix),
        "unnormalized_ratio_exact": str(e2_mix / e2_full),
        "unnormalized_ratio_pct": round(100.0 * float(e2_mix / e2_full), 2),
        "regularized_full_exact": str(reg_full),
        "regularized_full": float(reg_full),
        "regularized_mix_exact": str(reg_mix),
        "regularized_mix": float(reg_mix),
        "regularized_ratio_exact": str(reg_ratio),
        "regularized_ratio_raw": float(reg_ratio),
        "regularized_ratio_pct": round(100.0 * float(reg_ratio), 2),
    }


def eval_v_and_u_scores(u: np.ndarray, v: np.ndarray, delta0: float = 15.0) -> dict[str, float]:
    n, m = len(u), len(v)
    assert n >= 2 and m >= 2
    d_uv = float(np.linalg.norm(u[:, None, :] - v[None, :, :], axis=-1).mean())
    d_uu_v = float(np.linalg.norm(u[:, None, :] - u[None, :, :], axis=-1).mean())
    d_vv_v = float(np.linalg.norm(v[:, None, :] - v[None, :, :], axis=-1).mean())
    d_uu_u = d_uu_v * n / (n - 1)
    d_vv_u = d_vv_v * m / (m - 1)
    h_v = 0.5 * (d_uu_v + d_vv_v)
    h_u = 0.5 * (d_uu_u + d_vv_u)
    assert -1e-12 <= h_v <= 2.0 * d_uv + 1e-12
    assert -1e-12 <= h_u <= 2.0 * d_uv + 1e-12
    f_v = max(0.0, d_uv - h_v) / (d_uv + delta0) if d_uv >= 1e-12 else 0.0
    f_u_signed = (d_uv - h_u) / (d_uv + delta0)
    f_u_clipped = max(0.0, d_uv - h_u) / (d_uv + delta0)
    return {
        "v_reg": f_v,
        "u_signed": f_u_signed,
        "u_clipped": f_u_clipped,
        "u_raw_num": 2.0 * (d_uv - h_u),
    }


def check_unified_lipschitz_bounds(delta0: float = 15.0) -> dict:
    rng = np.random.default_rng(20261118)
    max_one_ratio = {"v_reg": 0.0, "u_signed": 0.0, "u_clipped": 0.0}
    max_two_ratio = {"v_reg": 0.0, "u_signed": 0.0, "u_clipped": 0.0}
    negative_u_cases = 0
    sign_crossing_cases = 0

    def random_disp(shape: tuple[int, int], eps: float) -> np.ndarray:
        dirs = rng.normal(size=shape)
        norms = np.linalg.norm(dirs, axis=-1, keepdims=True)
        radii = rng.uniform(0.0, eps, size=(shape[0], 1))
        return dirs / np.maximum(norms, 1e-12) * radii

    # 1. Randomized arbitrary-direction clouds + explicit identical-support negative-U clouds
    fixtures = []
    for n, m in ((2, 2), (2, 3), (3, 3), (4, 7)):
        for k in range(120):
            if k < 40:
                # Near-identical binary clouds to exercise negative U and sign crossings across 0
                pts = np.array([[10.0, 20.0, 30.0], [80.0, 20.0, 30.0]])
                u = pts[rng.integers(0, 2, size=n)].copy()
                v = pts[rng.integers(0, 2, size=m)].copy()
            elif k == 40:
                # Exact zero-distance constant clouds (d_UV = 0)
                u = np.full((n, 3), 50.0)
                v = np.full((m, 3), 50.0)
            else:
                u = rng.uniform(0.0, 100.0, size=(n, 3))
                v = rng.uniform(0.0, 100.0, size=(m, 3))
            eps = float(rng.uniform(0.05, 8.0))
            fixtures.append((u, v, eps))

    for u, v, eps in fixtures:
        v1 = v + random_disp(v.shape, eps)
        u1 = u + random_disp(u.shape, eps)
        s0 = eval_v_and_u_scores(u, v, delta0)
        s_one = eval_v_and_u_scores(u, v1, delta0)
        s_two = eval_v_and_u_scores(u1, v1, delta0)

        if s0["u_raw_num"] < -1e-12 or s_one["u_raw_num"] < -1e-12:
            negative_u_cases += 1
        if (s0["u_raw_num"] < -1e-12 and s_one["u_raw_num"] > 1e-12) or (
            s0["u_raw_num"] > 1e-12 and s_one["u_raw_num"] < -1e-12
        ):
            sign_crossing_cases += 1

        one_bound = 2.0 * eps / delta0
        two_bound = 4.0 * eps / delta0
        for key in ("v_reg", "u_signed", "u_clipped"):
            d1 = abs(s_one[key] - s0[key])
            d2 = abs(s_two[key] - s0[key])
            assert d1 <= one_bound + 1e-12, (key, d1, one_bound)
            assert d2 <= two_bound + 1e-12, (key, d2, two_bound)
            max_one_ratio[key] = max(max_one_ratio[key], d1 / one_bound)
            max_two_ratio[key] = max(max_two_ratio[key], d2 / two_bound)
        for st in (s0, s_one, s_two):
            assert 0.0 <= st["v_reg"] < 1.0
            assert 0.0 <= st["u_clipped"] < 1.0

    assert negative_u_cases > 0 and sign_crossing_cases > 0
    return {
        "fixtures_tested": len(fixtures),
        "negative_u_fixtures": negative_u_cases,
        "sign_crossing_fixtures": sign_crossing_cases,
        "zero_distance_tested": True,
        "single_sided_bound_formula": "2 * eps / delta_0",
        "two_sided_bound_formula": "4 * eps / delta_0",
        "max_observed_over_single_sided_bound": max_one_ratio,
        "max_observed_over_two_sided_bound": max_two_ratio,
        "clipped_strictly_less_than_one": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out_path = (
        (args.output / "sensitivity_checks.json")
        if (args.output.is_dir() or args.output.suffix != ".json")
        else args.output
    )
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_protected = verify_protected()
    sys.addaudithook(offline_guard)

    rows_a_fresh, _, _ = load_jsonl_clean("data/census_40models.jsonl", apply_legacy_reasoning_meta=False)
    fmap = json.loads((ROOT / "config" / "family_map.json").read_text(encoding="utf-8"))["families"]
    data = {
        k: core.load(ROOT / experiments.FILES[k])
        for k in ("B", "E", "S1_CF21", "S1_OR21", "S3_color", "S3_word", "S4a")
    }

    report = {
        "suite": "sensitivity_checks_v1",
        "protected_files_verified": n_protected,
        "s3_two_color_probe_posthoc": compute_s3_two_color_posthoc(data["S3_color"], data["S3_word"]),
        "dataset_a_pair_eligibility_sensitivity": compute_dataset_a_pair_eligibility(rows_a_fresh, fmap),
        "s1_standard9_cf0_cf21_audit": compute_s1_standard9_audit(),
        "side_channel_stepwise_ablations": compute_s4a_and_s1_side_ablations(data),
        "mixed_routing_point_mass_example": compute_mixed_routing_point_mass_example(),
        "unified_v_and_u_lipschitz_checks": check_unified_lipschitz_bounds(),
    }

    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    verify_protected()
    shown = out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path
    print(f"Wrote {shown}")


if __name__ == "__main__":
    main()
