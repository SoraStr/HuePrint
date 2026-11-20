#!/usr/bin/env python3
"""Offline empirical diagnostics addressing discrete-vs-continuous attribution,
cross-provider side-channel decontamination, S5c balanced-split variance,
external U-statistic consistency, private prompt-pool subsampling, and
two-stage sequential monitoring cascades.

Reads the 15 SHA-256-locked corpus JSONL files strictly offline (network and
subprocess calls blocked via sys.addaudithook) and verifies protected digests
before and after execution without modifying any archived baseline artifact.
"""
from __future__ import annotations

import argparse
import collections
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import statistics
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze as an
from reproduce_all import load_jsonl_clean
from hueprint_audit import baselines, core, experiments
from perturbation_calibration_analysis import decontaminate_rows

DEFAULT_OUT = ROOT / "results" / "diagnostics" / "operational_diagnostics.json"
MANIFEST_PATH = ROOT / "results" / "integrity_manifest.json"
S5_MANIFEST_PATH = ROOT / "extensions" / "competitor_benchmark_20261120" / "s5_integrity_manifest.json"
S5C_JSONL = ROOT / "extensions" / "competitor_benchmark_20261120" / "data" / "s5c_hueprint_anchor.jsonl"
S5_TARGETS = ROOT / "extensions" / "live_validation_20261111" / "configs" / "targets.s3_20models_locked64.json"


def offline_guard(event: str, args) -> None:
    if event in (
        "socket.connect",
        "socket.connect_ex",
        "socket.getaddrinfo",
        "socket.sendto",
        "subprocess.Popen",
    ):
        raise RuntimeError("Offline-only analysis blocked event: " + event)


def verify_protected() -> tuple[int, int]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["files"]
    for rel, expected in manifest.items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Protected baseline file mutated: {rel}")
    s5_manifest = json.loads(S5_MANIFEST_PATH.read_text(encoding="utf-8"))["files"]
    for rel, expected in s5_manifest.items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Protected S5 file mutated: {rel}")
    return len(manifest), len(s5_manifest)


def load_s5c_dedup() -> list[dict]:
    latest: dict[str, dict] = {}
    order: list[str] = []
    for ln in S5C_JSONL.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        k = r["trial_key"]
        if k not in latest:
            order.append(k)
        latest[k] = r
    return [latest[k] for k in order]


def exact_mmd_pair_matrix(
    ref_g: dict,
    qry_g: dict,
    ids: list[str],
    canonical_hex: bool = False,
) -> list[list[Fraction]]:
    n = len(ids)
    mat = [[Fraction(0, 1) for _ in range(n)] for _ in range(n)]
    for i, ti in enumerate(ids):
        for j, tj in enumerate(ids):
            cells = sorted(set(ref_g[ti]) & set(qry_g[tj]))
            vals = []
            for ck in cells:
                if canonical_hex:
                    x = [r["parsed"]["canonical_hex"] for r in ref_g[ti][ck] if r["parsed"]["status"] == "valid"]
                    y = [r["parsed"]["canonical_hex"] for r in qry_g[tj][ck] if r["parsed"]["status"] == "valid"]
                else:
                    x = [r.get("raw_text") or "" for r in ref_g[ti][ck]]
                    y = [r.get("raw_text") or "" for r in qry_g[tj][ck]]
                if len(x) >= 2 and len(y) >= 2:
                    vals.append(baselines.exact_mmd_u_cell(x, y))
            if not vals:
                raise ValueError(f"No shared >=2 cells for {ti} vs {tj}")
            mat[i][j] = sum(vals, Fraction(0, 1)) / len(vals)
    return mat


def compute_dataset_a_mmd(data_a: list[dict], fmap: dict) -> dict:
    # 1. Exact same cell eligibility as Table 3 (`within(data['A'], 2)`)
    ref_a, qry_a = experiments.within(data_a, 2)
    ids = sorted(set(ref_a) & set(qry_a))
    neg_sub = np.array([[fmap.get(t, {}).get("sublineage", t) != fmap.get(u, {}).get("sublineage", u) for u in ids] for t in ids])
    neg_fam = np.array([[fmap.get(t, {}).get("family", t) != fmap.get(u, {}).get("family", u) for u in ids] for t in ids])
    neg_same_fam = np.array([[t != u and fmap.get(t, {}).get("family", t) == fmap.get(u, {}).get("family", u) for u in ids] for t in ids])

    out = {}
    for mode, use_canon in (("raw_string_mmd_u", False), ("canonical_hex_mmd_u", True)):
        mat_ex = exact_mmd_pair_matrix(ref_a, qry_a, ids, canonical_hex=use_canon)
        st_all = baselines.exact_mmd_stats(mat_ex)
        st_sub = baselines.exact_mmd_stats(mat_ex, negative=neg_sub)
        st_fam = baselines.exact_mmd_stats(mat_ex, negative=neg_fam)
        st_wf = baselines.exact_mmd_stats(mat_ex, negative=neg_same_fam)

        # LOO 1-NN family attribution on full 6-rep cells (>=4 valid parses, matching Table 3)
        full_g = core.group(data_a)
        for t in full_g:
            full_g[t] = {c: rs for c, rs in full_g[t].items() if sum(r["parsed"]["status"] == "valid" for r in rs) >= 4}
        full_ids = sorted(full_g)
        mat_loo = exact_mmd_pair_matrix(full_g, full_g, full_ids, canonical_hex=use_canon)
        counts = collections.Counter(fmap[t]["family"] for t in full_ids if not fmap.get(t, {}).get("is_singleton", True))
        hits = 0
        total_loo = 0
        for j, t in enumerate(full_ids):
            if fmap.get(t, {}).get("is_singleton", True) or counts[fmap[t]["family"]] < 2:
                continue
            total_loo += 1
            best_i = min((i for i in range(len(full_ids)) if i != j), key=lambda i: (mat_loo[i][j], full_ids[i]))
            if fmap[full_ids[best_i]]["family"] == fmap[t]["family"]:
                hits += 1

        out[mode] = {
            "n_models": len(ids),
            "auc": round(st_all["auc"], 4),
            "eer_discrete_pct": round(100.0 * st_all["eer_discrete"], 2),
            "eer_linear_pct": round(100.0 * st_all["eer"], 2),
            "cross_sublineage_eer_pct": round(100.0 * st_sub["eer"], 2),
            "cross_family_eer_pct": round(100.0 * st_fam["eer"], 2),
            "within_family_eer_pct": round(100.0 * st_wf["eer"], 2),
            "loo_family_hits": f"{hits}/{total_loo}",
            "loo_family_pct": round(100.0 * hits / total_loo, 2),
        }
    return out


