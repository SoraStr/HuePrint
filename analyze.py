#!/usr/bin/env python3
"""
RGB/Hex Geometry & Distribution Fingerprint Analyzer.

Implements:
  1. Per-target & per-cell summary statistics (validity, Hex/Voxel entropy, modal share, T=0 determinism).
  2. Multi-scale distance metrics per probe cell:
     - Exact Hex JSD (discrete memorization anchors)
     - 8x8x8 Voxel-Binned JSD (jitter-tolerant discrete distribution)
     - 3D RGB Energy Distance & Normalized Energy Coefficient (continuous 3D point cloud)
     - 3D RGB Bures-Wasserstein Gaussian Manifold Distance (centroid shift + covariance deformation)
     - Syntactic & CoT Side-Channel JSD (case preference, comma spacing, thinking length & first-word)
     - Hybrid Composite Distance
  3. Biometric-style verification (odd/even split-half Genuine vs Impostor trials, ROC AUC, EER, tau*).
  4. Query-Budget Curve (EER mean & 90% band over random k-cell subsets).
  5. Nearest-Neighbor lineage table & Ecosystem Anomaly / Response-Caching / Hidden-CoT screens.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any

import numpy as np

# RGB encoding is kept intact; only a global change of units is applied.
RGB_SCALE = 100.0 / 255.0
ENERGY_DELTA0 = 15.0
W2_COV_REG = 1e-3
W2_LENGTH_SCALE = 50.0
ANALYSIS_PROTOCOL = {
    "version": "rgb100_v1_20261111",
    "color_space": "sRGB_encoded",
    "geometry_transform": "100 * RGB / 255",
    "geometry_range": [0.0, 100.0],
    "rgb_scale": RGB_SCALE,
    "energy_delta0": ENERGY_DELTA0,
    "w2_covariance_regularization": W2_COV_REG,
    "w2_length_scale": W2_LENGTH_SCALE,
    "hard_voxel_width_rgb255": 32,
    "soft_voxel_width_rgb255": 48.0,
    "parser_version": "3.0",
}


def rgb_to_geometry(rgb: list[int] | tuple[int, ...]) -> np.ndarray:
    """Convert encoded RGB channel values to RGB100 units, without gamma/Lab."""
    return np.asarray(rgb, dtype=np.float64) * RGB_SCALE


# ---------------------------------------------------------------------------
# Information-Theoretic & 3D Manifold Distance Functions
# ---------------------------------------------------------------------------

def shannon_entropy_bits(counts: dict[Any, int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    ent = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            ent -= p * math.log2(p)
    return ent


def jsd_base2(counts_a: dict[Any, float], counts_b: dict[Any, float]) -> float:
    """Jensen-Shannon divergence (base 2) bounded in [0, 1] with deterministic key order."""
    tot_a = float(sum(counts_a.values()))
    tot_b = float(sum(counts_b.values()))
    if tot_a <= 0.0 or tot_b <= 0.0:
        return 1.0
    keys = sorted(set(counts_a.keys()) | set(counts_b.keys()))
    jsd = 0.0
    for k in keys:
        pa = counts_a.get(k, 0.0) / tot_a
        pb = counts_b.get(k, 0.0) / tot_b
        m = 0.5 * (pa + pb)
        if pa > 0.0:
            jsd += 0.5 * pa * math.log2(pa / m)
        if pb > 0.0:
            jsd += 0.5 * pb * math.log2(pb / m)
    return min(1.0, max(0.0, jsd))


def add_soft_voxel(counter: dict[str, float], rgb: list[int] | tuple[int, ...], bin_width: float = 48.0) -> None:
    """Trilinear soft assignment over 3D RGB grid so boundary jitter is strictly Lipschitz continuous."""
    coords = [float(c) / bin_width for c in rgb]
    base_idx = [int(math.floor(x)) for x in coords]
    frac = [x - b for x, b in zip(coords, base_idx)]
    for dx in (0, 1):
        wx = (1.0 - frac[0]) if dx == 0 else frac[0]
        if wx <= 0.0:
            continue
        for dy in (0, 1):
            wy = (1.0 - frac[1]) if dy == 0 else frac[1]
            if wy <= 0.0:
                continue
            for dz in (0, 1):
                wz = (1.0 - frac[2]) if dz == 0 else frac[2]
                w = wx * wy * wz
                if w > 0.0:
                    k = f"{base_idx[0] + dx}_{base_idx[1] + dy}_{base_idx[2] + dz}"
                    counter[k] = counter.get(k, 0.0) + w


def energy_distance_3d(pts_a: np.ndarray, pts_b: np.ndarray, delta0: float = ENERGY_DELTA0) -> tuple[float, float, float]:
    """
    Compute Euclidean energy, normalized and regularized dissimilarities.
    The current pipeline supplies RGB100 points; delta0 uses those same units.
    """
    if len(pts_a) == 0 or len(pts_b) == 0:
        return 100.0, 1.0, 1.0

    diff_ab = pts_a[:, None, :] - pts_b[None, :, :]
    dist_ab = np.linalg.norm(diff_ab, axis=-1)
    mean_ab = float(np.mean(dist_ab))

    if mean_ab < 1e-12:
        return 0.0, 0.0, 0.0

    diff_aa = pts_a[:, None, :] - pts_a[None, :, :]
    mean_aa = float(np.mean(np.linalg.norm(diff_aa, axis=-1)))

    diff_bb = pts_b[:, None, :] - pts_b[None, :, :]
    mean_bb = float(np.mean(np.linalg.norm(diff_bb, axis=-1)))

    e2 = max(0.0, 2.0 * mean_ab - mean_aa - mean_bb)
    e_raw = math.sqrt(e2)
    e_norm = min(1.0, max(0.0, e2 / (2.0 * mean_ab)))
    e_reg = min(1.0, max(0.0, e2 / (2.0 * mean_ab + 2.0 * delta0)))
    return e_raw, e_norm, e_reg

def _sym_sqrtm_3x3(mat: np.ndarray) -> np.ndarray:
    """Exact symmetric positive semi-definite 3x3 matrix square root via eigendecomposition."""
    eigvals, eigvecs = np.linalg.eigh(0.5 * (mat + mat.T))
    eigvals = np.maximum(eigvals, 0.0)
    return (eigvecs * np.sqrt(eigvals)) @ eigvecs.T


def bures_wasserstein_3d(pts_a: np.ndarray, pts_b: np.ndarray, reg: float = W2_COV_REG) -> tuple[float, float, float]:
    """
    Compute 3D Gaussian Bures-Wasserstein distance W_2(A, B).
    The current pipeline supplies RGB100 points; reg has squared coordinate units.
    Returns (w2_total, centroid_l2, cov_bures_term).
    """
    if len(pts_a) == 0 or len(pts_b) == 0:
        return 100.0, 100.0, 0.0

    mu_a = np.mean(pts_a, axis=0)
    mu_b = np.mean(pts_b, axis=0)
    centroid_sq = float(np.sum((mu_a - mu_b) ** 2))

    if len(pts_a) > 1:
        cov_a = np.cov(pts_a, rowvar=False, bias=True) + reg * np.eye(3)
    else:
        cov_a = reg * np.eye(3)

    if len(pts_b) > 1:
        cov_b = np.cov(pts_b, rowvar=False, bias=True) + reg * np.eye(3)
    else:
        cov_b = reg * np.eye(3)

    sqrt_a = _sym_sqrtm_3x3(cov_a)
    inner = sqrt_a @ cov_b @ sqrt_a
    sqrt_inner = _sym_sqrtm_3x3(inner)
    bures_sq = max(0.0, float(np.trace(cov_a + cov_b - 2.0 * sqrt_inner)))

    w2 = math.sqrt(centroid_sq + bures_sq)
    return w2, math.sqrt(centroid_sq), math.sqrt(bures_sq)


# ---------------------------------------------------------------------------
# Cell Aggregation & Pairwise Cell Distance
# ---------------------------------------------------------------------------

def summarize_cell_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract empirical distributions and 3D point clouds from valid samples in a single cell."""
    hex_counts: dict[str, int] = collections.Counter()
    voxel_counts: dict[str, int] = collections.Counter()
    soft_voxel_counts: dict[str, float] = {}
    syntax_counts: dict[str, int] = collections.Counter()
    think_word_counts: dict[str, int] = collections.Counter()
    reason_len_bins: dict[str, int] = collections.Counter()
    rgb_points: list[list[float]] = []

    for s in samples:
        p = s["parsed"]
        if p.get("status") != "valid":
            continue
        hex_counts[p["canonical_hex"]] += 1
        voxel_counts[p["voxel_bin_8"]] += 1
        rgb = p.get("rgb") or [0, 0, 0]
        add_soft_voxel(soft_voxel_counts, rgb, bin_width=48.0)
        rgb_points.append(rgb_to_geometry(rgb).tolist())

        syn = p.get("syntax") or {}
        if "letter_case" in syn:
            syntax_counts[f"case:{syn['letter_case']}|hash:{syn.get('has_hash', True)}"] += 1
        elif "space_after_comma" in syn:
            syntax_counts[f"space:{syn['space_after_comma']}"] += 1

        if p.get("first_think_word"):
            think_word_counts[p["first_think_word"]] += 1

        r_tok = (s.get("usage") or {}).get("reasoning_tokens")
        r_len = r_tok if (r_tok is not None and r_tok > 0) else p.get("reasoning_char_len", 0)
        if r_len == 0:
            r_bin = "0"
        else:
            r_bin = f"2^{int(math.log2(max(1, r_len)))}"
        reason_len_bins[r_bin] += 1

    rgb_arr = np.array(rgb_points, dtype=np.float64) if rgb_points else np.zeros((0, 3), dtype=np.float64)
    return {
        "n_valid": len(rgb_points),
        "hex_counts": dict(hex_counts),
        "voxel_counts": dict(voxel_counts),
        "soft_voxel_counts": soft_voxel_counts,
        "syntax_counts": dict(syntax_counts),
        "think_word_counts": dict(think_word_counts),
        "reason_len_bins": dict(reason_len_bins),
        "rgb_arr": rgb_arr,
    }


