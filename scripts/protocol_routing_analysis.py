#!/usr/bin/env python3
"""Offline protocol-hyperparameter, sub-provider, cell-eligibility, and permutation-routing analyses.

Strictly read-only on all raw logs and prior frozen artifacts; blocks network
and subprocess access via Python audit hooks and verifies protected SHA-256 digests before and after execution.

Run:
  UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy \
    python -B scripts/protocol_routing_analysis.py
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import numpy as np
import analyze as an
from hueprint_audit.core import (
    SEED,
    energy_test_matrix,
    group,
    load,
    matrix,
    operating,
    permutation_p,
    permutation_weights,
    pvalue_stats,
    save,
    seed_for,
    stats,
    thresholds,
)
from hueprint_audit.experiments import EXT, FILES, b20, make_s1, within

OUT = ROOT / 'results/protocol_audit'
SEEDS = tuple(range(2026111300, 2026111320))
PROBS = (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0)
N_PERM = 999
ALPHA = 0.05


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def guard(event: str, args) -> None:
    if event in (
        'socket.connect',
        'socket.connect_ex',
        'socket.getaddrinfo',
        'socket.sendto',
        'subprocess.Popen',
    ):
        raise RuntimeError('Offline-only analysis blocked event: ' + event)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def family_map() -> dict[str, dict]:
    fm = json.loads((ROOT / 'config/family_map.json').read_text())['families']
    cfg = json.loads((ROOT / EXT / 'configs/targets.s3_20models_locked64.json').read_text())['targets']
    for target in cfg:
        fm[target['id']] = {'family': target['family'], 'vendor': target['model'].split('/')[0]}
    return fm


def raw_jsonl_rows(rel_path: str) -> list[dict]:
    rows = []
    with (ROOT / rel_path).open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def audit_protocols_and_providers(data: dict, out: Path) -> dict:
    """Forensic summary of request envelopes, temperatures, providers, and S1/S3/S4 subgroups."""
    cohort_summaries = []
    for name, rel in FILES.items():
        raw_rows = raw_jsonl_rows(rel)
        clean_rows = data[name]
        protocols = collections.Counter(str(r.get('protocol')) for r in clean_rows)
        temp_cfg = collections.Counter(str(r.get('temperature')) for r in clean_rows)
        temp_sent = collections.Counter(str(r.get('temperature_sent')) for r in clean_rows)
        max_tok = collections.Counter(str(r.get('max_tokens')) for r in clean_rows)
        providers_per_target = {}
        for tid in sorted({r['target_id'] for r in clean_rows}):
            trows = [r for r in clean_rows if r['target_id'] == tid]
            provs = collections.Counter(
                str(r.get('provider') or (r.get('response_meta') or {}).get('provider') or 'unspecified')
                for r in trows
            )
            providers_per_target[tid] = dict(provs)
        multi_provider_targets = {
            tid: pmap for tid, pmap in providers_per_target.items() if len(pmap) > 1
        }
        cohort_summaries.append({
            'cohort': name,
            'file': rel,
            'raw_records': len(raw_rows),
            'dedup_records': len(clean_rows),
            'n_targets': len(providers_per_target),
            'protocols': dict(protocols),
            'temperature_configured': dict(temp_cfg),
            'temperature_sent': dict(temp_sent),
            'max_tokens': dict(max_tok),
            'multi_provider_target_count': len(multi_provider_targets),
            'multi_provider_targets': multi_provider_targets,
        })

    # S1 subgroup stratification: 9 models without reasoning.effort vs 5 models with reasoning.effort="low"
    s1_or_cfg = json.loads((ROOT / EXT / 'configs/targets.s1_or_crossgateway.json').read_text())['targets']
    s1_cf_cfg = {
        t['id']: t
        for t in json.loads((ROOT / EXT / 'configs/targets.s1_cf_t21d.json').read_text())['targets']
    }
    reasoning_cf_ids = sorted(
        t['paired_cf_id'] for t in s1_or_cfg if (t.get('extra_body') or {}).get('reasoning')
    )
    standard_cf_ids = sorted(
        t['paired_cf_id'] for t in s1_or_cfg if not (t.get('extra_body') or {}).get('reasoning')
    )
    cf0, cf21, or21 = make_s1(data)
    b_ref, b_q = within(b20(data['B']), 1)
    _, b_mats, _ = matrix(b_ref, b_q)
    tau_b_energy = thresholds(b_mats['energy_reg'])['tau_mid']
    tau_b_hyb = thresholds(b_mats['hybrid'])['tau_mid']

    s1_stratified = {}
    for pair_name, ref_g, qry_g in [('CF0_CF21', cf0, cf21), ('CF21_OR21', cf21, or21), ('CF0_OR21', cf0, or21)]:
        ids_all, mats_all, _ = matrix(ref_g, qry_g)
        _, _, pvals_all = energy_test_matrix(ref_g, qry_g, N_PERM)
        per_model = []
        for idx, tid in enumerate(ids_all):
            or_entry = next(t for t in s1_or_cfg if t['paired_cf_id'] == tid)
            cf_entry = s1_cf_cfg[tid]
            per_model.append({
                'cf_id': tid,
                'or_id': or_entry['id'],
                'cf_model': cf_entry['model'],
                'or_model': or_entry['model'],
                'cf_send_temperature': bool(cf_entry.get('send_temperature', False)),
                'or_send_temperature': bool(or_entry.get('send_temperature', True)),
                'or_reasoning_effort': (or_entry.get('extra_body') or {}).get('reasoning', {}).get('effort'),
                'speculative_decode_mismatch': ('-sd' in cf_entry['model']) != ('-sd' in or_entry['model']),
                'genuine_energy_reg': float(mats_all['energy_reg'][idx, idx]),
                'genuine_hybrid': float(mats_all['hybrid'][idx, idx]),
                'perm_pvalue': float(pvals_all[idx, idx]),
                'perm_rejected_at_005': bool(pvals_all[idx, idx] <= ALPHA),
            })

        def subgroup_metrics(sub_ids: list[str]) -> dict:
            ix = [ids_all.index(t) for t in sub_ids]
            sub_p = pvals_all[np.ix_(ix, ix)]
            sub_e = mats_all['energy_reg'][np.ix_(ix, ix)]
            sub_h = mats_all['hybrid'][np.ix_(ix, ix)]
            return {
                'n_models': len(sub_ids),
                'ids': sub_ids,
                'perm_same_model_rejection_rate': float(np.mean(np.diag(sub_p) <= ALPHA)),
                'perm_same_model_rejections': int(np.sum(np.diag(sub_p) <= ALPHA)),
                'perm_diff_model_rejection_rate': float(np.mean(sub_p[~np.eye(len(ix), dtype=bool)] <= ALPHA)),
                'energy_reg_eer': stats(sub_e)['eer'],
                'energy_reg_frr_at_B_tau': operating(sub_e, tau_b_energy)['frr'],
                'energy_reg_far_at_B_tau': operating(sub_e, tau_b_energy)['far'],
                'hybrid_eer': stats(sub_h)['eer'],
                'hybrid_frr_at_B_tau': operating(sub_h, tau_b_hyb)['frr'],
                'hybrid_far_at_B_tau': operating(sub_h, tau_b_hyb)['far'],
            }

        s1_stratified[pair_name] = {
            'all_14': subgroup_metrics(ids_all),
            'standard_9_no_reasoning_override': subgroup_metrics(standard_cf_ids),
            'reasoning_5_effort_low_override': subgroup_metrics(reasoning_cf_ids),
            'per_model': per_model,
        }

    # S3 odd/even sub-provider mixture symmetry & reasoning-token tail analysis
    s3_odd_even = []
    for tid in sorted({r['target_id'] for r in data['S3_color']}):
        trows = [r for r in data['S3_color'] if r['target_id'] == tid]
        odd = [r for r in trows if r['rep'] % 2 == 1]
        even = [r for r in trows if r['rep'] % 2 == 0]
        p_odd = collections.Counter(str(r.get('provider') or 'unspecified') for r in odd)
        p_even = collections.Counter(str(r.get('provider') or 'unspecified') for r in even)
        all_p = sorted(set(p_odd) | set(p_even))
        tv = 0.5 * sum(abs(p_odd[p] / len(odd) - p_even[p] / len(even)) for p in all_p)
        out_tok_odd = [int((r.get('usage') or {}).get('output_tokens') or 0) for r in odd]
        out_tok_even = [int((r.get('usage') or {}).get('output_tokens') or 0) for r in even]
        in_tok_even = sum(int((r.get('usage') or {}).get('input_tokens') or 0) for r in even)
        sum_out_even = sum(out_tok_even)
        s3_odd_even.append({
            'target_id': tid,
            'n_providers': len(all_p),
            'providers_odd': dict(p_odd),
            'providers_even': dict(p_even),
            'odd_even_provider_tv_distance': float(tv),
            'query_input_tokens': in_tok_even,
            'query_output_tokens': sum_out_even,
            'query_output_tokens_median_per_call': float(np.median(out_tok_even)),
            'query_output_tokens_max_per_call': int(max(out_tok_even)),
            'enrollment_output_tokens_max_per_call': int(max(out_tok_odd)),
            'scenario_L_query_usd': float(0.71e-6 * (in_tok_even + sum_out_even)),
            'scenario_G_query_usd': float(2.50e-6 * in_tok_even + 10.0e-6 * sum_out_even),
        })

    g_costs = sorted(r['scenario_G_query_usd'] for r in s3_odd_even)
    l_costs = sorted(r['scenario_L_query_usd'] for r in s3_odd_even)
    g_non_outlier = [r['scenario_G_query_usd'] for r in s3_odd_even if r['target_id'] != 's3-deepseek-v3.2']
    deepseek_providers = collections.defaultdict(list)
    for r in data['S3_color']:
        if r['target_id'] == 's3-deepseek-v3.2':
            prov = str(r.get('provider') or 'unspecified')
            deepseek_providers[prov].append(int((r.get('usage') or {}).get('output_tokens') or 0))
    deepseek_breakdown = {
        prov: {
            'calls': len(toks),
            'min_out_tokens': int(min(toks)),
            'median_out_tokens': float(np.median(toks)),
            'max_out_tokens': int(max(toks)),
            'gt_64_calls': int(sum(x > 64 for x in toks)),
        }
        for prov, toks in sorted(deepseek_providers.items())
    }

    result = {
        'cohorts': cohort_summaries,
        's1_stratified': s1_stratified,
        's3_provider_and_cost_audit': {
            'multi_provider_count': sum(r['n_providers'] > 1 for r in s3_odd_even),
            'multi_provider_max_tv_odd_vs_even': float(
                max(r['odd_even_provider_tv_distance'] for r in s3_odd_even if r['n_providers'] > 1)
            ),
            'multi_provider_mean_tv_odd_vs_even': float(
                np.mean([r['odd_even_provider_tv_distance'] for r in s3_odd_even if r['n_providers'] > 1])
            ),
            'scenario_L_query_usd_quantiles': {
                'min': float(min(l_costs)),
                'median': float(np.median(l_costs)),
                'p90': float(np.quantile(l_costs, 0.90)),
                'max': float(max(l_costs)),
            },
            'scenario_G_query_usd_quantiles': {
                'min': float(min(g_costs)),
                'median': float(np.median(g_costs)),
                'p90': float(np.quantile(g_costs, 0.90)),
                'max_19_of_20_excluding_deepseek_v32': float(max(g_non_outlier)),
                'max_all_20': float(max(g_costs)),
            },
            'deepseek_v32_provider_token_breakdown': deepseek_breakdown,
            'per_target': s3_odd_even,
        },
    }
    save(out / 'protocol_hyperparameter_audit.json', result)
    return result


def arrays(rows: list[dict]) -> np.ndarray:
    return (
        np.array([r['parsed']['rgb'] for r in rows if r['parsed']['status'] == 'valid'], dtype=float)
        .reshape(-1, 3)
        * (100.0 / 255.0)
    )


def select_cells(rows: list[dict], k: int) -> list[str]:
    cells = sorted({f"{r['task_id']}|{r['lang']}" for r in rows})
    if k == 10:
        cells = [c for c in cells if c.endswith('|en')]
    elif k == 20:
        cells = [c for c in cells if c.endswith(('|en', '|zh'))]
    if len(cells) != k:
        raise AssertionError((k, len(cells)))
    return cells


def protocol_groups(rows: list[dict], k: int, nref: int):
    cells = select_cells(rows, k)
    raw = group(rows)
    ref, query = {}, {}
    for t, cs in raw.items():
        ref[t], query[t] = {}, {}
        for c in cells:
            rs = sorted(cs[c], key=lambda r: r['rep'])
            ref[t][c] = [r for r in rs if r['rep'] % 2][:nref]
            query[t][c] = [r for r in rs if not r['rep'] % 2]
            assert len(ref[t][c]) == nref
    return ref, query, cells


def clean_matrix_vreg(ref: dict, query: dict, cells: list[str], nq: int):
    ids = sorted(ref)
    mat = np.zeros((len(ids), len(ids)))
    for i, t in enumerate(ids):
        for j, u in enumerate(ids):
            vals = []
            for c in cells:
                x, y = arrays(ref[t][c]), arrays(query[u][c][:nq])
                if len(x) and len(y):
                    vals.append(an.energy_distance_3d(x, y)[2])
            mat[i, j] = sum(vals) / len(vals)
    return ids, mat


def eval_mixed_cell_vreg_and_perm(
    ref_rows: list[dict],
    genuine_pool: list[dict],
    fallback_pool: list[dict],
    order_g: np.ndarray,
    order_f: np.ndarray,
    uniforms: np.ndarray,
    ww_cache: dict,
    label: str,
    cell: str,
):
    """Vectorized exact evaluation of both D_E-reg and 999-perm energy test on (S, P)."""
    x = arrays(ref_rows)
    n_seeds = len(order_g)
    n_probs = len(PROBS)
    shape = (n_seeds, n_probs)
    pool = genuine_pool + fallback_pool
    chosen = np.where(
        uniforms[:, None, :] < np.array(PROBS)[None, :, None],
        order_g[:, None, :],
        order_f[:, None, :] + len(genuine_pool),
    )
    fallback_n = (chosen >= len(genuine_pool)).sum(axis=-1)
    n = len(x)
    if n == 0:
        return (
            np.zeros(shape),
            np.zeros((n_seeds, n_probs, N_PERM + 1)),
            np.zeros(shape, dtype=bool),
            fallback_n,
        )

    coords_pool = (
        np.array(
            [r['parsed']['rgb'] if r['parsed']['status'] == 'valid' else [0, 0, 0] for r in pool],
            dtype=float,
        )
        * (100.0 / 255.0)
    )
    valid_pool = np.array([r['parsed']['status'] == 'valid' for r in pool], dtype=bool)
    keep = valid_pool[chosen]  # (S, P, nq)
    counts = keep.sum(axis=-1)  # (S, P)

    # Regularized V-score (exact match to service_audit_analysis.py)
    cross = np.linalg.norm(x[:, None] - coords_pool[None, :], axis=-1).mean(axis=0)
    yy = np.linalg.norm(coords_pool[:, None] - coords_pool[None, :], axis=-1)
    aa = np.linalg.norm(x[:, None] - x[None, :], axis=-1).mean()
    ab = np.sum(cross[chosen] * keep, axis=-1) / np.maximum(counts, 1)
    bb = (
        yy[chosen[..., :, None], chosen[..., None, :]]
        * keep[..., :, None]
        * keep[..., None, :]
    ).sum(axis=(-1, -2)) / np.maximum(counts, 1) ** 2
    vreg_score = np.maximum(0.0, ab - 0.5 * (aa + bb)) / (ab + an.ENERGY_DELTA0)

    # Stratified conditional permutation values: (S, P, 1000)
    all_pts = np.concatenate([x, coords_pool], axis=0)
    full_dist = np.linalg.norm(all_pts[:, None, :] - all_pts[None, :, :], axis=-1)
    ref_idx = np.arange(n, dtype=int)
    perm_vals = np.zeros((n_seeds, n_probs, N_PERM + 1), dtype=float)

    for si, seed in enumerate(SEEDS):
        # Group probabilities within this seed by valid query count m
        by_m = collections.defaultdict(list)
        for pi in range(n_probs):
            m = int(counts[si, pi])
            if m > 0:
                q_idx = n + chosen[si, pi, keep[si, pi]]
                by_m[m].append((pi, np.concatenate([ref_idx, q_idx])))
        for m, items in by_m.items():
            key = (label, seed, cell, n, m)
            if key not in ww_cache:
                rng = np.random.default_rng(seed_for('tsc-round4-perm', label, seed, cell, n, m))
                mask = permutation_weights(n, m, N_PERM, rng)
                w = mask / n - (1.0 - mask) / m  # (1000, n+m)
                ww_cache[key] = (w[:, :, None] * w[:, None, :]).reshape(N_PERM + 1, (n + m) * (n + m))
            ww = ww_cache[key]
            pis = [it[0] for it in items]
            idx_mat = np.stack([it[1] for it in items], axis=0)  # (T, n+m)
            sub_d = full_dist[idx_mat[:, :, None], idx_mat[:, None, :]].reshape(len(items), -1)
            vals = np.maximum(-(sub_d @ ww.T) * (n * m / (n + m)), 0.0)
            perm_vals[si, pis, :] = vals

    return vreg_score, perm_vals, counts > 0, fallback_n


def run_routing_suite(data: dict, out: Path) -> dict:
    """Evaluate frozen tau_mid AND 999-permutation test on same-gateway and cross-gateway mixtures."""
    fm = family_map()
    prior_routing = json.loads((ROOT / 'results/service_audit/routing.json').read_text())
    prior_lookup = {
        (r['protocol'], r['subgroup'], r['p_honest']): r for r in prior_routing['results']
    }

    # Build S1 cross-gateway pools (CF0 -> OR21 and CF21 -> OR21, 20 cells, 3 ref vs 3 query out of 6)
    cf0_g, cf21_g, or21_g = make_s1(data)
    b_ref20, b_q20, b_cells20 = protocol_groups(data['B'], 20, 3)
    _, b_mat20 = clean_matrix_vreg(b_ref20, b_q20, b_cells20, 3)
    tau_b20 = float((np.diag(b_mat20).max() + b_mat20[~np.eye(len(b_mat20), dtype=bool)].min()) / 2.0)

    def build_s1_plan(ref_group: dict):
        ids = sorted(set(ref_group) & set(or21_g))
        cells = sorted(b_cells20)
        ref = {t: {c: sorted(ref_group[t][c], key=lambda r: r['rep'])[:3] for c in cells} for t in ids}
        qry = {t: {c: sorted(or21_g[t][c], key=lambda r: r['rep']) for c in cells} for t in ids}
        return ref, qry, cells, tau_b20

    plans = []
    for label, source, k, nr, nq in [
        ('B20_q3', 'B', 20, 3, 3),
        ('B40_q7', 'B', 40, 8, 7),
        ('S3_10_q3', 'S3_color', 10, 3, 3),
        ('S3_10_q7', 'S3_color', 10, 8, 7),
    ]:
        br, bq, bc = protocol_groups(data['B'], k, nr)
        _, bm = clean_matrix_vreg(br, bq, bc, nq)
        tau = float((np.diag(bm).max() + bm[~np.eye(len(bm), dtype=bool)].min()) / 2.0)
        ref, qry, cells = protocol_groups(data[source], k, nr)
        plans.append((label, source, k, nr, nq, ref, qry, cells, tau, True))

    s1_cf0_ref, s1_or_qry, s1_cells, tau_s1 = build_s1_plan(cf0_g)
    s1_cf21_ref, _, _, _ = build_s1_plan(cf21_g)
    plans.append(('S1_CF0_OR21_20_q3', 'S1_CF0_to_OR21', 20, 3, 3, s1_cf0_ref, s1_or_qry, s1_cells, tau_s1, False))
    plans.append(('S1_CF21_OR21_20_q3', 'S1_CF21_to_OR21', 20, 3, 3, s1_cf21_ref, s1_or_qry, s1_cells, tau_s1, False))

    aggregate_rows = []
    seed_rows = []

    for label, source, k, nr, nq, ref, query, cells, tau, check_prior in plans:
        t0 = time.perf_counter()
        ids = sorted(ref)
        ww_cache: dict = {}
        orders = {
            (t, c): np.array([
                np.random.default_rng(seed_for('tsc-query-order', label, seed, t, c)).permutation(len(query[t][c]))[:nq]
                for seed in SEEDS
            ])
            for t in ids
            for c in cells
        }
        vreg_records, pval_records, family_flags, fall_counts, pair_refs = [], [], [], [], []
        clean_vreg_per_ref = {}
        clean_pval_per_ref = {}

        for t in ids:
            for u in ids:
                if t == u:
                    continue
                v_sums = np.zeros((len(SEEDS), len(PROBS)))
                p_sums = np.zeros((len(SEEDS), len(PROBS), N_PERM + 1))
                counts = np.zeros((len(SEEDS), len(PROBS)))
                fallback = np.zeros((len(SEEDS), len(PROBS)))
                for c in cells:
                    uniforms = np.array([
                        np.random.default_rng(seed_for('tsc-routing', label, seed, t, u, c)).random(nq)
                        for seed in SEEDS
                    ])
                    v_sc, p_vals, ok, nf = eval_mixed_cell_vreg_and_perm(
                        ref[t][c], query[t][c], query[u][c],
                        orders[t, c], orders[u, c], uniforms,
                        ww_cache, label, c,
                    )
                    v_sums += v_sc * ok
                    p_sums += p_vals * ok[:, :, None]
                    counts += ok
                    fallback += nf
                v_scores = v_sums / counts
                p_totals = p_sums / counts[:, :, None]
                p_values = permutation_p(p_totals)

                if t in clean_vreg_per_ref:
                    np.testing.assert_allclose(clean_vreg_per_ref[t], v_scores[:, -1], atol=1e-14)
                    np.testing.assert_allclose(clean_pval_per_ref[t], p_values[:, -1], atol=1e-14)
                clean_vreg_per_ref[t] = v_scores[:, -1]
                clean_pval_per_ref[t] = p_values[:, -1]

                vreg_records.append(v_scores)
                pval_records.append(p_values)
                pair_refs.append(t)
                family_flags.append(fm[t]['family'] == fm[u]['family'])
                fall_counts.append(fallback / (k * nq))

        v_stack = np.stack(vreg_records)  # (Pairs, Seeds, Probs)
        p_stack = np.stack(pval_records)  # (Pairs, Seeds, Probs)
        fc_stack = np.stack(fall_counts)

        for subgroup, mask in [
            ('all_distinct_labels', np.ones(len(v_stack), dtype=bool)),
            ('same_family', np.array(family_flags, dtype=bool)),
        ]:
            if not np.any(mask):
                continue
            eligible_refs = sorted({t for t, sel in zip(pair_refs, mask) if sel})
            clean_v_group = np.stack([clean_vreg_per_ref[t] for t in eligible_refs]) > tau
            clean_p_group = np.stack([clean_pval_per_ref[t] for t in eligible_refs]) <= ALPHA

            for pi, p in enumerate(PROBS):
                tau_seed_rates = (v_stack[mask, :, pi] > tau).mean(axis=0)
                perm_seed_rates = (p_stack[mask, :, pi] <= ALPHA).mean(axis=0)

                if check_prior:
                    ref_row = prior_lookup[(label, subgroup, p)]
                    assert abs(float(tau_seed_rates.mean()) - ref_row['rejection_mean']) < 1e-12, (
                        label, subgroup, p, tau_seed_rates.mean(), ref_row['rejection_mean']
                    )

                agg = {
                    'protocol': label,
                    'source': source,
                    'subgroup': subgroup,
                    'K': k,
                    'n_reference_per_cell': nr,
                    'n_query_per_cell': nq,
                    'reference_calls': k * nr,
                    'query_calls': k * nq,
                    'p_honest': p,
                    'lambda_fallback': round(1.0 - p, 4),
                    'tau_mid': tau,
                    'perm_alpha': ALPHA,
                    'n_permutations': N_PERM,
                    'n_seeds': len(SEEDS),
                    'n_distinct_directed_pairs': int(mask.sum()),
                    'n_reference_labels': len(eligible_refs),
                    'tau_rejection_mean': float(tau_seed_rates.mean()),
                    'tau_rejection_seed_p05': float(np.quantile(tau_seed_rates, 0.05)),
                    'tau_rejection_seed_p95': float(np.quantile(tau_seed_rates, 0.95)),
                    'tau_genuine_frr_mean': float(clean_v_group.mean()),
                    'perm_rejection_mean': float(perm_seed_rates.mean()),
                    'perm_rejection_seed_p05': float(np.quantile(perm_seed_rates, 0.05)),
                    'perm_rejection_seed_p95': float(np.quantile(perm_seed_rates, 0.95)),
                    'perm_genuine_frr_mean': float(clean_p_group.mean()),
                    'observed_fallback_fraction_mean': float(fc_stack[mask, :, pi].mean()),
                }
                aggregate_rows.append(agg)
                for si, seed in enumerate(SEEDS):
                    seed_rows.append({
                        'protocol': label,
                        'subgroup': subgroup,
                        'p_honest': p,
                        'seed': seed,
                        'tau_rejection_rate': float(tau_seed_rates[si]),
                        'tau_genuine_frr': float(clean_v_group[:, si].mean()),
                        'perm_rejection_rate': float(perm_seed_rates[si]),
                        'perm_genuine_frr': float(clean_p_group[:, si].mean()),
                    })
        print(f'routing+perm complete {label} in {time.perf_counter() - t0:.2f}s', flush=True)

    result = {
        'protocol': (
            'Exact 20-seed Bernoulli mixed-routing comparison between frozen midpoint thresholds '
            '(tau_mid calibrated on Dataset B) and 999-permutation stratified Szekely-Rizzo conditional '
            'energy testing (alpha=0.05). Same-gateway plans (B20_q3, B40_q7, S3_10_q3, S3_10_q7) match '
            'results/service_audit/routing.json bit-for-bit on tau_mid while adding '
            'exact conditional permutation rejection curves. Cross-gateway plans (S1_CF0_OR21_20_q3, '
            'S1_CF21_OR21_20_q3) quantify the drift-vs-sensitivity trade-off when enrollment and query '
            'traverse distinct gateways.'
        ),
        'seeds': list(SEEDS),
        'probabilities': list(PROBS),
        'results': aggregate_rows,
    }
    save(out / 'routing_permutation.json', result)
    write_csv(out / 'routing_permutation.csv', aggregate_rows)
    write_csv(out / 'routing_permutation_seeds.csv', seed_rows)
    return result


def reconcile_table5_table7(data: dict, out: Path) -> dict:
    """Verify exact cell eligibility causing Table 5 (min_split=1) vs Table 7 (min_split=2) E differences."""
    comp = json.loads((ROOT / 'results/benchmark/comparisons.json').read_text())
    cal = json.loads((ROOT / 'results/benchmark/calibration_results.json').read_text())['operating_points']
    eu_full = json.loads((ROOT / 'results/energy_u/results.json').read_text())
    eu_ops = eu_full['operating_points']

    def sel_cal(prefix: str, variant: str) -> float:
        rows = [
            r['frr'] for r in cal
            if (r['scenario'] == prefix or r['scenario'].startswith(prefix + '_seed'))
            and r['calibration'] == 'B3v3'
            and r['metric'] == 'energy_reg'
            and r['variant'] == variant
            and r['threshold_kind'] == 'tau_mid'
        ]
        return float(np.mean(rows))

    def sel_eu(prefix: str, metric: str) -> float:
        rows = [
            r['frr'] for r in eu_ops
            if (r['scenario'] == prefix or r['scenario'].startswith(prefix + '_seed'))
            and r['calibration'] == 'B3v3'
            and r['metric'] == metric
            and r['threshold_kind'] == 'tau_mid'
        ]
        return float(np.mean(rows))

    e_ref_1, e_qry_1 = within(data['E'], 1)
    dropped_details = []
    for tid in sorted(e_ref_1):
        for ck in sorted(e_ref_1[tid]):
            nr = sum(r['parsed']['status'] == 'valid' for r in e_ref_1[tid][ck])
            nq = sum(r['parsed']['status'] == 'valid' for r in e_qry_1[tid][ck])
            if min(nr, nq) < 2:
                dropped_details.append({
                    'target_id': tid,
                    'cell': ck,
                    'n_valid_ref': nr,
                    'n_valid_query': nq,
                })

    result = {
        'explanation': (
            'Table 5 evaluates V-statistic metrics over all shared cells with n_k >= 1 and m_k >= 1 '
            '(20/20 cells for all 10 Dataset E endpoints). Table 7 compares V and U estimators on the '
            'identical U-eligible cell subset requiring n_k >= 2 and m_k >= 2 (because unbiased U divides '
            'by n_k - 1 and m_k - 1), which excludes cells with a single valid response and leaves 19-20 '
            'cells on Dataset E.'
        ),
        'dataset_E_cells_with_min_lt_2': dropped_details,
        'table5_min_split_1': {
            'shared_valid_cells_min_max': comp['E']['shared_valid_cells_min_max'],
            'raw_V_clean_frr': sel_cal('E_clean', 'raw'),
            'centered_V_clean_frr': sel_cal('E_clean', 'self_Bcv'),
            'raw_V_jitter_frr': sel_cal('E_jitter8', 'raw'),
            'centered_V_jitter_frr': sel_cal('E_jitter8', 'self_Bcv'),
        },
        'table7_min_split_2': {
            'raw_V_clean_frr': sel_eu('E_clean', 'v_reg'),
            'centered_V_clean_frr': sel_eu('E_clean', 'v_reg_self'),
            'raw_V_jitter_frr': sel_eu('E_jitter8', 'v_reg'),
            'centered_V_jitter_frr': sel_eu('E_jitter8', 'v_reg_self'),
        },
    }
    save(out / 'table5_vs_table7_cells.json', result)
    return result


def write_summary_report(out: Path, proto: dict, routing: dict, t57: dict) -> None:
    lines = [
        '# Offline Protocol, Sub-Provider, and Permutation-Routing Summary',
        '',
        'All computations are strictly read-only on raw logs and prior frozen artifacts.',
        '',
        '## 1. S1 Cross-Gateway Subgroup Stratification (9 Standard vs. 5 Reasoning-Override Models)',
        '',
        '| Scenario | Group | Models | Perm Reject (p<=0.05) | Energy EER | Energy FRR/FAR (B tau) | Hybrid EER |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for sc in ('CF0_CF21', 'CF21_OR21', 'CF0_OR21'):
        for gkey, glabel in [
            ('all_14', 'All 14'),
            ('standard_9_no_reasoning_override', '9 Standard (no reasoning override)'),
            ('reasoning_5_effort_low_override', '5 Reasoning (OR effort=low)'),
        ]:
            g = proto['s1_stratified'][sc][gkey]
            lines.append(
                f"| {sc} | {glabel} | {g['n_models']} | "
                f"{g['perm_same_model_rejections']}/{g['n_models']} ({g['perm_same_model_rejection_rate']:.2%}) | "
                f"{g['energy_reg_eer']:.2%} | {g['energy_reg_frr_at_B_tau']:.2%} / {g['energy_reg_far_at_B_tau']:.2%} | "
                f"{g['hybrid_eer']:.2%} |"
            )

    lines += [
        '',
        '## 2. Mixed-Routing Detection: Frozen Midpoint (tau_mid) vs. 999-Permutation Test (alpha=0.05)',
        '',
        '| Protocol | Subgroup | Query Calls | tau_mid @ p=0.8 (20% fallback) | tau_mid Clean FRR (p=1) | Perm @ p=0.8 (20% fallback) | Perm Clean FRR (p=1) |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for r in routing['results']:
        if r['p_honest'] == 0.8:
            lines.append(
                f"| {r['protocol']} | {r['subgroup']} | {r['query_calls']} | "
                f"{r['tau_rejection_mean']:.2%} ({r['tau_rejection_seed_p05']:.2%}–{r['tau_rejection_seed_p95']:.2%}) | "
                f"{r['tau_genuine_frr_mean']:.2%} | "
                f"{r['perm_rejection_mean']:.2%} ({r['perm_rejection_seed_p05']:.2%}–{r['perm_rejection_seed_p95']:.2%}) | "
                f"{r['perm_genuine_frr_mean']:.2%} |"
            )

    s3c = proto['s3_provider_and_cost_audit']
    q_g = s3c['scenario_G_query_usd_quantiles']
    lines += [
        '',
        '## 3. S3 Provider Mixing & Reasoning-Token Cost Tail',
        '',
        f"- Multi-provider targets in S3 color: {s3c['multi_provider_count']}/20 "
        f"(odd vs. even provider-share TV distance mean={s3c['multi_provider_mean_tv_odd_vs_even']:.4f}, "
        f"max={s3c['multi_provider_max_tv_odd_vs_even']:.4f}).",
        f"- Scenario G per-audit query USD across 20 S3 targets: min=${q_g['min']:.4f}, "
        f"median=${q_g['median']:.4f}, p90=${q_g['p90']:.4f}, "
        f"max(19/20)=${q_g['max_19_of_20_excluding_deepseek_v32']:.4f}, "
        f"max(all 20, s3-deepseek-v3.2)=${q_g['max_all_20']:.4f}.",
        '',
        '## 4. Table 5 vs. Table 7 Valid-Cell Rule on Dataset E',
        '',
        f"- Cells excluded in Table 7 due to min(n_ref, n_query) < 2: {len(t57['dataset_E_cells_with_min_lt_2'])} "
        f"({t57['dataset_E_cells_with_min_lt_2']}).",
    ]
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=OUT)
    args = ap.parse_args()
    out = args.output.resolve()
    if out == ROOT:
        ap.error('Output directory must be a subdirectory')
    out.mkdir(parents=True, exist_ok=True)

    manifest_path = ROOT / 'results/integrity_manifest.json'
    raw_manifest = json.loads(manifest_path.read_text())
    protected_expected = raw_manifest['files'] if isinstance(raw_manifest, dict) and 'files' in raw_manifest else raw_manifest
    before = {rel: sha(ROOT / rel) for rel in protected_expected}
    assert before == protected_expected, 'Protected files differed BEFORE execution!'

    sys.addaudithook(guard)
    data = {name: load(path) for name, path in FILES.items()}
    proto = audit_protocols_and_providers(data, out)
    routing = run_routing_suite(data, out)
    t57 = reconcile_table5_table7(data, out)
    write_summary_report(out, proto, routing, t57)

    after = {rel: sha(ROOT / rel) for rel in protected_expected}
    assert after == protected_expected, 'Protected files changed AFTER execution!'

    save(out / 'manifest.json', {
        'protocol': 'protocol_routing_offline_v1',
        'protected_file_count': len(protected_expected),
        'all_protected_unchanged': True,
        'live_api_calls': 0,
        'seeds': list(SEEDS),
        'n_permutations': N_PERM,
        'alpha': ALPHA,
        'output_sha256': {
            p.name: sha(p)
            for p in sorted(out.iterdir())
            if p.is_file() and p.name != 'manifest.json'
        },
    })
    shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print('completed', str(shown), flush=True)


if __name__ == '__main__':
    main()
