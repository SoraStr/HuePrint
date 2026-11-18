#!/usr/bin/env python3
"""Offline perturbation tightness, S1 open-set, side-channel decontamination, and bootstrap diagnostics.

Computes and archives exact supplementary metrics without mutating any protected
raw logs or historical baseline outputs:
1. Proposition 1 tightness equality verification (uniform-on-support counterexample vs. proportional iff condition).
2. Study S1 calibration overlap (1,200/1,200 B rows) and open-set heldout4 cross-cohort FAR/FRR (52 vs. 12 impostors).
3. Pure-text syntax decontamination of D_side and D_hyb (merging numeric_only->upper and stripping usage.reasoning_tokens).
4. Completion-cap inventory (16-256 tokens) and Dataset A min_split=1 vs. min_split=2 valid-parse conditioning sensitivity.
5. Enrollment bootstrap self-dispersion downward bias ratios (mu_self / G) and centered shift EERs.
"""
from __future__ import annotations

import copy
import glob
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze as an
from reproduce_all import load_jsonl_clean
from hueprint_audit import core, experiments

OUT_DIR = ROOT / "results" / "diagnostics"


def psi_bound(t: float) -> float:
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    return 0.5 * math.log2(2.0 / (2.0 - t)) + 0.5 * (1.0 - t) * math.log2(2.0 * (1.0 - t) / (2.0 - t)) + 0.5 * t


def jsd_dict(p: dict, q: dict) -> float:
    keys = set(p) | set(q)
    acc = 0.0
    for k in keys:
        pk = p.get(k, 0.0)
        qk = q.get(k, 0.0)
        mk = 0.5 * (pk + qk)
        if pk > 0.0:
            acc += 0.5 * pk * math.log2(pk / mk)
        if qk > 0.0:
            acc += 0.5 * qk * math.log2(qk / mk)
    return acc