def compute_cell_distance(cell_a: dict[str, Any], cell_b: dict[str, Any]) -> dict[str, float]:
    """Compute all distance metrics between two summarized cells."""
    d_hex = jsd_base2(cell_a["hex_counts"], cell_b["hex_counts"])
    d_voxel = jsd_base2(cell_a["voxel_counts"], cell_b["voxel_counts"])
    d_soft_voxel = jsd_base2(cell_a["soft_voxel_counts"], cell_b["soft_voxel_counts"])
    e_raw, d_energy_norm, d_energy_reg = energy_distance_3d(cell_a["rgb_arr"], cell_b["rgb_arr"], delta0=ENERGY_DELTA0)
    w2_raw, w2_centroid, w2_cov = bures_wasserstein_3d(cell_a["rgb_arr"], cell_b["rgb_arr"])
    d_w2_norm = 1.0 - math.exp(-w2_raw / W2_LENGTH_SCALE)

    side_parts = [jsd_base2(cell_a["syntax_counts"], cell_b["syntax_counts"])]
    if cell_a["think_word_counts"] or cell_b["think_word_counts"]:
        side_parts.append(jsd_base2(cell_a["think_word_counts"], cell_b["think_word_counts"]))
    if set(cell_a["reason_len_bins"].keys()) != {"0"} or set(cell_b["reason_len_bins"].keys()) != {"0"}:
        side_parts.append(jsd_base2(cell_a["reason_len_bins"], cell_b["reason_len_bins"]))
    d_side = sum(side_parts) / len(side_parts)

    # Hybrid composite distance in [0, 1]
    d_hybrid = (
        0.35 * d_voxel
        + 0.25 * d_hex
        + 0.25 * d_energy_norm
        + 0.15 * d_side
    )
    # Explicit comparison variant: preserve the historical score and weights.
    d_hybrid_reg = (
        0.35 * d_voxel
        + 0.25 * d_hex
        + 0.25 * d_energy_reg
        + 0.15 * d_side
    )
    # Jitter-resistant manifold distance in [0, 1] (pure continuous/soft 3D geometry, no exact-string dependency)
    d_robust = 0.50 * d_soft_voxel + 0.50 * d_energy_reg

    return {
        "robust_manifold": d_robust,
        "hybrid": d_hybrid,
        "hybrid_reg": d_hybrid_reg,
        "soft_voxel_jsd": d_soft_voxel,
        "energy_reg": d_energy_reg,
        "voxel_jsd": d_voxel,
        "hex_jsd": d_hex,
        "energy_norm": d_energy_norm,
        "energy_raw": e_raw,
        "w2_norm": d_w2_norm,
        "w2_raw": w2_raw,
        "w2_centroid": w2_centroid,
        "w2_cov": w2_cov,
        "side_jsd": d_side,
    }