def compute_s1_discrete_and_mmd(data: dict) -> dict:
    cf0_g, cf21_g, or21_g = experiments.make_s1(data)
    comp = json.loads((ROOT / "results" / "benchmark" / "comparisons.json").read_text(encoding="utf-8"))
    e_ids = set(comp["E"]["ids"])

    # Fit frozen B3v3 and B6v6 thresholds for hex_jsd and raw/canonical MMD-U for complete fairness
    b3_r, b3_q = experiments.within(experiments.b20(data["B"]))
    b6_r = core.group([r for r in data["B"] if r["lang"] in ("en", "zh") and r["rep"] <= 6])
    b6_q = core.group([r for r in data["B"] if r["lang"] in ("en", "zh") and 7 <= r["rep"] <= 12])
    b_ids, b3_mats, _ = core.matrix(b3_r, b3_q)
    _, b6_mats, _ = core.matrix(b6_r, b6_q)
    tau_b3_hex = core.thresholds(b3_mats["hex_jsd"])["tau_mid"]
    tau_b6_hex = core.thresholds(b6_mats["hex_jsd"])["tau_mid"]

    b3_mmd = np.array([[float(v) for v in row] for row in exact_mmd_pair_matrix(b3_r, b3_q, b_ids, False)])
    b6_mmd = np.array([[float(v) for v in row] for row in exact_mmd_pair_matrix(b6_r, b6_q, b_ids, False)])
    tau_b3_mmd = core.thresholds(b3_mmd)["tau_mid"]
    tau_b6_mmd = core.thresholds(b6_mmd)["tau_mid"]

    paths = {}
    for label, rg, qg in (
        ("CF0_to_CF21", cf0_g, cf21_g),
        ("CF21_to_OR21", cf21_g, or21_g),
        ("CF0_to_OR21", cf0_g, or21_g),
    ):
        ids, mats, _ = core.matrix(rg, qg)
        mmd_ex = exact_mmd_pair_matrix(rg, qg, ids, canonical_hex=False)
        mmd_canon_ex = exact_mmd_pair_matrix(rg, qg, ids, canonical_hex=True)
        mmd_fl = np.array([[float(v) for v in row] for row in mmd_ex])

        st_hex = core.stats(mats["hex_jsd"])
        op_hex_b3 = core.operating(mats["hex_jsd"], tau_b3_hex)
        op_hex_b6 = core.operating(mats["hex_jsd"], tau_b6_hex)

        st_mmd = baselines.exact_mmd_stats(mmd_ex, mmd_fl)
        st_mmd_c = baselines.exact_mmd_stats(mmd_canon_ex)
        op_mmd_b3 = core.operating(mmd_fl, tau_b3_mmd)
        op_mmd_b6 = core.operating(mmd_fl, tau_b6_mmd)

        held_ix = [i for i, t in enumerate(ids) if t in e_ids]
        sub_hex = mats["hex_jsd"][np.ix_(held_ix, held_ix)]
        sub_mmd_ex = [[mmd_ex[i][j] for j in held_ix] for i in held_ix]
        st_hex_h4 = core.stats(sub_hex)
        st_mmd_h4 = baselines.exact_mmd_stats(sub_mmd_ex)

        paths[label] = {
            "hex_jsd_all14": {
                "top1_hits": f"{int(round(st_hex['top1'] * len(ids)))}/{len(ids)}",
                "auc": round(st_hex["auc"], 4),
                "eer_pct": round(100.0 * st_hex["eer"], 2),
                "genuine_mean": round(st_hex["genuine_mean"], 4),
                "impostor_mean": round(st_hex["impostor_mean"], 4),
                "frozen_b3v3_frr_far_pct": f"{100*op_hex_b3['frr']:.2f}% / {100*op_hex_b3['far']:.2f}%",
                "frozen_b6v6_frr_far_pct": f"{100*op_hex_b6['frr']:.2f}% / {100*op_hex_b6['far']:.2f}%",
            },
            "color_mmd_u_raw_all14": {
                "top1_hits": f"{int(round(st_mmd['top1'] * len(ids)))}/{len(ids)}",
                "auc": round(st_mmd["auc"], 4),
                "eer_pct": round(100.0 * st_mmd["eer"], 2),
                "genuine_mean": round(st_mmd["genuine_mean"], 4),
                "impostor_mean": round(st_mmd["impostor_mean"], 4),
                "frozen_b3v3_frr_far_pct": f"{100*op_mmd_b3['frr']:.2f}% / {100*op_mmd_b3['far']:.2f}%",
                "frozen_b6v6_frr_far_pct": f"{100*op_mmd_b6['frr']:.2f}% / {100*op_mmd_b6['far']:.2f}%",
            },
            "color_mmd_u_canonical_hex_all14": {
                "top1_hits": f"{int(round(st_mmd_c['top1'] * len(ids)))}/{len(ids)}",
                "auc": round(st_mmd_c["auc"], 4),
                "eer_pct": round(100.0 * st_mmd_c["eer"], 2),
            },
            "heldout4": {
                "hex_jsd_eer_pct": round(100.0 * st_hex_h4["eer"], 2),
                "color_mmd_u_raw_eer_pct": round(100.0 * st_mmd_h4["eer"], 2),
            },
        }
    return paths