def verify_theorem1_tightness() -> dict:
    # Interior cube jitter a=1 around (100, 100, 100): 27 equiprobable outcomes
    cube = [(100 + dx, 100 + dy, 100 + dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]
    q_jitter = {c: 1.0 / 27.0 for c in cube}

    # Case 1: Non-uniform 2-point P_ref where Q_jitter IS uniform on supp(P_ref)
    p_ref_nonunif = {(100, 100, 100): 0.9, (101, 100, 100): 0.1}
    t_r2 = 25.0 / 27.0
    jsd_r2 = jsd_dict(p_ref_nonunif, q_jitter)
    psi_r2 = psi_bound(t_r2)

    # Case 2: Point-mass P_ref (r=1, a=1) where Q_jitter(x) = (1-t) P_ref(x) on supp(P_ref)
    p_ref_point = {(100, 100, 100): 1.0}
    t_r1 = 26.0 / 27.0
    jsd_r1 = jsd_dict(p_ref_point, q_jitter)
    psi_r1 = psi_bound(t_r1)

    assert jsd_r2 > psi_r2 + 0.02, "Expected strict inequality on non-uniform P_ref"
    assert abs(jsd_r1 - psi_r1) < 1e-15, "Expected exact equality on point-mass P_ref"
    return {
        "nonuniform_pref_uniform_q_on_support": {
            "r": 2,
            "a": 1,
            "t": t_r2,
            "jsd_actual": jsd_r2,
            "psi_t": psi_r2,
            "gap": jsd_r2 - psi_r2,
            "equality_holds": False,
        },
        "point_mass_pref_proportional_q_on_support": {
            "r": 1,
            "a": 1,
            "t": t_r1,
            "jsd_actual": jsd_r1,
            "psi_t": psi_r1,
            "gap": abs(jsd_r1 - psi_r1),
            "equality_holds": True,
        },
    }


def audit_s1_overlap_and_openset(data: dict) -> dict:
    cf0_g, cf21_g, or21_g = experiments.make_s1(data)
    b_keys = {r["trial_key"] for r in experiments.b20(data["B"])}
    cf0_keys = {r["trial_key"] for cs in cf0_g.values() for rs in cs.values() for r in rs}
    shared_b_keys = len(b_keys & cf0_keys)
    assert shared_b_keys == 1200

    comp = json.loads((ROOT / "results" / "benchmark" / "comparisons.json").read_text(encoding="utf-8"))
    cal_rows = json.loads((ROOT / "results" / "benchmark" / "calibration_results.json").read_text(encoding="utf-8"))
    b_ids = set(comp["B20x6"]["ids"])
    e_ids = set(comp["E"]["ids"])

    # Extract frozen thresholds on B3v3 and B6v6
    ops = cal_rows["operating_points"]
    tau_b3_raw = next(
        r["threshold"] for r in ops
        if r["scenario"] == "B3v3_development" and r["metric"] == "energy_reg" and r["variant"] == "raw" and r["threshold_kind"] == "tau_mid"
    )
    tau_b3_self = next(
        r["threshold"] for r in ops
        if r["scenario"] == "B3v3_development" and r["metric"] == "energy_reg" and r["variant"] == "self_alpha1" and r["threshold_kind"] == "tau_mid"
    )
    tau_b6_raw = next(
        r["threshold"] for r in ops
        if r["scenario"] == "B6v6_development" and r["metric"] == "energy_reg" and r["variant"] == "raw" and r["threshold_kind"] == "tau_mid"
    )
    tau_b6_self = next(
        r["threshold"] for r in ops
        if r["scenario"] == "B6v6_development" and r["metric"] == "energy_reg" and r["variant"] == "self_alpha1" and r["threshold_kind"] == "tau_mid"
    )

    _, cf0_details = core.enrollment_mu(cf0_g, 6)
    _, cf21_details = core.enrollment_mu(cf21_g, 6)
    s1_paths = {}
    for scen, ref_g, qry_g, details in [
        ("S1_CF0_CF21_6v6", cf0_g, cf21_g, cf0_details),
        ("S1_CF21_OR21_6v6", cf21_g, or21_g, cf21_details),
        ("S1_CF0_OR21_6v6", cf0_g, or21_g, cf0_details),
    ]:
        entry = comp[scen]
        ids = entry["ids"]
        mat = np.array(entry["matrices"]["energy_reg"], dtype=float)
        mu_mat = core.mu_for_matrix(ref_g, qry_g, ids, details, "energy_reg")
        mat_self = mat - mu_mat

        held_idx = [i for i, t in enumerate(ids) if t in e_ids]
        assert len(held_idx) == 4
        gen_held = [mat[i, i] for i in held_idx]
        gen_held_self = [mat_self[i, i] for i in held_idx]

        imp_within12 = [mat[i, j] for i in held_idx for j in held_idx if i != j]
        imp_openset52 = [(ids[i], ids[j], float(mat[i, j]), float(mat_self[i, j])) for i in held_idx for j in range(len(ids)) if i != j]

        s1_paths[scen] = {
            "heldout4_ids": [ids[i] for i in held_idx],
            "n_genuine": 4,
            "n_impostor_within4x3": len(imp_within12),
            "n_impostor_openset4x13": len(imp_openset52),
            "b3v3_raw": {
                "threshold": tau_b3_raw,
                "frr": sum(v > tau_b3_raw for v in gen_held) / 4.0,
                "far_within12": sum(v <= tau_b3_raw for v in imp_within12) / 12.0,
                "far_openset52": sum(x[2] <= tau_b3_raw for x in imp_openset52) / 52.0,
                "openset_false_accept_pairs": [
                    {"ref": r, "qry": q, "score": s} for r, q, s, _ in imp_openset52 if s <= tau_b3_raw
                ],
            },
            "b3v3_self": {
                "threshold": tau_b3_self,
                "frr": sum(v > tau_b3_self for v in gen_held_self) / 4.0,
                "far_openset52": sum(x[3] <= tau_b3_self for x in imp_openset52) / 52.0,
            },
            "b6v6_raw": {
                "threshold": tau_b6_raw,
                "frr": sum(v > tau_b6_raw for v in gen_held) / 4.0,
                "false_reject_models": [ids[held_idx[k]] for k, v in enumerate(gen_held) if v > tau_b6_raw],
                "far_openset52": sum(x[2] <= tau_b6_raw for x in imp_openset52) / 52.0,
            },
            "b6v6_self": {
                "threshold": tau_b6_self,
                "frr": sum(v > tau_b6_self for v in gen_held_self) / 4.0,
                "far_openset52": sum(x[3] <= tau_b6_self for x in imp_openset52) / 52.0,
            },
        }
    return {
        "cf0_total_rows": len(cf0_keys),
        "cf0_exact_b20x6_calibration_overlap_rows": shared_b_keys,
        "dev10_count": len([t for t in comp["S1_CF0_CF21_6v6"]["ids"] if t in b_ids]),
        "heldout4_count": 4,
        "paths": s1_paths,
    }


def decontaminate_rows(
    rows: list[dict],
    merge_numeric_case: bool = True,
    strip_envelope_telemetry: bool = True,
) -> list[dict]:
    from collect import parse_color_response

    cleaned = []
    for r in rows:
        rc = copy.deepcopy(r)
        if strip_envelope_telemetry:
            rc["explicit_reasoning"] = ""
            if "usage" in rc and isinstance(rc["usage"], dict):
                rc["usage"] = {k: v for k, v in rc["usage"].items() if k != "reasoning_tokens"}
            rc["parsed"] = parse_color_response(
                raw_text=rc.get("raw_text", ""),
                expected_format=rc.get("format", "hex"),
                explicit_reasoning="",
            )
        syn = rc["parsed"].get("syntax")
        if merge_numeric_case and isinstance(syn, dict) and syn.get("letter_case") == "numeric_only":
            syn["letter_case"] = "upper"
        cleaned.append(rc)
    return cleaned


def decontaminate_grouped(
    g: dict,
    merge_numeric_case: bool = True,
    strip_envelope_telemetry: bool = True,
) -> dict:
    return {
        t: {
            c: decontaminate_rows(
                rs,
                merge_numeric_case=merge_numeric_case,
                strip_envelope_telemetry=strip_envelope_telemetry,
            )
            for c, rs in cs.items()
        }
        for t, cs in g.items()
    }


def audit_side_channel_decontamination(data: dict) -> dict:
    a_rows = copy.deepcopy(data["A"])
    for r in a_rows:
        r.pop("legacy_reasoning_meta", None)

    def eval_split(r_dict, q_dict):
        _, mats, _ = core.matrix(r_dict, q_dict)
        return {
            m: {k: float(core.stats(mats[m])[k]) for k in ("auc", "eer", "genuine_mean", "impostor_mean")}
            for m in ("side_jsd", "hybrid", "hybrid_reg", "energy_reg")
        }

    a_orig = eval_split(*experiments.within(a_rows, min_split=2))
    a_no_num = eval_split(*experiments.within(decontaminate_rows(a_rows, merge_numeric_case=True, strip_envelope_telemetry=False), min_split=2))
    a_pure = eval_split(*experiments.within(decontaminate_rows(a_rows), min_split=2))

    b_orig = eval_split(*experiments.within(data["B"], min_split=1))
    b_no_num = eval_split(*experiments.within(decontaminate_rows(data["B"], merge_numeric_case=True, strip_envelope_telemetry=False), min_split=1))
    b_pure = eval_split(*experiments.within(decontaminate_rows(data["B"]), min_split=1))

    s4_orig = eval_split(*experiments.within(data["S4a"], min_split=1))
    s4_no_env = eval_split(*experiments.within(decontaminate_rows(data["S4a"], merge_numeric_case=False, strip_envelope_telemetry=True), min_split=1))
    s4_pure = eval_split(*experiments.within(decontaminate_rows(data["S4a"]), min_split=1))

    cf0_g, _, or21_g = experiments.make_s1(data)
    s1_orig = eval_split(cf0_g, or21_g)
    s1_no_env = eval_split(
        decontaminate_grouped(cf0_g, merge_numeric_case=False, strip_envelope_telemetry=True),
        decontaminate_grouped(or21_g, merge_numeric_case=False, strip_envelope_telemetry=True),
    )
    return {
        "A_fresh_3v3_min2": {"archived": a_orig, "no_numeric_case": a_no_num, "pure_content_syntax": a_pure},
        "B_40x15_8v7_min1": {"archived": b_orig, "no_numeric_case": b_no_num, "pure_content_syntax": b_pure},
        "S4a_5v5_min1": {"archived": s4_orig, "content_only_no_envelope": s4_no_env, "pure_content_syntax": s4_pure},
        "S1_CF0_to_OR21_6v6": {"archived": s1_orig, "content_only_no_envelope": s1_no_env},
    }


def audit_caps_and_conditioning(data: dict) -> dict:
    benchmark_cfgs = [
        "config/targets.census_combined.json",
        "config/targets.cloudflare.json",
        "config/targets.exp_40u15r.json",
        "config/targets.heldout_confirm.json",
        "config/targets.new16.json",
        "extensions/live_validation_20261111/configs/targets.s1_cf_t21d.json",
        "extensions/live_validation_20261111/configs/targets.s1_or_crossgateway.json",
        "extensions/live_validation_20261111/configs/targets.s2_multiprovider.json",
        "extensions/live_validation_20261111/configs/targets.s3_20models_locked64.json",
        "extensions/live_validation_20261111/configs/targets.s4_20models_implicit128.json",
    ]
    caps = set()
    by_file = {}
    for rel in benchmark_cfgs:
        cfg_path = ROOT / rel
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        targets = cfg.get("targets", cfg if isinstance(cfg, list) else [])
        fcaps = sorted({int(t["max_tokens"]) for t in targets if isinstance(t, dict) and "max_tokens" in t})
        if fcaps:
            by_file[rel] = fcaps
            caps.update(fcaps)

    a_rows = copy.deepcopy(data["A"])
    for r in a_rows:
        r.pop("legacy_reasoning_meta", None)
    ar2, aq2 = experiments.within(a_rows, min_split=2)
    ar1, aq1 = experiments.within(a_rows, min_split=1)
    _, m2, c2 = core.matrix(ar2, aq2)
    _, m1, c1 = core.matrix(ar1, aq1)
    return {
        "configured_max_tokens_values": sorted(caps),
        "configured_max_tokens_min_max": [min(caps), max(caps)],
        "max_tokens_by_config": by_file,
        "dataset_A_min_split_sensitivity": {
            "min_split_2": {
                "min_shared_cells": int(c2.min()),
                "energy_norm_eer": float(core.stats(m2["energy_norm"])["eer"]),
                "energy_reg_eer": float(core.stats(m2["energy_reg"])["eer"]),
                "energy_norm_auc": float(core.stats(m2["energy_norm"])["auc"]),
                "energy_reg_auc": float(core.stats(m2["energy_reg"])["auc"]),
            },
            "min_split_1": {
                "min_shared_cells": int(c1.min()),
                "energy_norm_eer": float(core.stats(m1["energy_norm"])["eer"]),
                "energy_reg_eer": float(core.stats(m1["energy_reg"])["eer"]),
                "energy_norm_auc": float(core.stats(m1["energy_norm"])["auc"]),
                "energy_reg_auc": float(core.stats(m1["energy_reg"])["auc"]),
            },
        },
    }


def audit_bootstrap_bias_and_shifts() -> dict:
    cal = json.loads((ROOT / "results" / "benchmark" / "calibration_results.json").read_text(encoding="utf-8"))
    ops = cal["operating_points"]

    def get_op(scen, fit, metric, var):
        return next(
            r for r in ops
            if r["scenario"] == scen and r["calibration"] == fit and r["metric"] == metric and r["variant"] == var and r["threshold_kind"] == "tau_mid"
        )

    ratios = {}
    for scen, fit in [("B3v3_development", "B3v3"), ("E_clean", "B3v3"), ("B6v6_development", "B6v6"), ("B8v7_development", "B8v7")]:
        raw = get_op(scen, fit, "energy_reg", "raw")
        self1 = get_op(scen, fit, "energy_reg", "self_alpha1")
        mu_mean = raw["genuine_mean"] - self1["genuine_mean"]
        ratios[scen] = {
            "genuine_mean": raw["genuine_mean"],
            "mu_self_mean": mu_mean,
            "mu_over_genuine_ratio": mu_mean / raw["genuine_mean"],
        }

    shift_eers = {}
    for scen in ("Bfull_shift8", "Bfull_shift-8"):
        shift_eers[scen] = {
            "energy_reg_raw_eer": get_op(scen, "B8v7", "energy_reg", "raw")["eer"],
            "energy_reg_self_eer": get_op(scen, "B8v7", "energy_reg", "self_alpha1")["eer"],
            "hybrid_reg_raw_eer": get_op(scen, "B8v7", "hybrid_reg", "raw")["eer"],
        }
    return {"bootstrap_mu_vs_genuine": ratios, "shift_reswept_eers": shift_eers}


def offline_guard(event: str, args) -> None:
    if event in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.sendto", "subprocess.Popen"):
        raise RuntimeError("Offline-only analysis blocked event: " + event)


def verify_protected() -> int:
    import hashlib
    manifest = json.loads((ROOT / "results" / "integrity_manifest.json").read_text(encoding="utf-8"))["files"]
    for rel, expected in manifest.items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Protected file mutated: {rel}")
    return len(manifest)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT_DIR / "perturbation_diagnostics.json")
    args = parser.parse_args()
    out_path = (args.output / "perturbation_diagnostics.json") if (args.output.is_dir() or args.output.suffix != ".json") else args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    verify_protected()
    sys.addaudithook(offline_guard)
    data = {k: core.load(ROOT / v) for k, v in experiments.FILES.items()}
    report = {
        "suite": "perturbation_calibration_v1",
        "theorem1_tightness": verify_theorem1_tightness(),
        "s1_overlap_and_openset": audit_s1_overlap_and_openset(data),
        "side_channel_decontamination": audit_side_channel_decontamination(data),
        "caps_and_conditioning": audit_caps_and_conditioning(data),
        "bootstrap_bias_and_shifts": audit_bootstrap_bias_and_shifts(),
    }
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    verify_protected()
    shown = out_path.resolve().relative_to(ROOT) if out_path.resolve().is_relative_to(ROOT) else out_path
    print(f"Wrote {shown}")
    print(json.dumps({
        "thm1_gap_r2": round(report["theorem1_tightness"]["nonuniform_pref_uniform_q_on_support"]["gap"], 6),
        "s1_cf0_cf21_openset52_far": round(report["s1_overlap_and_openset"]["paths"]["S1_CF0_CF21_6v6"]["b3v3_raw"]["far_openset52"] * 100, 2),
        "s1_cf0_or21_b6v6_heldout4_frr": round(report["s1_overlap_and_openset"]["paths"]["S1_CF0_OR21_6v6"]["b6v6_raw"]["frr"] * 100, 2),
        "A_side_pure_auc_eer": [
            round(report["side_channel_decontamination"]["A_fresh_3v3_min2"]["pure_content_syntax"]["side_jsd"]["auc"], 4),
            round(report["side_channel_decontamination"]["A_fresh_3v3_min2"]["pure_content_syntax"]["side_jsd"]["eer"] * 100, 2),
        ],
        "B_side_pure_auc_eer": [
            round(report["side_channel_decontamination"]["B_40x15_8v7_min1"]["pure_content_syntax"]["side_jsd"]["auc"], 4),
            round(report["side_channel_decontamination"]["B_40x15_8v7_min1"]["pure_content_syntax"]["side_jsd"]["eer"] * 100, 2),
        ],
        "S4a_hyb_no_envelope_eer": round(report["side_channel_decontamination"]["S4a_5v5_min1"]["content_only_no_envelope"]["hybrid"]["eer"] * 100, 2),
        "S1_side_genuine_archived_vs_no_env": [
            round(report["side_channel_decontamination"]["S1_CF0_to_OR21_6v6"]["archived"]["side_jsd"]["genuine_mean"], 4),
            round(report["side_channel_decontamination"]["S1_CF0_to_OR21_6v6"]["content_only_no_envelope"]["side_jsd"]["genuine_mean"], 4),
        ],
        "max_tokens_min_max": report["caps_and_conditioning"]["configured_max_tokens_min_max"],
    }, indent=2))


if __name__ == "__main__":
    main()