# ---------------------------------------------------------------------------
# Biometric ROC, AUC, EER & Query-Budget Curve
# ---------------------------------------------------------------------------

def compute_roc_eer(genuine_scores: list[float], impostor_scores: list[float]) -> dict[str, Any]:
    """
    Compute ROC Area Under Curve (AUC), Equal Error Rate (EER), and optimal threshold tau*.
    Lower score = closer / more likely genuine. Always returns finite JSON-safe numbers.
    """
    if not genuine_scores or not impostor_scores:
        return {
            "auc": 0.5,
            "auc_raw": 0.5,
            "eer": 0.5,
            "eer_raw": 0.5,
            "eer_linear": 0.5,
            "eer_linear_raw": 0.5,
            "threshold": 0.5,
            "threshold_raw": 0.5,
            "threshold_midpoint": 0.5,
            "far_at_threshold": 0.5,
            "frr_at_threshold": 0.5,
            "genuine_median": None,
            "impostor_median": None,
            "impostor_p05": None,
        }

    gen_raw = np.asarray(genuine_scores, dtype=np.float64)
    imp_raw = np.asarray(impostor_scores, dtype=np.float64)
    gen_arr = np.sort(gen_raw[np.isfinite(gen_raw)])
    imp_arr = np.sort(imp_raw[np.isfinite(imp_raw)])
    n_g = len(gen_arr)
    n_i = len(imp_arr)
    if n_g == 0 or n_i == 0:
        return {
            "auc": 0.5,
            "auc_raw": 0.5,
            "eer": 0.5,
            "eer_raw": 0.5,
            "eer_linear": 0.5,
            "eer_linear_raw": 0.5,
            "threshold": 0.5,
            "threshold_raw": 0.5,
            "threshold_midpoint": 0.5,
            "far_at_threshold": 0.5,
            "frr_at_threshold": 0.5,
            "genuine_median": None,
            "impostor_median": None,
            "impostor_p05": None,
        }

    # Vectorized exact Mann-Whitney U AUC: P(gen < imp) + 0.5 * P(gen == imp)
    less_counts = n_i - np.searchsorted(imp_arr, gen_arr, side="right")
    eq_counts = np.searchsorted(imp_arr, gen_arr, side="right") - np.searchsorted(imp_arr, gen_arr, side="left")
    auc = float(np.sum(less_counts + 0.5 * eq_counts)) / (n_g * n_i)
    # Strictly finite candidate thresholds (prepend min_val - 1e-9 to represent FRR=1, FAR=0)
    min_val = float(min(gen_arr[0], imp_arr[0]))
    candidates = np.unique(np.concatenate([[min_val - 1e-9], gen_arr, imp_arr]))
    frr_vec = (n_g - np.searchsorted(gen_arr, candidates, side="right")) / n_g
    far_vec = np.searchsorted(imp_arr, candidates, side="right") / n_i
    gaps = np.abs(frr_vec - far_vec)
    best_idx = int(np.argmin(gaps))
    best_eer = float(0.5 * (frr_vec[best_idx] + far_vec[best_idx]))
    best_tau = float(candidates[best_idx])

    # Linear ROC intersection where FAR - FRR crosses 0
    diff = far_vec - frr_vec
    cross_indices = np.flatnonzero(diff >= 0.0)
    if len(cross_indices) == 0:
        eer_linear = float(best_eer)
    else:
        ix = int(cross_indices[0])
        if ix == 0 or abs(diff[ix] - diff[ix - 1]) < 1e-12:
            eer_linear = float(far_vec[ix])
        else:
            w = -diff[ix - 1] / (diff[ix] - diff[ix - 1])
            eer_linear = float(far_vec[ix - 1] + w * (far_vec[ix] - far_vec[ix - 1]))

    gen = gen_arr.tolist()
    imp = imp_arr.tolist()
    max_gen = float(gen_arr[-1])
    min_imp = float(imp_arr[0])
    return {
        "auc": round(auc, 4),
        "auc_raw": auc,
        "eer": round(best_eer, 4),
        "eer_raw": best_eer,
        "eer_linear": round(eer_linear, 4),
        "eer_linear_raw": eer_linear,
        "threshold": round(best_tau, 4),
        "threshold_raw": best_tau,
        "threshold_midpoint": 0.5 * max_gen + 0.5 * min_imp,
        "far_at_threshold": round(float(far_vec[best_idx]), 4),
        "frr_at_threshold": round(float(frr_vec[best_idx]), 4),
        "genuine_median": round(statistics.median(gen), 4),
        "impostor_median": round(statistics.median(imp), 4),
        "impostor_p05": round(imp[max(0, int(0.05 * n_i) - 1)], 4),
    }