def compute_s2_decontamination(rows_s2: list[dict]) -> dict:
    meta = {
        t["id"]: t
        for t in json.loads((ROOT / experiments.EXT / "configs/targets.s2_multiprovider.json").read_text(encoding="utf-8"))["targets"]
    }

    def eval_s2_rows(rows_use: list[dict], split_mode: str) -> dict:
        if split_mode == "6v6":
            rg, qg = core.group(rows_use), core.group(rows_use)
        else:
            rg, qg = experiments.within(rows_use)
        ids, mats, _ = core.matrix(rg, qg)
        # Construct color-only composite without D_side: (0.35 D_vox + 0.25 D_hex + 0.25 D_E) / 0.85
        mats["color_composite_no_side"] = (
            0.35 * mats["voxel_jsd"] + 0.25 * mats["hex_jsd"] + 0.25 * mats["energy_norm"]
        ) / 0.85
        positive = np.array([[t != u and meta[t]["weight_group"] == meta[u]["weight_group"] for u in ids] for t in ids])
        negative = np.array([[meta[t]["weight_group"] != meta[u]["weight_group"] for u in ids] for t in ids])

        out_m = {}
        for m in ("hybrid", "hybrid_reg", "color_composite_no_side", "energy_reg", "energy_norm", "voxel_jsd", "hex_jsd", "side_jsd"):
            mat = mats[m]
            st = core.stats(mat, positive, negative)
            masked = mat.copy()
            np.fill_diagonal(masked, np.inf)
            top1_hits = sum(
                meta[ids[int(np.argmin(masked[:, j]))]]["weight_group"] == meta[t]["weight_group"]
                for j, t in enumerate(ids)
            )
            entry = {
                "auc": round(st["auc"], 4),
                "eer_pct": round(100.0 * st["eer"], 2),
                "group_top1": f"{top1_hits}/{len(ids)}",
            }
            if split_mode == "6v6":
                clean_pairs = [
                    (i, j) for i, t in enumerate(ids) for j, u in enumerate(ids)
                    if positive[i, j] and meta[t]["quant"] in ("bf16", "fp8") and meta[u]["quant"] in ("bf16", "fp8")
                ]
                low_pairs = [
                    (i, j) for i, t in enumerate(ids) for j, u in enumerate(ids)
                    if positive[i, j] and meta[t]["quant"] in ("bf16", "fp8") and meta[u]["quant"] in ("int4", "fp4")
                ]
                roc_q = an.compute_roc_eer([mat[i, j] for i, j in clean_pairs], [mat[i, j] for i, j in low_pairs])
                entry["lowbit_anomaly_auc"] = round(roc_q["auc_raw"], 4)
                entry["lowbit_anomaly_eer_pct"] = round(100.0 * roc_q["eer_linear_raw"], 2)
            out_m[m] = entry
        return out_m

    rows_no_env = decontaminate_rows(rows_s2, merge_numeric_case=False, strip_envelope_telemetry=True)
    rows_pure = decontaminate_rows(rows_s2, merge_numeric_case=True, strip_envelope_telemetry=True)
    return {
        "6v6": {
            "archived": eval_s2_rows(rows_s2, "6v6"),
            "content_only_no_envelope": eval_s2_rows(rows_no_env, "6v6"),
            "pure_content_syntax": eval_s2_rows(rows_pure, "6v6"),
        },
        "3v3": {
            "archived": eval_s2_rows(rows_s2, "3v3"),
            "content_only_no_envelope": eval_s2_rows(rows_no_env, "3v3"),
            "pure_content_syntax": eval_s2_rows(rows_pure, "3v3"),
        },
    }


def compute_s5c_all_3v3_splits() -> dict:
    rows = load_s5c_dedup()
    targets = json.loads(S5_TARGETS.read_text(encoding="utf-8"))["targets"]
    tids = [t["id"] for t in targets]
    fam_by_tid = {t["id"]: t["family"] for t in targets}
    pos = np.eye(len(tids), dtype=bool)
    neg_all = ~pos
    neg_fam = np.array([[i != j and fam_by_tid[tids[i]] == fam_by_tid[tids[j]] for j in range(len(tids))] for i in range(len(tids))])

    # Enumerate the 10 unordered 3v3 partitions of {0,1,2,3,4,5} (fixing 0 in half A)
    unordered_splits = []
    for comb in itertools.combinations(range(1, 6), 2):
        half_a = (0, *comb)
        half_b = tuple(r for r in range(6) if r not in half_a)
        unordered_splits.append((half_a, half_b))
    assert len(unordered_splits) == 10

    per_split = []
    for ha, hb in unordered_splits:
        ga = core.group([r for r in rows if int(r["rep"]) in ha])
        gb = core.group([r for r in rows if int(r["rep"]) in hb])
        ids_m, mats, _ = core.matrix(ga, gb)
        ix = [ids_m.index(t) for t in tids]
        mat_e = mats["energy_reg"][np.ix_(ix, ix)]
        mat_h = mats["hybrid"][np.ix_(ix, ix)]
        mat_mmd_ex = exact_mmd_pair_matrix(ga, gb, tids, canonical_hex=False)

        se_all = core.stats(mat_e, pos, neg_all)
        se_fam = core.stats(mat_e, pos, neg_fam)
        sh_all = core.stats(mat_h, pos, neg_all)
        sh_fam = core.stats(mat_h, pos, neg_fam)
        sm_all = baselines.exact_mmd_stats(mat_mmd_ex, positive=pos, negative=neg_all)
        sm_fam = baselines.exact_mmd_stats(mat_mmd_ex, positive=pos, negative=neg_fam)

        per_split.append({
            "half_a": list(ha),
            "half_b": list(hb),
            "energy_reg_all_eer_pct": round(100.0 * se_all["eer"], 2),
            "energy_reg_all_auc": round(se_all["auc"], 4),
            "energy_reg_within_fam_eer_pct": round(100.0 * se_fam["eer"], 2),
            "energy_reg_within_fam_auc": round(se_fam["auc"], 4),
            "hybrid_all_eer_pct": round(100.0 * sh_all["eer"], 2),
            "hybrid_within_fam_eer_pct": round(100.0 * sh_fam["eer"], 2),
            "color_mmd_u_all_eer_pct": round(100.0 * sm_all["eer"], 2),
            "color_mmd_u_within_fam_eer_pct": round(100.0 * sm_fam["eer"], 2),
        })

    def summarize_key(k: str) -> dict:
        vals = [x[k] for x in per_split]
        return {
            "mean": round(float(statistics.mean(vals)), 2) if "pct" in k else round(float(statistics.mean(vals)), 4),
            "sd": round(float(statistics.stdev(vals)), 2) if "pct" in k else round(float(statistics.stdev(vals)), 4),
            "median": round(float(statistics.median(vals)), 2) if "pct" in k else round(float(statistics.median(vals)), 4),
            "min": min(vals),
            "max": max(vals),
        }

    return {
        "n_balanced_partitions": len(per_split),
        "summary": {
            k: summarize_key(k)
            for k in (
                "energy_reg_all_eer_pct",
                "energy_reg_all_auc",
                "energy_reg_within_fam_eer_pct",
                "energy_reg_within_fam_auc",
                "color_mmd_u_all_eer_pct",
                "color_mmd_u_within_fam_eer_pct",
            )
        },
        "partitions": per_split,
    }


