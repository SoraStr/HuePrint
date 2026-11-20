#!/usr/bin/env python3
"""Offline V/U energy sensitivity analysis; never calls a model or changes logs.

Run: UV_OFFLINE=1 uv run --offline --no-project --with numpy python -B scripts/energy_u_analysis.py
The U numerator is unbiased under independent IID sampling, but may be negative.
Neither its regularized ratio nor its clipped variant is an unbiased estimator.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import analyze as an
from hueprint_audit.core import (JITTER_SEEDS, SEED, group, jitter_group, load,
                                 operating, save, seed_for, stats, summarize,
                                 thresholds)
from hueprint_audit.experiments import FILES, b20, make_s1, within

DELTA = 15.0
METRICS = ('v_e2', 'v_norm', 'v_reg', 'v_reg_self', 'u_e2',
           'u_reg_signed', 'u_reg_clipped')


def offline_guard(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.getaddrinfo',
                 'socket.sendto', 'subprocess.Popen'):
        raise RuntimeError('This analysis is offline: ' + event)


def cell_energy(x, y):
    """V numerator and signed U numerator from the same valid RGB100 samples."""
    n, m = len(x), len(y)
    if n < 2 or m < 2:
        raise ValueError('U requires at least two valid observations per side')
    xy = float(np.linalg.norm(x[:, None] - y[None, :], axis=-1).mean())
    xx = float(np.linalg.norm(x[:, None] - x[None, :], axis=-1).mean())
    yy = float(np.linalg.norm(y[:, None] - y[None, :], axis=-1).mean())
    v = max(0.0, 2 * xy - xx - yy)
    u = 2 * xy - xx * n / (n - 1) - yy * m / (m - 1)
    return {'v_e2': v, 'v_norm': v / (2 * xy) if xy >= 1e-12 else 0.,
            'v_reg': v / (2 * xy + 2 * DELTA), 'u_e2': u,
            'u_reg_signed': u / (2 * xy + 2 * DELTA),
            'u_reg_clipped': max(0., u) / (2 * xy + 2 * DELTA)}


def v_bootstrap_mu(ref, planned_query_n, repeats=256):
    """Existing enrollment-only seed contract, evaluating just regularized V."""
    result = {}
    for tid, cells in sorted(ref.items()):
        result[tid] = {}
        for ck, rows in sorted(cells.items()):
            valid = [r for r in rows if r['parsed']['status'] == 'valid']
            if len(valid) < 2:
                continue
            x = an.summarize_cell_samples(valid)['rgb_arr']
            n = len(x)
            signature = [(r['trial_key'], r['parsed'], r.get('usage')) for r in valid]
            rng = np.random.default_rng(seed_for('enrollment-bootstrap', SEED,
                                               signature, planned_query_n))
            values = []
            for _ in range(repeats):
                # Sorting matches the existing bootstrap's cached sample order.
                ix = sorted(rng.integers(n, size=n))
                iy = sorted(rng.integers(n, size=planned_query_n))
                values.append(cell_energy(x[ix], x[iy])['v_reg'])
            result[tid][ck] = float(np.mean(values))
    return result


def matrices(ref, query, mu):
    aa, bb = summarize(ref), summarize(query)
    ids = sorted(set(aa) & set(bb))
    mats = {m: np.zeros((len(ids), len(ids))) for m in METRICS}
    counts = np.zeros((len(ids), len(ids)), dtype=int)
    dropped = np.zeros_like(counts)
    cell_rows = []
    for i, tid in enumerate(ids):
        for j, uid in enumerate(ids):
            values = []
            for ck in sorted(set(aa[tid]) & set(bb[uid])):
                x, y = aa[tid][ck]['rgb_arr'], bb[uid][ck]['rgb_arr']
                if min(len(x), len(y)) < 2:
                    dropped[i, j] += 1
                    continue
                v = cell_energy(x, y)
                v['v_reg_self'] = v['v_reg'] - mu[tid][ck]
                values.append(v)
                cell_rows.append({'reference': tid, 'query': uid, 'cell': ck,
                                  'n_reference': len(x), 'n_query': len(y), **v})
            if not values:
                raise ValueError(f'No eligible cells: {tid}, {uid}')
            counts[i, j] = len(values)
            for metric in METRICS:
                mats[metric][i, j] = sum(v[metric] for v in values) / len(values)
    return ids, mats, counts, dropped, cell_rows


def checks():
    # Exact enumeration of IID Bernoulli samples checks unbiasedness and V bias.
    vals = []
    for bits in itertools.product((0., 1.), repeat=5):
        x = np.array([[b, 0., 0.] for b in bits[:2]])
        y = np.array([[b, 0., 0.] for b in bits[2:]])
        vals.append(cell_energy(x, y))
    assert abs(np.mean([v['u_e2'] for v in vals])) < 1e-14
    assert abs(np.mean([v['v_e2'] for v in vals]) - (1/2 + 1/3)*.5) < 1e-14
    assert min(v['u_e2'] for v in vals) < 0
    assert np.mean([v['u_reg_clipped'] for v in vals]) > 0
    ratio_bias = float(np.mean([v['u_reg_signed'] for v in vals]))
    rng = np.random.default_rng(20261113)
    maximum = 0.
    for _ in range(100):
        x, y = rng.uniform(0, 100, (3, 3)), rng.uniform(0, 100, (6, 3))
        v = cell_energy(x, y)
        raw, norm, reg = an.energy_distance_3d(x, y)
        maximum = max(maximum, abs(v['v_e2']-raw**2), abs(v['v_norm']-norm),
                      abs(v['v_reg']-reg))
        assert v['u_e2'] <= v['v_e2'] + 1e-12
    assert maximum < 1e-10
    try:
        cell_energy(np.zeros((1, 3)), np.zeros((2, 3)))
    except ValueError:
        pass
    else:
        raise AssertionError('n=1 must be rejected')
    return {'exact_bernoulli_enumeration': '32 equiprobable n=2,m=3 samples',
            'mean_u_e2': float(np.mean([v['u_e2'] for v in vals])),
            'mean_v_e2': float(np.mean([v['v_e2'] for v in vals])),
            'null_signed_ratio_mean': ratio_bias,
            'canonical_v_max_error_100_random_pairs': maximum,
            'negative_u_observed': True, 'singleton_rejection': True}


def csv_write(path, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def benchmark_cross_checks():
    comparisons = json.loads((ROOT/'results/benchmark/comparisons.json').read_text())
    cal = json.loads((ROOT/'results/benchmark/calibration_results.json').read_text())
    return {
        'table_II': {key: comparisons['A_fresh'][key]['hybrid']
                     for key in ('cross_sublineage', 'cross_family')},
        'table_IX': [r for r in cal['operating_points']
                     if r['scenario'] in ('Bfull_shift8', 'Bfull_shift-8', 'Bfull_quant32')
                     and r['metric'] == 'energy_reg' and r['threshold_kind'] == 'tau_mid'
                     and r['variant'] in ('raw', 'self_alpha1')],
        'sources': ['results/benchmark/comparisons.json', 'results/benchmark/calibration_results.json']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT/'results/energy_u')
    args = p.parse_args()
    out = args.output.resolve()
    if out == ROOT:
        p.error('Output must be a subdirectory')
    out.mkdir(parents=True, exist_ok=True)
    if (out/'results.json').exists():
        p.error('Refusing to overwrite completed results; choose a fresh --output directory')
    sys.addaudithook(offline_guard)
    keys = ('B', 'E', 'S1_CF21', 'S1_OR21')
    sources = [ROOT/FILES[k] for k in keys] + [
        ROOT/'results/benchmark/calibration_results.json',
        ROOT/'results/benchmark/frozen_calibration.json',
        ROOT/'results/benchmark/comparisons.json', ROOT/'analyze.py',
        ROOT/'scripts/hueprint_audit/core.py',
        ROOT/'scripts/hueprint_audit/experiments.py']
    hashes = {str(s.relative_to(ROOT)): hashlib.sha256(s.read_bytes()).hexdigest() for s in sources}
    data = {key: load(ROOT/FILES[key]) for key in keys}
    result = {'protocol': 'energy_u_offline_v1', 'delta_rgb100': DELTA,
              'validity_rule': 'At least two parsed-valid observations on each side; identical cells for V and U.',
              'aggregation': 'Mean of per-cell scores, including per-cell clipping for u_reg_clipped.',
              'tuning': 'No test-based tuning. Delta=15 and self coefficient=1 retained. Thresholds fitted on B only.',
              'jitter_seeds': list(JITTER_SEEDS), 'checks': checks(), 'scenarios': {}}
    devs = {'B3v3': within(b20(data['B'])),
            'B6v6': (group([r for r in data['B'] if r['lang'] in ('en', 'zh') and r['rep'] <= 6]),
                     group([r for r in data['B'] if r['lang'] in ('en', 'zh') and 7 <= r['rep'] <= 12]))}
    fit = {}
    rows = []
    pairs = []
    mu_cache = {}

    def evaluate(name, ref, query, planned_n, fit_names):
        key = (id(ref), planned_n)
        if key not in mu_cache:
            mu_cache[key] = v_bootstrap_mu(ref, planned_n)
        ids, mats, count, dropped, cells = matrices(ref, query, mu_cache[key])
        entry = {'ids': ids, 'matrices': {m: x.tolist() for m, x in mats.items()},
                 'shared_cells': count.tolist(), 'excluded_cells': dropped.tolist(),
                 'shared_cells_min_max': [int(count.min()), int(count.max())],
                 'excluded_cell_pair_total': int(dropped.sum()),
                 'negative_u_cell_fraction': float(np.mean([r['u_e2'] < 0 for r in cells])),
                 'negative_u_pair_fraction': float(np.mean(mats['u_e2'] < 0)), 'metrics': {}}
        for metric, mat in mats.items():
            entry['metrics'][metric] = stats(mat)
            for fit_name in fit_names:
                for kind, tau in fit[fit_name][metric].items():
                    rows.append({'scenario': name, 'calibration': fit_name, 'metric': metric,
                                 'threshold_kind': kind, 'threshold': tau,
                                 **stats(mat), **operating(mat, tau)})
        for i, tid in enumerate(ids):
            for j, uid in enumerate(ids):
                pairs.append({'scenario': name, 'reference': tid, 'query': uid,
                              'genuine': i == j, 'valid_cells': int(count[i, j]),
                              **{m: float(mat[i, j]) for m, mat in mats.items()}})
        result['scenarios'][name] = entry
        print(name, 'eligible cells', entry['shared_cells_min_max'], flush=True)
        return mats

    # Freeze both B calibration protocols before reading any test statistic.
    for name, (ref, query) in devs.items():
        mats = evaluate(name+'_development', ref, query, 3 if name == 'B3v3' else 6, [])
        fit[name] = {metric: thresholds(mat) for metric, mat in mats.items()}
    save(out/'frozen_thresholds.json', fit)
    er, eq = within(data['E'])
    evaluate('E_clean', er, eq, 3, ['B3v3'])
    for seed in JITTER_SEEDS:
        evaluate(f'E_jitter8_seed{seed}', er, jitter_group(eq, 8, seed), 3, ['B3v3'])
    cf0, cf21, or21 = make_s1(data)
    for label, ref, query in [('CF0_CF21', cf0, cf21), ('CF21_OR21', cf21, or21), ('CF0_OR21', cf0, or21)]:
        evaluate('S1_'+label, ref, query, 6, ['B3v3', 'B6v6'])
    legacy = json.loads((ROOT/'results/benchmark/calibration_results.json').read_text())
    result['legacy_min1_frozen_baselines'] = [r for r in legacy['operating_points']
        if (r['scenario'] in result['scenarios']) and r['metric'] == 'energy_reg'
        and r['variant'] in ('raw', 'self_alpha1') and r['threshold_kind'] == 'tau_mid']
    result['frozen_thresholds'] = fit
    result['operating_points'] = rows
    result['four_zero_failures'] = {'confidence': .95, 'n': 4, 'failures': 0,
        'one_sided_exact_failure_upper': 1 - .05**.25,
        'assumption': 'Four independent Bernoulli trials sharing one failure probability. Not an EER confidence interval; model pairs and repeated paths are dependent.'}
    result['benchmark_cross_checks'] = benchmark_cross_checks()
    # Reproduce historical V numbers when the matched rule leaves all cells intact.
    errors = []
    for legacy_row in result['legacy_min1_frozen_baselines']:
        entry = result['scenarios'][legacy_row['scenario']]
        development = result['scenarios'][legacy_row['calibration']+'_development']
        if entry['excluded_cell_pair_total'] or development['excluded_cell_pair_total']:
            continue
        metric = 'v_reg' if legacy_row['variant'] == 'raw' else 'v_reg_self'
        candidates = [r for r in rows if r['scenario'] == legacy_row['scenario']
                      and r['calibration'] == legacy_row['calibration']
                      and r['metric'] == metric and r['threshold_kind'] == 'tau_mid']
        if not candidates:  # Development matrices are fitted, not held-out tests.
            continue
        candidate = candidates[0]
        errors.extend(abs(candidate[k]-legacy_row[k]) for k in ('eer', 'auc', 'frr', 'far'))
    result['checks']['legacy_matches_when_no_cells_excluded'] = len(errors)//4
    result['checks']['legacy_max_error'] = max(errors, default=0.)
    assert max(errors, default=0.) < 1e-10
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == h for path, h in hashes.items())
    result['integrity'] = {'protected_input_sha256': hashes, 'inputs_unchanged': True,
                           'live_api_calls': 0, 'network_guard': True,
                           'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           'numpy_version': np.__version__, 'python_version': sys.version}
    save(out/'results.json', result)
    csv_write(out/'operating_points.csv', rows)
    csv_write(out/'pair_scores.csv', pairs)
    save(out/'benchmark_cross_checks.json', result['benchmark_cross_checks'])
    write_report(out, result)


def write_report(out, result):
    lines = ['# Signed U-statistic energy: offline sensitivity analysis', '',
        'Only existing parsed cloud responses are used. No model calls or test-based parameter selection.', '',
        'For independent IID samples from P and Q, let a = E||X-X′|| and b = E||Y-Y′||. The V numerator has expectation E²(P,Q) + a/n + b/m. Under P=Q, this becomes (1/n+1/m)a. Replacing within-sample denominators n²,m² by n(n−1),m(m−1) gives an unbiased signed numerator for E²(P,Q). It can be negative.', '',
        'The signed regularized score divides that numerator by the random positive denominator 2dXY+30. Neither random-denominator normalization nor positive-part clipping preserves exact unbiasedness, so signed and clipped U ratios are reported side by side. No square root is applied to signed U. Main-manuscript Proposition 2 (Supplement G) establishes unified one-sided (2*eps/delta0) and two-sided (4*eps/delta0) Lipschitz bounds for both V and U regularized energy ratios on the cone 0 <= h <= 2d.', '',
        'All new V/U comparisons use the same cells with at least two valid observations per side. Legacy V results allowing one valid observation are retained in results.json, rather than silently mixing validity rules. Enrollment self-centering uses 256 independent bootstrap draws per cell and alpha=1. All thresholds are fitted on B. B3v3 is primary; B6v6 is the budget-matched S1 sensitivity analysis.', '',
        '| Scenario | Calibration | Score | EER | FRR | FAR | Threshold |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    rows = result['operating_points']
    for scenario in ('E_clean', 'E_jitter8', 'S1_CF0_CF21', 'S1_CF21_OR21', 'S1_CF0_OR21'):
        for calibration in (('B3v3', 'B6v6') if scenario.startswith('S1') else ('B3v3',)):
            for metric in METRICS:
                selected = [r for r in rows if (r['scenario'] == scenario or r['scenario'].startswith(scenario+'_seed'))
                            and r['calibration'] == calibration and r['metric'] == metric and r['threshold_kind'] == 'tau_mid']
                means = {k: float(np.mean([r[k] for r in selected])) for k in ('eer', 'frr', 'far', 'threshold')}
                lines.append(f"| {scenario} | {calibration} | {metric} | {100*means['eer']:.2f}% | {100*means['frr']:.2f}% | {100*means['far']:.2f}% | {means['threshold']:.8f} |")
    lines += ['', 'Jitter rows average ten fixed seeds on the same response pool to evaluate coordinate perturbation sensitivity.', '',
        'Benchmark cross-checks are copied from frozen results/benchmark JSON with their original protocol and thresholds, while Table S9 evaluates V and U estimators over identical n_c, m_c >= 2 cells. Under regularized energy, all three B-full directional-shift/quantization rows retain 0.00% re-swept EER and 0.00% frozen FAR while crossing clean frozen cutoffs (100.00% flagging rate).', '',
        'Implementation checks enumerate 32 IID Bernoulli sample outcomes to verify the null expectations, exhibit negative U values and clipping bias, reject n=1, and compare V against the canonical implementation on 100 random pairs. Protected source/log hashes are checked before and after the run.', '']
    (out/'REPORT.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