def compute_query_budget_curve(
    genuine_cell_Matrix: list[dict[str, float]],
    impostor_cell_Matrix: list[dict[str, float]],
    all_cells: list[str],
    k_values: list[int],
    n_resamples: int = 200,
    seed: int = 42,
) -> dict[int, dict[str, float]]:
    """Resample random k-subsets of probe cells to quantify EER vs query budget."""
    rng = random.Random(seed)
    results: dict[int, dict[str, float]] = {}
    max_k = len(all_cells)

    for k in k_values:
        if k > max_k or k <= 0:
            continue
        eers: list[float] = []
        trials = 1 if k == max_k else n_resamples
        for _ in range(trials):
            subset = all_cells if k == max_k else rng.sample(all_cells, k)
            gen_scores = []
            for row in genuine_cell_Matrix:
                vals = [row[c] for c in subset if c in row]
                if vals:
                    gen_scores.append(sum(vals) / len(vals))
            imp_scores = []
            for row in impostor_cell_Matrix:
                vals = [row[c] for c in subset if c in row]
                if vals:
                    imp_scores.append(sum(vals) / len(vals))
            if gen_scores and imp_scores:
                eers.append(compute_roc_eer(gen_scores, imp_scores)["eer"])

        if eers:
            eers_sorted = sorted(eers)
            p05 = eers_sorted[max(0, int(0.05 * len(eers_sorted)))]
            p95 = eers_sorted[min(len(eers_sorted) - 1, int(0.95 * len(eers_sorted)))]
            results[k] = {
                "mean_eer_pct": round(100.0 * statistics.mean(eers), 2),
                "p05_eer_pct": round(100.0 * p05, 2),
                "p95_eer_pct": round(100.0 * p95, 2),
            }
    return results