def u_cell_scores(u: np.ndarray, v: np.ndarray, delta0: float = 15.0) -> tuple[float, float, float]:
    n, m = len(u), len(v)
    d_uv = float(np.linalg.norm(u[:, None, :] - v[None, :, :], axis=-1).mean())
    d_uu_v = float(np.linalg.norm(u[:, None, :] - u[None, :, :], axis=-1).mean())
    d_vv_v = float(np.linalg.norm(v[:, None, :] - v[None, :, :], axis=-1).mean())
    d_uu_u = d_uu_v * n / (n - 1)
    d_vv_u = d_vv_v * m / (m - 1)
    h_v = 0.5 * (d_uu_v + d_vv_v)
    h_u = 0.5 * (d_uu_u + d_vv_u)
    v_reg = max(0.0, d_uv - h_v) / (d_uv + delta0) if d_uv >= 1e-12 else 0.0
    u_signed = (d_uv - h_u) / (d_uv + delta0)
    u_clipped = max(0.0, d_uv - h_u) / (d_uv + delta0)
    return v_reg, u_signed, u_clipped


def compute_u_statistic_external_cohorts(data: dict) -> dict:
    def pair_u_matrices(rg: dict, qg: dict) -> tuple[list[str], dict[str, np.ndarray]]:
        sa, sb = core.summarize(rg), core.summarize(qg)
        ids = sorted(set(sa) & set(sb))
        mats = {k: np.zeros((len(ids), len(ids))) for k in ("v_reg", "u_signed", "u_clipped")}
        for i, ti in enumerate(ids):
            for j, tj in enumerate(ids):
                cells = [
                    c for c in sorted(set(sa[ti]) & set(sb[tj]))
                    if sa[ti][c]["n_valid"] >= 2 and sb[tj][c]["n_valid"] >= 2
                ]
                scores = [u_cell_scores(sa[ti][c]["rgb_arr"], sb[tj][c]["rgb_arr"]) for c in cells]
                mats["v_reg"][i, j] = sum(s[0] for s in scores) / len(scores)
                mats["u_signed"][i, j] = sum(s[1] for s in scores) / len(scores)
                mats["u_clipped"][i, j] = sum(s[2] for s in scores) / len(scores)
        return ids, mats

    cf0_g, cf21_g, or21_g = experiments.make_s1(data)
    s5c_rows = load_s5c_dedup()
    s5_fh_r = core.group([r for r in s5c_rows if int(r["rep"]) in (0, 1, 2)])
    s5_fh_q = core.group([r for r in s5c_rows if int(r["rep"]) in (3, 4, 5)])
    s3_3v3_r = core.group([r for r in data["S3_color"] if int(r["rep"]) in (1, 3, 5)])
    s3_3v3_q = core.group([r for r in data["S3_color"] if int(r["rep"]) in (2, 4, 6)])

    cohorts = {}
    for name, (rg, qg) in (
        ("A_3v3", experiments.within(data["A"], 2)),
        ("B20x6_3v3", experiments.within(experiments.b20(data["B"]), 2)),
        ("E_3v3", experiments.within(data["E"], 2)),
        ("S1_CF0_CF21_6v6", (cf0_g, cf21_g)),
        ("S1_CF21_OR21_6v6", (cf21_g, or21_g)),
        ("S1_CF0_OR21_6v6", (cf0_g, or21_g)),
        ("S3_3v3_first6", (s3_3v3_r, s3_3v3_q)),
        ("S3_15v15", experiments.within(data["S3_color"], 2)),
        ("S5c_3v3_fh", (s5_fh_r, s5_fh_q)),
    ):
        _, mats = pair_u_matrices(rg, qg)
        cohorts[name] = {
            k: {
                "eer_pct": round(100.0 * core.stats(mats[k])["eer"], 2),
                "auc": round(core.stats(mats[k])["auc"], 4),
            }
            for k in ("v_reg", "u_signed", "u_clipped")
        }

    # S2 cross-provider 6v6 on >=2 cells
    meta_s2 = {
        t["id"]: t
        for t in json.loads((ROOT / experiments.EXT / "configs/targets.s2_multiprovider.json").read_text(encoding="utf-8"))["targets"]
    }
    ids_s2, mats_s2 = pair_u_matrices(core.group(data["S2"]), core.group(data["S2"]))
    pos_s2 = np.array([[t != u and meta_s2[t]["weight_group"] == meta_s2[u]["weight_group"] for u in ids_s2] for t in ids_s2])
    neg_s2 = np.array([[meta_s2[t]["weight_group"] != meta_s2[u]["weight_group"] for u in ids_s2] for t in ids_s2])
    cohorts["S2_provider_6v6"] = {
        k: {
            "eer_pct": round(100.0 * core.stats(mats_s2[k], pos_s2, neg_s2)["eer"], 2),
            "auc": round(core.stats(mats_s2[k], pos_s2, neg_s2)["auc"], 4),
        }
        for k in ("v_reg", "u_signed", "u_clipped")
    }
    return cohorts


def compute_private_pool_subsampling(data: dict) -> dict:
    rng = np.random.default_rng(20261120)

    # 1. Dataset B 40-cell enrolled pool: online audit draws k random cells matched to their own enrolled reference cells
    b_ref_8, b_qry_7 = experiments.within(data["B"], 1)
    b_qry_3 = core.group([r for r in data["B"] if int(r["rep"]) in (2, 4, 6)])
    sa_b = core.summarize(b_ref_8)
    ids_b = sorted(sa_b)
    all_40_cells = sorted({c for t in ids_b for c in sa_b[t]})
    assert len(all_40_cells) == 40

    cal_ops = json.loads((ROOT / "results" / "benchmark" / "calibration_results.json").read_text(encoding="utf-8"))["operating_points"]
    tau_b8_raw = next(
        r["threshold"] for r in cal_ops
        if r["scenario"] == "B8v7_development" and r["metric"] == "energy_reg" and r["variant"] == "raw" and r["threshold_kind"] == "tau_mid"
    )
    tau_b3_raw = next(
        r["threshold"] for r in cal_ops
        if r["scenario"] == "B3v3_development" and r["metric"] == "energy_reg" and r["variant"] == "raw" and r["threshold_kind"] == "tau_mid"
    )

    b_pool_res = {}
    for q_label, q_grp, tau_use in (("q3_reps", b_qry_3, tau_b3_raw), ("q7_reps", b_qry_7, tau_b8_raw)):
        sb_q = core.summarize(q_grp)
        cell_dist = {}
        for ti in ids_b:
            for tj in ids_b:
                cell_dist[ti, tj] = {
                    c: core.cell_scores(sa_b[ti][c], sb_q[tj][c])["energy_reg"]
                    for c in all_40_cells
                    if c in sa_b[ti] and c in sb_q[tj] and sa_b[ti][c]["n_valid"] > 0 and sb_q[tj][c]["n_valid"] > 0
                }
        sub_out = {}
        for k_sub in (8, 10, 16, 20):
            eers, aucs, frrs, fars = [], [], [], []
            for _ in range(200):
                chosen = [all_40_cells[idx] for idx in rng.choice(len(all_40_cells), size=k_sub, replace=False)]
                mat = np.zeros((len(ids_b), len(ids_b)))
                for i, ti in enumerate(ids_b):
                    for j, tj in enumerate(ids_b):
                        vals = [cell_dist[ti, tj][c] for c in chosen if c in cell_dist[ti, tj]]
                        mat[i, j] = sum(vals) / len(vals)
                st = core.stats(mat)
                op = core.operating(mat, tau_use)
                eers.append(100.0 * st["eer"])
                aucs.append(st["auc"])
                frrs.append(100.0 * op["frr"])
                fars.append(100.0 * op["far"])
            sub_out[f"k={k_sub}_of_40"] = {
                "prompt_reuse_reduction_factor": round(40.0 / k_sub, 2),
                "mean_eer_pct": round(float(np.mean(eers)), 2),
                "p95_eer_pct": round(float(np.quantile(eers, 0.95)), 2),
                "mean_auc": round(float(np.mean(aucs)), 4),
                "frozen_mean_frr_pct": round(float(np.mean(frrs)), 2),
                "frozen_mean_far_pct": round(float(np.mean(fars)), 2),
            }
        b_pool_res[q_label] = sub_out

    # 2. Dataset C + B multi-template 24-cell private pool (P0 u P1 u P2, 8 reps per cell -> 4v4 odd/even)
    c_tasks_p0 = {"hex_favorite", "rgb_favorite", "hex_ocean", "hex_warm"}
    p0_rows = [
        dict(r, task_id="p0_" + r["task_id"])
        for r in data["B"]
        if r["task_id"] in c_tasks_p0 and r["lang"] in ("en", "zh") and int(r["rep"]) <= 8
    ]
    pool24_rows = p0_rows + list(data["C"])
    # Token cost to enroll 4 reps across all 24 cells (96 calls) or 8 reps across 24 cells (192 calls)
    tok_by_model_4rep = collections.defaultdict(int)
    for r in pool24_rows:
        if int(r["rep"]) % 2 == 1:
            u = r.get("usage") or {}
            tok_by_model_4rep[r["target_id"]] += int(u.get("input_tokens") or 0) + int(u.get("output_tokens") or 0)

    r24, q24 = experiments.within(pool24_rows, 1)
    sr24, sq24 = core.summarize(r24), core.summarize(q24)
    ids_c = sorted(set(sr24) & set(sq24))
    all_24_cells = sorted({c for t in ids_c for c in sr24[t]})
    assert len(all_24_cells) == 24

    c_cell_dist = {}
    for ti in ids_c:
        for tj in ids_c:
            c_cell_dist[ti, tj] = {
                c: {m: core.cell_scores(sr24[ti][c], sq24[tj][c])[m] for m in ("energy_reg", "hybrid")}
                for c in all_24_cells
                if c in sr24[ti] and c in sq24[tj] and sr24[ti][c]["n_valid"] > 0 and sq24[tj][c]["n_valid"] > 0
            }

    # Full 24-cell pool baseline + random k-cell online draws
    c_pool_res = {
        "pool_cells_total": 24,
        "enroll_4rep_96calls_max_tokens_per_model": max(tok_by_model_4rep.values()),
        "enroll_4rep_96calls_median_tokens_per_model": float(statistics.median(tok_by_model_4rep.values())),
        "subsets": {},
    }
    for k_sub in (6, 8, 12, 24):
        n_draws = 1 if k_sub == 24 else 200
        eers_e, eers_h, aucs_e = [], [], []
        for _ in range(n_draws):
            chosen = all_24_cells if k_sub == 24 else [all_24_cells[idx] for idx in rng.choice(24, size=k_sub, replace=False)]
            mat_e = np.zeros((len(ids_c), len(ids_c)))
            mat_h = np.zeros((len(ids_c), len(ids_c)))
            for i, ti in enumerate(ids_c):
                for j, tj in enumerate(ids_c):
                    ve = [c_cell_dist[ti, tj][c]["energy_reg"] for c in chosen if c in c_cell_dist[ti, tj]]
                    vh = [c_cell_dist[ti, tj][c]["hybrid"] for c in chosen if c in c_cell_dist[ti, tj]]
                    mat_e[i, j] = sum(ve) / len(ve)
                    mat_h[i, j] = sum(vh) / len(vh)
            se = core.stats(mat_e)
            sh = core.stats(mat_h)
            eers_e.append(100.0 * se["eer"])
            eers_h.append(100.0 * sh["eer"])
            aucs_e.append(se["auc"])
        c_pool_res["subsets"][f"k={k_sub}_of_24"] = {
            "prompt_reuse_reduction_factor": round(24.0 / k_sub, 2),
            "energy_reg_mean_eer_pct": round(float(np.mean(eers_e)), 2),
            "energy_reg_p95_eer_pct": round(float(np.quantile(eers_e, 0.95)), 2),
            "hybrid_mean_eer_pct": round(float(np.mean(eers_h)), 2),
            "energy_reg_mean_auc": round(float(np.mean(aucs_e)), 4),
        }

    return {
        "B_40cell_pool": b_pool_res,
        "C_24cell_multitemplate_pool": c_pool_res,
    }