# ---------------------------------------------------------------------------
# Main Analysis Pipeline
# ---------------------------------------------------------------------------

def run_analysis(args: argparse.Namespace) -> dict[str, Any]:
    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"Input JSONL not found: {in_path}")

    from collect import parse_color_response

    seen_rows: dict[str, tuple[Any, ...]] = {}
    rows: list[dict[str, Any]] = []
    with in_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            tk = obj.get("trial_key")
            if not isinstance(tk, str) or not tk.strip():
                raise ValueError(f"Missing or invalid trial_key: {tk!r}")
            rep_val = obj.get("rep")
            if not isinstance(rep_val, int) or isinstance(rep_val, bool) or rep_val < 1:
                raise ValueError(f"Invalid rep field (must be positive int): {rep_val!r}")
            old_p = obj.get("parsed") or {}
            if old_p.get("parser_version") not in (None, "2.1", "3.0"):
                raise ValueError(f"Unsupported parser_version: {old_p.get('parser_version')!r}")
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
            if tk in seen_rows:
                if seen_rows[tk] != sig:
                    raise ValueError(f"Conflicting duplicate trial_key: {tk}")
                continue
            seen_rows[tk] = sig
            new_p = parse_color_response(
                raw_text=obj.get("raw_text", ""),
                expected_format=obj.get("format", "hex"),
                explicit_reasoning=obj.get("explicit_reasoning", ""),
            )
            leg = obj.get("legacy_reasoning_meta") or old_p
            if not obj.get("explicit_reasoning") and leg.get("has_reasoning_trace"):
                new_p["has_reasoning_trace"] = True
                new_p["reasoning_char_len"] = leg.get("reasoning_char_len", 0)
                new_p["first_think_word"] = leg.get("first_think_word")
            obj["parsed"] = new_p
            rows.append(obj)
    by_target: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        by_target[r["target_id"]].append(r)

    target_ids = sorted(by_target.keys())
    all_cells_set: set[str] = set()

    # 1. Per-target & per-cell summaries + screens
    target_summaries: dict[str, Any] = {}
    full_cells: dict[str, dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    odd_cells: dict[str, dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    even_cells: dict[str, dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    anomalies: dict[str, list[dict[str, Any]]] = {
        "response_caching_suspects": [],
        "unrequested_reasoning_traces": [],
        "hidden_token_overhead": [],
    }

    all_cell_hex_entropies: list[float] = []
    all_cell_voxel_entropies: list[float] = []
    all_cell_modal_shares: list[float] = []

    for tid in target_ids:
        t_rows = by_target[tid]
        t1_rows = [r for r in t_rows if abs(float(r.get("temperature", 1.0)) - 1.0) < 1e-4]
        t0_rows = [r for r in t_rows if abs(float(r.get("temperature", 1.0)) - 0.0) < 1e-4]

        status_counts = collections.Counter(r["parsed"]["status"] for r in t_rows)
        latencies = [float(r["latency_ms"]) for r in t1_rows if r.get("latency_ms") is not None]
        median_lat = statistics.median(latencies) if latencies else 0.0

        # Screen for unrequested reasoning or hidden token overhead
        reason_trace_count = sum(1 for r in t_rows if r["parsed"].get("has_reasoning_trace"))
        high_overhead_count = sum(
            1 for r in t_rows
            if ((r.get("usage") or {}).get("output_tokens") or 0) > 35
            and not r["parsed"].get("has_reasoning_trace")
        )
        if reason_trace_count > 0:
            anomalies["unrequested_reasoning_traces"].append({
                "target_id": tid,
                "count": reason_trace_count,
                "share": round(reason_trace_count / len(t_rows), 4),
            })
        if high_overhead_count > 0:
            anomalies["hidden_token_overhead"].append({
                "target_id": tid,
                "count": high_overhead_count,
                "share": round(high_overhead_count / len(t_rows), 4),
            })

        # T=0 greedy determinism check
        t0_by_cell: dict[str, list[str]] = collections.defaultdict(list)
        for r in t0_rows:
            if r["parsed"]["status"] == "valid":
                ckey = f"{r['task_id']}|{r['lang']}"
                t0_by_cell[ckey].append(r["parsed"]["canonical_hex"])
        t0_det_cells = [
            1 if len(set(vals)) == 1 else 0
            for vals in t0_by_cell.values()
            if len(vals) >= 2
        ]

        # Group T=1.0 by cell
        t1_by_cell: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for r in t1_rows:
            ckey = f"{r['task_id']}|{r['lang']}"
            t1_by_cell[ckey].append(r)

        t_hex_ent: list[float] = []
        t_vox_ent: list[float] = []
        t_modal: list[float] = []

        for ckey, c_rows in sorted(t1_by_cell.items()):
            cell_full = summarize_cell_samples(c_rows)
            if cell_full["n_valid"] >= args.min_cell_samples:
                full_cells[tid][ckey] = cell_full
                all_cells_set.add(ckey)

                h_ent = shannon_entropy_bits(cell_full["hex_counts"])
                v_ent = shannon_entropy_bits(cell_full["voxel_counts"])
                m_share = max(cell_full["hex_counts"].values()) / cell_full["n_valid"]
                t_hex_ent.append(h_ent)
                t_vox_ent.append(v_ent)
                t_modal.append(m_share)
                all_cell_hex_entropies.append(h_ent)
                all_cell_voxel_entropies.append(v_ent)
                all_cell_modal_shares.append(m_share)

                # Response-level caching screen (Sec. VII-C): single unique answer at T=1.0 + latency < 0.5 * median
                c_lats = [float(r["latency_ms"]) for r in c_rows if r.get("latency_ms") is not None]
                c_med_lat = statistics.median(c_lats) if c_lats else 0.0
                if len(cell_full["hex_counts"]) == 1 and median_lat > 0 and c_med_lat < 0.5 * median_lat:
                    anomalies["response_caching_suspects"].append({
                        "target_id": tid,
                        "cell": ckey,
                        "collapsed_hex": next(iter(cell_full["hex_counts"].keys())),
                        "cell_median_latency_ms": round(c_med_lat, 2),
                        "target_median_latency_ms": round(median_lat, 2),
                    })

            # Strict integer-rep Odd / Even split for biometric verification (no OR leakage)
            odd_r = [r for r in c_rows if int(r["rep"]) % 2 == 1]
            even_r = [r for r in c_rows if int(r["rep"]) % 2 == 0]
            c_odd = summarize_cell_samples(odd_r)
            c_even = summarize_cell_samples(even_r)
            if c_odd["n_valid"] >= args.min_split_samples and c_even["n_valid"] >= args.min_split_samples:
                odd_cells[tid][ckey] = c_odd
                even_cells[tid][ckey] = c_even

        target_summaries[tid] = {
            "total_responses": len(t_rows),
            "validity_rate": round(status_counts["valid"] / max(1, len(t_rows)), 4),
            "valid_cells_count": len(full_cells[tid]),
            "median_hex_entropy_bits": round(statistics.median(t_hex_ent), 3) if t_hex_ent else None,
            "median_voxel_entropy_bits": round(statistics.median(t_vox_ent), 3) if t_vox_ent else None,
            "median_modal_share": round(statistics.median(t_modal), 3) if t_modal else None,
            "t0_greedy_determinism_rate": round(sum(t0_det_cells) / len(t0_det_cells), 4) if t0_det_cells else None,
            "median_latency_ms": round(median_lat, 2),
        }

    all_cells = sorted(all_cells_set)

    # 2. Split-Half Genuine vs Impostor Trials (RQ1 & RQ3)
    metrics_list = ["robust_manifold", "energy_reg", "soft_voxel_jsd", "hybrid", "voxel_jsd", "hex_jsd", "energy_norm", "w2_norm", "side_jsd"]
    genuine_by_metric: dict[str, list[float]] = collections.defaultdict(list)
    impostor_by_metric: dict[str, list[float]] = collections.defaultdict(list)
    genuine_hybrid_per_cell: list[dict[str, float]] = []
    impostor_hybrid_per_cell: list[dict[str, float]] = []

    for tid in target_ids:
        shared = sorted(set(odd_cells[tid].keys()) & set(even_cells[tid].keys()))
        if not shared:
            continue
        cell_dists = {c: compute_cell_distance(odd_cells[tid][c], even_cells[tid][c]) for c in shared}
        genuine_hybrid_per_cell.append({c: cell_dists[c]["hybrid"] for c in shared})
        for m in metrics_list:
            genuine_by_metric[m].append(sum(cell_dists[c][m] for c in shared) / len(shared))

    for i, tid_a in enumerate(target_ids):
        for j, tid_b in enumerate(target_ids):
            if i == j:
                continue
            shared = sorted(set(odd_cells[tid_a].keys()) & set(even_cells[tid_b].keys()))
            if not shared:
                continue
            cell_dists = {c: compute_cell_distance(odd_cells[tid_a][c], even_cells[tid_b][c]) for c in shared}
            impostor_hybrid_per_cell.append({c: cell_dists[c]["hybrid"] for c in shared})
            for m in metrics_list:
                impostor_by_metric[m].append(sum(cell_dists[c][m] for c in shared) / len(shared))

    verification_metrics = {
        m: compute_roc_eer(genuine_by_metric[m], impostor_by_metric[m])
        for m in metrics_list
    }

    budget_curve = compute_query_budget_curve(
        genuine_cell_Matrix=genuine_hybrid_per_cell,
        impostor_cell_Matrix=impostor_hybrid_per_cell,
        all_cells=all_cells,
        k_values=[1, 2, 4, 8, 16, 24, 32, 40],
    )

    # 3. Full Pairwise Distance Matrix & 1-NN Lineage Lookup (RQ2 & RQ4)
    pairwise_matrix: dict[str, dict[str, dict[str, float]]] = collections.defaultdict(dict)
    nearest_neighbors: list[dict[str, Any]] = []
    gen_med_hybrid = verification_metrics["hybrid"].get("genuine_median", 0.14)
    imp_p05_hybrid = verification_metrics["hybrid"].get("impostor_p05", 0.25)

    for i, tid_a in enumerate(target_ids):
        best_peer = None
        best_dist = 999.0
        best_breakdown: dict[str, float] = {}
        for j, tid_b in enumerate(target_ids):
            if i == j:
                continue
            shared = sorted(set(full_cells[tid_a].keys()) & set(full_cells[tid_b].keys()))
            if not shared:
                continue
            c_dists = [compute_cell_distance(full_cells[tid_a][c], full_cells[tid_b][c]) for c in shared]
            avg_d = {m: round(sum(d[m] for d in c_dists) / len(c_dists), 4) for m in metrics_list}
            avg_d["w2_raw_rgb100"] = round(sum(d["w2_raw"] for d in c_dists) / len(c_dists), 2)
            avg_d["shared_cells"] = len(shared)
            pairwise_matrix[tid_a][tid_b] = avg_d

            if avg_d["hybrid"] < best_dist:
                best_dist = avg_d["hybrid"]
                best_peer = tid_b
                best_breakdown = avg_d

        if best_peer is not None:
            flag = "normal"
            if best_dist <= gen_med_hybrid * 1.15:
                flag = "IDENTICAL_DISTRIBUTION_SUSPECT"
            elif best_dist <= imp_p05_hybrid:
                flag = "CLOSE_LINEAGE_NEIGHBOR"
            nearest_neighbors.append({
                "target_id": tid_a,
                "nearest_neighbor": best_peer,
                "hybrid_distance": best_dist,
                "voxel_jsd": best_breakdown.get("voxel_jsd"),
                "hex_jsd": best_breakdown.get("hex_jsd"),
                "w2_raw_rgb100": best_breakdown.get("w2_raw_rgb100"),
                "flag": flag,
            })

    report = {
        "analysis_protocol": dict(ANALYSIS_PROTOCOL),
        "census_overview": {
            "total_targets": len(target_ids),
            "total_responses": len(rows),
            "active_probe_cells": len(all_cells),
            "overall_median_hex_entropy_bits": round(statistics.median(all_cell_hex_entropies), 3) if all_cell_hex_entropies else None,
            "overall_median_voxel_entropy_bits": round(statistics.median(all_cell_voxel_entropies), 3) if all_cell_voxel_entropies else None,
            "overall_median_modal_share": round(statistics.median(all_cell_modal_shares), 3) if all_cell_modal_shares else None,
        },
        "target_summaries": target_summaries,
        "verification_roc_eer": verification_metrics,
        "query_budget_curve_hybrid": budget_curve,
        "nearest_neighbors": nearest_neighbors,
        "pairwise_distances": dict(pairwise_matrix),
        "ecosystem_anomalies": anomalies,
    }

    if args.output_json:
        out_p = Path(args.output_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print_console_report(report)
    return report


def print_console_report(rep: dict[str, Any]) -> None:
    ov = rep["census_overview"]
    print("=" * 78)
    print(" RGB/HEX BEHAVIORAL FINGERPRINT ANALYSIS REPORT")
    print("=" * 78)
    print(
        f"Targets: {ov['total_targets']} | Responses: {ov['total_responses']} | "
        f"Active Cells: {ov['active_probe_cells']} | "
        f"Median Hex Entropy: {ov['overall_median_hex_entropy_bits']} bits | "
        f"Modal Share: {ov['overall_median_modal_share']}"
    )
    print("-" * 78)
    print("1. PER-TARGET SUMMARY (RQ1)")
    print(f"  {'Target ID':<28} {'Valid%':>7} {'Cells':>5} {'HexEnt':>7} {'VoxEnt':>7} {'Modal':>6} {'T0Det%':>7}")
    for tid, s in rep["target_summaries"].items():
        v_pct = f"{100.0 * s['validity_rate']:.1f}%"
        t0_pct = f"{100.0 * s['t0_greedy_determinism_rate']:.1f}%" if s["t0_greedy_determinism_rate"] is not None else "  N/A "
        print(
            f"  {tid:<28} {v_pct:>7} {s['valid_cells_count']:>5} "
            f"{str(s['median_hex_entropy_bits']):>7} {str(s['median_voxel_entropy_bits']):>7} "
            f"{str(s['median_modal_share']):>6} {t0_pct:>7}"
        )

    print("-" * 78)
    print("2. BIOMETRIC VERIFICATION PERFORMANCE (RQ3: Odd/Even Split-Half)")
    print(f"  {'Metric':<15} {'AUC':>7} {'DiscEER%':>9} {'LinEER%':>9} {'Tau*':>7} {'GenMed':>8} {'ImpMed':>8}")
    for m, v in rep["verification_roc_eer"].items():
        print(
            f"  {m:<15} {v['auc']:>7.4f} {100.0 * v['eer_raw']:>8.2f}% {100.0 * v['eer_linear_raw']:>8.2f}% "
            f"{v['threshold']:>7.4f} {v['genuine_median']:>8.4f} {v['impostor_median']:>8.4f}"
        )

    if rep["query_budget_curve_hybrid"]:
        print("-" * 78)
        print("3. QUERY-BUDGET CURVE (Hybrid EER vs Number of Probe Cells k)")
        parts = [f"k={k}: {v['mean_eer_pct']:.1f}% [{v['p05_eer_pct']:.1f}-{v['p95_eer_pct']:.1f}%]" for k, v in rep["query_budget_curve_hybrid"].items()]
        print("  " + " | ".join(parts))

    if rep["nearest_neighbors"]:
        print("-" * 78)
        print("4. NEAREST-NEIGHBOR LINEAGE & SUBSTITUTION AUDIT (RQ2 & RQ4)")
        print(f"  {'Target ID':<24} -> {'Nearest Neighbor':<24} {'Hybrid':>7} {'VoxJSD':>7} {'W2(RGB)':>8}  {'Status'}")
        for nn in rep["nearest_neighbors"]:
            print(
                f"  {nn['target_id']:<24} -> {nn['nearest_neighbor']:<24} "
                f"{nn['hybrid_distance']:>7.4f} {nn['voxel_jsd']:>7.4f} "
                f"{nn['w2_raw_rgb100']:>8.2f}  {nn['flag']}"
            )
    print("=" * 78)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Analyze RGB/Hex LLM Fingerprints from JSONL")
    p.add_argument("--input", default="data/responses.jsonl", help="Input JSONL file from collect.py")
    p.add_argument("--output-json", default="data/analysis_rgb_report.json", help="Output JSON report path")
    p.add_argument("--min-cell-samples", type=int, default=6, help="Min valid samples per cell for full comparison")
    p.add_argument("--min-split-samples", type=int, default=3, help="Min valid samples per half for split-half ROC")
    return p


if __name__ == "__main__":
    parser = build_arg_parser()
    run_analysis(parser.parse_args())