def compute_two_stage_sequential_cascade(data: dict) -> dict:
    """Evaluate two-stage online canary monitoring (`Stage 1` 3-rep screen ->
    `Stage 2` disjoint confirmation window only upon Stage-1 crossing)."""
    cal_ops = json.loads((ROOT / "results" / "benchmark" / "calibration_results.json").read_text(encoding="utf-8"))["operating_points"]
    tau_b3_raw = next(
        r["threshold"] for r in cal_ops
        if r["scenario"] == "B3v3_development" and r["metric"] == "energy_reg" and r["variant"] == "raw" and r["threshold_kind"] == "tau_mid"
    )
    tau_b6_raw = next(
        r["threshold"] for r in cal_ops
        if r["scenario"] == "B6v6_development" and r["metric"] == "energy_reg" and r["variant"] == "raw" and r["threshold_kind"] == "tau_mid"
    )

    # 1. Study S3 20 locked models (10 cells, 30 reps):
    # Enroll on odd reps 1..11 (6 reps/cell = 60 enrollment calls, matching B6v6 reference depth).
    # Remaining disjoint query stream per endpoint:
    #   Five 3-rep Stage-1 windows on even reps: W1={2,4,6}, W2={8,10,12}, W3={14,16,18}, W4={20,22,24}, W5={26,28,30}
    #   Reserved disjoint 6-rep Stage-2 confirmation pool on odd reps {13,15,17,19,21,23} (60 calls).
    # When Stage 1 (30 calls, evaluated against frozen B3v3 tau_mid = 0.14802) crosses tau_b3_raw,
    # Stage 2 queries the 60-call confirmation window and escalates iff the 6v6 score exceeds frozen B6v6 tau_mid = 0.11303!
    targets_s3 = json.loads(S5_TARGETS.read_text(encoding="utf-8"))["targets"]
    tids_s3 = [t["id"] for t in targets_s3]
    fam_s3 = {t["id"]: t["family"] for t in targets_s3}

    s3_enroll = core.group([r for r in data["S3_color"] if int(r["rep"]) in (1, 3, 5, 7, 9, 11)])
    s3_confirm = core.group([r for r in data["S3_color"] if int(r["rep"]) in (13, 15, 17, 19, 21, 23)])
    stage1_rep_windows = [(2, 4, 6), (8, 10, 12), (14, 16, 18), (20, 22, 24), (26, 28, 30)]
    s3_stage1_grps = [core.group([r for r in data["S3_color"] if int(r["rep"]) in w]) for w in stage1_rep_windows]

    ids_c, mats_conf, _ = core.matrix(s3_enroll, s3_confirm)
    ix_s3 = [ids_c.index(t) for t in tids_s3]
    mat_conf = mats_conf["energy_reg"][np.ix_(ix_s3, ix_s3)]

    mat_s1_list = []
    for g_w in s3_stage1_grps:
        _, mw, _ = core.matrix(s3_enroll, g_w)
        mat_s1_list.append(mw["energy_reg"][np.ix_(ix_s3, ix_s3)])

    # Evaluate across 5 x 20 = 100 genuine windows, 5 x 380 = 1900 all-pairs substitution windows,
    # and 5 x 38 = 190 within-family substitution windows
    gen_s1_cross = 0
    gen_2stage_alert = 0
    gen_total = 0

    imp_all_s1_det = 0
    imp_all_2stage_det = 0
    imp_all_total = 0

    imp_fam_s1_det = 0
    imp_fam_2stage_det = 0
    imp_fam_total = 0

    for mat_w in mat_s1_list:
        for i, ti in enumerate(tids_s3):
            for j, tj in enumerate(tids_s3):
                c1 = bool(mat_w[i, j] > tau_b3_raw)
                c2 = bool(c1 and (mat_conf[i, j] > tau_b6_raw))
                if i == j:
                    gen_total += 1
                    gen_s1_cross += int(c1)
                    gen_2stage_alert += int(c2)
                else:
                    imp_all_total += 1
                    imp_all_s1_det += int(c1)
                    imp_all_2stage_det += int(c2)
                    if fam_s3[ti] == fam_s3[tj]:
                        imp_fam_total += 1
                        imp_fam_s1_det += int(c1)
                        imp_fam_2stage_det += int(c2)

    s1_frr = gen_s1_cross / gen_total
    two_stage_frr = gen_2stage_alert / gen_total
    # Expected query calls per routine genuine check: 30 + s1_frr * 60
    expected_calls_genuine = 30.0 + s1_frr * 60.0
    # Using S5c 30-call Scenario G median USD ($0.0068 for 30 calls => ~$0.0136 for 60 calls)
    expected_usd_G_genuine = 0.0068 + s1_frr * (2.0 * 0.0068)

    # Also compute 24-hour hourly compound false-alarm probability: 1 - (1 - FRR)^24
    hourly_24h_s1_false_alarm_pct = round(100.0 * (1.0 - (1.0 - s1_frr) ** 24), 2)
    hourly_24h_2stage_false_alarm_pct = round(100.0 * (1.0 - (1.0 - two_stage_frr) ** 24), 2)

    # 2. Cross-gateway Study S1 (`CF21 -> OR21` and `CF0 -> OR21`):
    # Split each 6-rep query log into Stage-1 odd reps {1,3,5} (60 calls across 20 cells)
    # and Stage-2 full 6v6 confirmation (adding even reps {2,4,6}, +60 calls only on crossings)
    cf0_g, cf21_g, _ = experiments.make_s1(data)
    map_or = {
        t["id"]: t["paired_cf_id"]
        for t in json.loads((ROOT / experiments.EXT / "configs/targets.s1_or_crossgateway.json").read_text(encoding="utf-8"))["targets"]
    }
    or21_odd = core.group([r for r in data["S1_OR21"] if int(r["rep"]) % 2 == 1], target_map=map_or)
    or21_all = core.group(data["S1_OR21"], target_map=map_or)

    s1_cascade = {}
    for name, ref_g in (("CF0_to_OR21", cf0_g), ("CF21_to_OR21", cf21_g)):
        ids_14, m_st1, _ = core.matrix(ref_g, or21_odd)
        _, m_st2, _ = core.matrix(ref_g, or21_all)
        e1 = m_st1["energy_reg"]
        e2 = m_st2["energy_reg"]
        n14 = len(ids_14)
        g_c1 = sum(e1[i, i] > tau_b3_raw for i in range(n14))
        g_c2 = sum((e1[i, i] > tau_b3_raw) and (e2[i, i] > tau_b6_raw) for i in range(n14))
        i_det1 = sum(e1[i, j] > tau_b3_raw for i in range(n14) for j in range(n14) if i != j)
        i_det2 = sum((e1[i, j] > tau_b3_raw) and (e2[i, j] > tau_b6_raw) for i in range(n14) for j in range(n14) if i != j)
        tot_imp = n14 * (n14 - 1)
        s1_cascade[name] = {
            "n_genuine": n14,
            "n_impostor": tot_imp,
            "stage1_frr_pct": round(100.0 * g_c1 / n14, 2),
            "two_stage_frr_pct": round(100.0 * g_c2 / n14, 2),
            "stage1_tpr_pct": round(100.0 * i_det1 / tot_imp, 2),
            "two_stage_tpr_pct": round(100.0 * i_det2 / tot_imp, 2),
            "two_stage_far_pct": round(100.0 * (1.0 - i_det2 / tot_imp), 2),
            "expected_calls_genuine": round(60.0 + (g_c1 / n14) * 60.0, 2),
        }

    # Also evaluate true protocol-matched B(10 shared English cells) -> S3(10 English cells) out-of-cohort transfer
    # using both raw energy_reg and self-centered / U-clipped ratio (zero S3 data used in threshold fitting).
    s3_cells = sorted({f"{r['task_id']}|{r['lang']}" for r in data["S3_color"]})
    b10_s1_r = core.group([r for r in data["B"] if f"{r['task_id']}|{r['lang']}" in set(s3_cells) and int(r["rep"]) in (1, 3, 5, 7, 9, 11)])
    b10_s1_q = core.group([r for r in data["B"] if f"{r['task_id']}|{r['lang']}" in set(s3_cells) and int(r["rep"]) in (2, 4, 6)])
    b10_s2_q = core.group([r for r in data["B"] if f"{r['task_id']}|{r['lang']}" in set(s3_cells) and int(r["rep"]) in (2, 4, 6, 8, 10, 12)])
    _, b10_m1, _ = core.matrix(b10_s1_r, b10_s1_q)
    _, b10_m2, _ = core.matrix(b10_s1_r, b10_s2_q)
    tau_b10_stage1 = core.thresholds(b10_m1["energy_reg"])["tau_mid"]
    tau_b10_stage2 = core.thresholds(b10_m2["energy_reg"])["tau_mid"]

    # Also compute U-clipped thresholds on B10 (6v3 Stage 1 and 6v6 Stage 2) and evaluate on S3 stream
    def u_clip_mat(rg: dict, qg: dict, order_ids: list[str] | None = None) -> np.ndarray:
        sa, sb = core.summarize(rg), core.summarize(qg)
        use_ids = order_ids or sorted(set(sa) & set(sb))
        m = np.zeros((len(use_ids), len(use_ids)))
        for i, ti in enumerate(use_ids):
            for j, tj in enumerate(use_ids):
                cs = [c for c in sorted(set(sa[ti]) & set(sb[tj])) if sa[ti][c]["n_valid"] >= 2 and sb[tj][c]["n_valid"] >= 2]
                m[i, j] = sum(u_cell_scores(sa[ti][c]["rgb_arr"], sb[tj][c]["rgb_arr"])[2] for c in cs) / len(cs)
        return m

    tau_b10_u1 = core.thresholds(u_clip_mat(b10_s1_r, b10_s1_q))["tau_mid"]
    tau_b10_u2 = core.thresholds(u_clip_mat(b10_s1_r, b10_s2_q))["tau_mid"]
    s3_u_conf = u_clip_mat(s3_enroll, s3_confirm, tids_s3)
    s3_u_w_list = [u_clip_mat(s3_enroll, gw, tids_s3) for gw in s3_stage1_grps]

    def eval_stream(w_mats: list[np.ndarray], c_mat: np.ndarray, t1: float, t2: float) -> dict:
        g1 = g2 = ia1 = ia2 = if1 = if2 = 0
        gt = iat = ift = 0
        for mw in w_mats:
            for i, ti in enumerate(tids_s3):
                for j, tj in enumerate(tids_s3):
                    c_st1 = bool(mw[i, j] > t1)
                    c_st2 = bool(c_st1 and (c_mat[i, j] > t2))
                    if i == j:
                        gt += 1; g1 += int(c_st1); g2 += int(c_st2)
                    else:
                        iat += 1; ia1 += int(c_st1); ia2 += int(c_st2)
                        if fam_s3[ti] == fam_s3[tj]:
                            ift += 1; if1 += int(c_st1); if2 += int(c_st2)
        frr1 = g1 / gt
        frr2 = g2 / gt
        return {
            "tau_stage1": round(t1, 5),
            "tau_stage2": round(t2, 5),
            "stage1_frr_pct": round(100.0 * frr1, 2),
            "two_stage_frr_pct": round(100.0 * frr2, 2),
            "compound_24h_hourly_false_alarm_stage1_pct": round(100.0 * (1.0 - (1.0 - frr1) ** 24), 2),
            "compound_24h_hourly_false_alarm_2stage_pct": round(100.0 * (1.0 - (1.0 - frr2) ** 24), 2),
            "stage1_all_pairs_tpr_pct": round(100.0 * ia1 / iat, 2),
            "two_stage_all_pairs_tpr_pct": round(100.0 * ia2 / iat, 2),
            "two_stage_all_pairs_far_pct": round(100.0 * (1.0 - ia2 / iat), 2),
            "stage1_within_family_tpr_pct": round(100.0 * if1 / ift, 2),
            "two_stage_within_family_tpr_pct": round(100.0 * if2 / ift, 2),
            "two_stage_within_family_far_pct": round(100.0 * (1.0 - if2 / ift), 2),
            "expected_calls_per_genuine_check": round(30.0 + frr1 * 60.0, 2),
            "expected_scenario_G_usd_per_genuine_check": round(0.0068 + frr1 * 2.0 * 0.0068, 4),
        }

    s3_b10_v_stream = eval_stream(mat_s1_list, mat_conf, tau_b10_stage1, tau_b10_stage2)
    s3_b10_u_stream = eval_stream(s3_u_w_list, s3_u_conf, tau_b10_u1, tau_b10_u2)

    return {
        "S3_5window_stream_mismatched_B20_cutoffs": {
            "frozen_tau_stage1_b3v3": round(tau_b3_raw, 5),
            "frozen_tau_stage2_b6v6": round(tau_b6_raw, 5),
            "genuine_windows": gen_total,
            "stage1_false_crossings": gen_s1_cross,
            "stage1_frr_pct": round(100.0 * s1_frr, 2),
            "two_stage_false_alerts": gen_2stage_alert,
            "two_stage_frr_pct": round(100.0 * two_stage_frr, 2),
            "compound_24h_hourly_false_alarm_stage1_pct": hourly_24h_s1_false_alarm_pct,
            "compound_24h_hourly_false_alarm_2stage_pct": hourly_24h_2stage_false_alarm_pct,
            "all_pairs_windows": imp_all_total,
            "stage1_all_pairs_tpr_pct": round(100.0 * imp_all_s1_det / imp_all_total, 2),
            "two_stage_all_pairs_tpr_pct": round(100.0 * imp_all_2stage_det / imp_all_total, 2),
            "two_stage_all_pairs_far_pct": round(100.0 * (1.0 - imp_all_2stage_det / imp_all_total), 2),
            "within_family_windows": imp_fam_total,
            "stage1_within_family_tpr_pct": round(100.0 * imp_fam_s1_det / imp_fam_total, 2),
            "two_stage_within_family_tpr_pct": round(100.0 * imp_fam_2stage_det / imp_fam_total, 2),
            "two_stage_within_family_far_pct": round(100.0 * (1.0 - imp_fam_2stage_det / imp_fam_total), 2),
            "expected_calls_per_genuine_check": round(expected_calls_genuine, 2),
            "expected_scenario_G_usd_per_genuine_check": round(expected_usd_G_genuine, 4),
        },
        "S3_5window_stream_matched_B10_v_reg": s3_b10_v_stream,
        "S3_5window_stream_matched_B10_u_clipped": s3_b10_u_stream,
        "S1_cross_gateway_cascade": s1_cascade,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out_path = args.output.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_base, n_s5 = verify_protected()
    sys.addaudithook(offline_guard)

    fmap = json.loads((ROOT / "config" / "family_map.json").read_text(encoding="utf-8"))["families"]
    data = {
        k: core.load(ROOT / experiments.FILES[k])
        for k in ("A", "B", "C", "E", "S1_CF21", "S1_OR21", "S2", "S3_color")
    }

    report = {
        "suite": "operational_diagnostics_v1",
        "protected_baseline_files_verified": n_base,
        "protected_s5_files_verified": n_s5,
        "dataset_a_color_mmd_u": compute_dataset_a_mmd(data["A"], fmap),
        "study_s1_discrete_and_mmd_scores": compute_s1_discrete_and_mmd(data),
        "study_s2_side_decontamination": compute_s2_decontamination(data["S2"]),
        "study_s5c_all_balanced_3v3_splits": compute_s5c_all_3v3_splits(),
        "u_statistic_external_cohorts": compute_u_statistic_external_cohorts(data),
        "private_pool_subsampling": compute_private_pool_subsampling(data),
        "two_stage_sequential_cascade": compute_two_stage_sequential_cascade(data),
    }

    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    verify_protected()
    shown = out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path
    print(f"Wrote {shown}")


if __name__ == "__main__":
    main()
