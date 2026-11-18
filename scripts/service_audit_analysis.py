#!/usr/bin/env python3
"""Offline service-audit analyses. Never mutates source logs or prior results.

UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy \
  python -B scripts/service_audit_analysis.py
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import heapq
import json
import os
import platform
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np
import analyze as an
from hueprint_audit.core import group, load, save, seed_for, energy_permutations, permutation_p
from hueprint_audit.experiments import FILES

OUT = ROOT / 'results/service_audit'
SEEDS = tuple(range(2026111300, 2026111320))
PROBS = (0., .2, .4, .5, .6, .8, 1.)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def guard(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto', 'subprocess.Popen'):
        raise RuntimeError('Offline-only analysis: ' + event)


def write_csv(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def roc(genuine, other):
    r = an.compute_roc_eer(list(genuine), list(other))
    return {'auc': r['auc_raw'], 'eer': r['eer_linear_raw'], 'eer_discrete': r['eer_raw']}


def frozen_threshold(mat):
    mat = np.asarray(mat)
    g, other = np.diag(mat), mat[~np.eye(len(mat), dtype=bool)]
    return float((g.max() + other.min()) / 2)


def family_map():
    fm = json.loads((ROOT / 'config/family_map.json').read_text())['families']
    cfg = json.loads((ROOT / 'extensions/live_validation_20261111/configs/targets.s3_20models_locked64.json').read_text())['targets']
    for target in cfg:
        fm[target['id']] = {'family': target['family'], 'vendor': target['model'].split('/')[0]}
    return fm


def family_analysis(out):
    d = json.loads((ROOT / 'results/benchmark/comparisons.json').read_text())
    fm = family_map()
    rows, pairs = [], []
    metrics = ('hex_jsd', 'voxel_jsd', 'energy_reg', 'hybrid')
    for scenario, fit in [('A_fresh', 'B20x6'), ('B20x6', 'B20x6'),
                          ('B_full', 'B_full'), ('E', 'B20x6'), ('S3_color_within', 'B_full')]:
        ids = d[scenario]['ids']
        eye = np.eye(len(ids), dtype=bool)
        for field in ('family', 'vendor', 'sublineage'):
            if any(field not in fm[t] for t in ids):
                continue
            same = np.array([[fm[t][field] == fm[u][field] for u in ids] for t in ids]) & ~eye
            if not same.any():
                continue
            for metric in metrics:
                m = np.asarray(d[scenario]['matrices'][metric])
                tau = frozen_threshold(d[fit]['matrices'][metric])
                gen, neg = m[eye], m[same]
                rows.append({'scenario': scenario, 'negative_group': 'same_' + field,
                             'metric': metric, 'n_genuine': len(gen), 'n_directed_negative': len(neg),
                             **roc(gen, neg), 'threshold_source': fit, 'threshold': tau,
                             'frr': float(np.mean(gen > tau)), 'far': float(np.mean(neg <= tau)),
                             'false_rejects': int(np.sum(gen > tau)), 'false_accepts': int(np.sum(neg <= tau)),
                             'is_development_resubstitution': scenario.startswith('B'),
                             'shares_raw_records_with_B': scenario.startswith('B') or scenario == 'A_fresh'})
        for i, t in enumerate(ids):
            for j, u in enumerate(ids):
                if i != j:
                    pairs.append({'scenario': scenario, 'reference': t, 'query': u,
                                  'same_family': fm[t]['family'] == fm[u]['family'],
                                  'same_vendor': fm[t]['vendor'] == fm[u]['vendor'],
                                  'same_sublineage': fm[t].get('sublineage') == fm[u].get('sublineage') if 'sublineage' in fm[t] and 'sublineage' in fm[u] else None,
                                  **{m: d[scenario]['matrices'][m][i][j] for m in metrics}})
    result = {'protocol': 'Existing immutable comparison matrices and versioned family_map labels. S3 uses its saved config family and model namespace as vendor; no sublineage labels invented. '
              'Directed distinct-label negatives; no checkpoint attestation or tier ordering inferred. '
              'All genuine labels remain in each ROC. Thresholds fitted only on B; B rows are '
              'development resubstitution. A/E use B20x6; S3 uses B_full despite sample/prompt '
              'differences, explicitly a threshold-transfer stress test. A and B share 480 original '
              'responses, so A is not an independent calibration holdout.', 'results': rows}
    save(out / 'same_family.json', result)
    write_csv(out / 'same_family.csv', rows)
    write_csv(out / 'same_family_pairs.csv', pairs)
    return result


def arrays(rows):
    return np.array([r['parsed']['rgb'] for r in rows if r['parsed']['status'] == 'valid'], dtype=float).reshape(-1, 3) * (100 / 255)


def energy_score(x, y):
    if len(x) == 0 or len(y) == 0:
        return None
    return an.energy_distance_3d(x, y)[2]


def select_cells(rows, k):
    cells = sorted({f"{r['task_id']}|{r['lang']}" for r in rows})
    if k == 10:
        cells = [c for c in cells if c.endswith('|en')]
    elif k == 20:
        cells = [c for c in cells if c.endswith(('|en', '|zh'))]
    if len(cells) != k:
        raise AssertionError((k, len(cells)))
    return cells


def protocol_groups(rows, k, nref):
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


def clean_matrix(ref, query, cells, nq):
    ids = sorted(ref)
    mat = np.zeros((len(ids), len(ids)))
    for i, t in enumerate(ids):
        for j, u in enumerate(ids):
            values = [energy_score(arrays(ref[t][c]), arrays(query[u][c][:nq])) for c in cells]
            values = [v for v in values if v is not None]
            if not values:
                raise AssertionError('No common valid cells')
            mat[i, j] = sum(values) / len(values)
    return ids, mat


def batch_mixed_scores(ref_rows, genuine_pool, fallback_pool, n, order_g, order_f, uniforms):
    """Return seed x probability regularized V scores, preserving invalid call slots."""
    x = arrays(ref_rows)
    shape = (len(order_g), len(PROBS))
    pool = genuine_pool + fallback_pool
    coords = np.array([r['parsed']['rgb'] if r['parsed']['status'] == 'valid' else [0, 0, 0] for r in pool], dtype=float) * (100 / 255)
    valid = np.array([r['parsed']['status'] == 'valid' for r in pool])
    chosen = np.where(uniforms[:, None, :] < np.array(PROBS)[None, :, None],
                      order_g[:, None, :], order_f[:, None, :] + len(genuine_pool))
    fallback_n = (chosen >= len(genuine_pool)).sum(axis=-1)
    if not len(x):
        return np.zeros(shape), np.zeros(shape, dtype=bool), fallback_n
    keep = valid[chosen]
    count = keep.sum(axis=-1)
    cross = np.linalg.norm(x[:, None] - coords[None, :], axis=-1).mean(axis=0)
    yy = np.linalg.norm(coords[:, None] - coords[None, :], axis=-1)
    aa = np.linalg.norm(x[:, None] - x[None, :], axis=-1).mean()
    ab = np.sum(cross[chosen] * keep, axis=-1) / np.maximum(count, 1)
    bb = (yy[chosen[..., :, None], chosen[..., None, :]] * keep[..., :, None] * keep[..., None, :]).sum(axis=(-1, -2)) / np.maximum(count, 1) ** 2
    score = np.maximum(0, ab - .5 * (aa + bb)) / (ab + an.ENERGY_DELTA0)
    return score, count > 0, fallback_n


def routing_analysis(data, out):
    fm = family_map()
    plans = [('B20_q3', 'B', 20, 3, 3), ('B40_q7', 'B', 40, 8, 7),
             ('S3_10_q3', 'S3_color', 10, 3, 3), ('S3_10_q7', 'S3_color', 10, 8, 7)]
    frozen, records, aggregate, pair_rows = {}, [], [], []
    for label, source, k, nr, nq in plans:
        br, bq, bc = protocol_groups(data['B'], k, nr)
        bids, bm = clean_matrix(br, bq, bc, nq)
        tau = frozen_threshold(bm)
        frozen[label] = {'source': 'Dataset B only; no S3 calibration', 'K': k, 'n_reference': nr,
                         'n_query': nq, 'ids': bids, 'matrix': bm.tolist(), 'tau_mid': tau,
                         'calibration_query': 'first n even repetitions; fixed before mixture evaluation'}
    save(out / 'routing_frozen_thresholds.json', frozen)
    for label, source, k, nr, nq in plans:
        ref, query, cells = protocol_groups(data[source], k, nr)
        ids = sorted(ref)
        tau = frozen[label]['tau_mid']
        score_records, family, fall_counts, pair_references = [], [], [], []
        # Sampling is without replacement within each genuine/fallback pool.
        orders = {(t, c): np.array([np.random.default_rng(seed_for('tsc-query-order', label, seed, t, c)).permutation(len(query[t][c]))[:nq] for seed in SEEDS])
                  for t in ids for c in cells}
        clean_per_ref = {}
        for t in ids:
            for u in ids:
                if t == u:
                    continue
                sums = np.zeros((len(SEEDS), len(PROBS)))
                counts = np.zeros_like(sums)
                fallback = np.zeros_like(sums)
                for c in cells:
                    uniforms = np.array([np.random.default_rng(seed_for('tsc-routing', label, seed, t, u, c)).random(nq) for seed in SEEDS])
                    score, ok, nf = batch_mixed_scores(ref[t][c], query[t][c], query[u][c], nq, orders[t, c], orders[u, c], uniforms)
                    sums += score * ok
                    counts += ok
                    fallback += nf
                if np.any(counts == 0):
                    raise AssertionError('No valid scored cells')
                scores = sums / counts
                if t in clean_per_ref:
                    np.testing.assert_allclose(clean_per_ref[t], scores[:, -1], atol=1e-14)
                clean_per_ref[t] = scores[:, -1]
                score_records.append(scores)
                pair_references.append(t)
                family.append(fm[t]['family'] == fm[u]['family'])
                fall_counts.append(fallback / (k * nq))
                for si, seed in enumerate(SEEDS):
                    for pi, p in enumerate(PROBS):
                        pair_rows.append({'protocol': label, 'seed': seed, 'p_honest': p,
                                          'reference': t, 'fallback': u, 'same_family': family[-1],
                                          'score': float(scores[si, pi]), 'detected': bool(scores[si, pi] > tau),
                                          'observed_fallback_fraction': float(fallback[si, pi] / (k * nq)),
                                          'valid_scored_cells': int(counts[si, pi])})
        stack = np.stack(score_records)
        fc = np.stack(fall_counts)
        clean = np.stack(list(clean_per_ref.values())) > tau
        for subgroup, mask in [('all_distinct_labels', np.ones(len(stack), bool)), ('same_family', np.array(family))]:
            if not np.any(mask):
                continue
            eligible_refs = sorted({t for t, selected in zip(pair_references, mask) if selected})
            clean_group = np.stack([clean_per_ref[t] for t in eligible_refs]) > tau
            for pi, p in enumerate(PROBS):
                seed_rates = (stack[mask, :, pi] > tau).mean(axis=0)
                # Keep pair weighting across the entire curve. Separately report
                # unique-reference clean FRR, excluding references absent from a subgroup.
                agg = {'protocol': label, 'source': source, 'subgroup': subgroup, 'K': k,
                       'n_reference_per_cell': nr, 'n_query_per_cell': nq, 'reference_calls': k * nr,
                       'query_calls': k * nq, 'p_honest': p, 'tau_mid': tau, 'n_seeds': len(SEEDS),
                       'n_distinct_directed_pairs': int(mask.sum()), 'n_reference_labels': len(eligible_refs),
                       'rejection_mean': float(seed_rates.mean()), 'rejection_seed_p05': float(np.quantile(seed_rates, .05)),
                       'rejection_seed_p95': float(np.quantile(seed_rates, .95)),
                       'acceptance_mean': float(1 - seed_rates.mean()),
                       'genuine_frr_mean': float(clean_group.mean()),
                       'observed_fallback_fraction_mean': float(fc[mask, :, pi].mean()),
                       'meaning': 'pair-weighted genuine false rejection' if p == 1 else 'pair-weighted mixture detection'}
                aggregate.append(agg)
                for si, seed in enumerate(SEEDS):
                    records.append({'protocol': label, 'subgroup': subgroup, 'p_honest': p,
                                    'seed': seed, 'rejection_rate': float(seed_rates[si]),
                                    'genuine_frr': float(clean_group[:, si].mean())})
        print('routing complete', label, flush=True)
    result = {'protocol': 'Offline Bernoulli routing simulation using disjoint odd enrollment and even query pools. '
              'Query pool sampling is without replacement for each source; invalid responses consume calls but '
              'geometric scoring uses shared valid cells. No synthetic new API observations. '
              'Twenty fixed seeds share uniform masks across p. Seed 5th/95th percentiles describe finite-pool '
              'simulation variability, not independent-model confidence intervals. B evaluation is development '
              'resubstitution; S3 transfers B thresholds. All pairs are distinct declared labels; same-family '
              'pairs are not asserted to be ordered tier downgrades. Curves remain directed-pair weighted at all p; '
              'the separate genuine_frr column averages unique eligible reference labels, excluding subgroup singletons. '
              'At p=1 repeated reference scores are not independent trials.',
              'seeds': list(SEEDS), 'probabilities': list(PROBS), 'results': aggregate}
    save(out / 'routing.json', result)
    write_csv(out / 'routing.csv', aggregate)
    write_csv(out / 'routing_seeds.csv', records)
    write_csv(out / 'routing_pairs.csv', pair_rows)
    return result


def schedule_estimate(latencies_ms, concurrency):
    lanes = [0.] * concurrency
    for duration in latencies_ms:
        finished = heapq.heappop(lanes)
        heapq.heappush(lanes, finished + duration)
    return max(lanes) / 1000


def overhead_analysis(data, out):
    pricing_path = ROOT / 'results/service_audit/current_pricing_snapshot.json'
    pricing = json.loads(pricing_path.read_text())
    prices = {r['id']: (float(r['pricing']['prompt']), float(r['pricing']['completion'])) for r in pricing['rates']}
    gpt_price = prices['openai/gpt-4o']
    llama_price = prices['meta-llama/llama-3.3-70b-instruct']
    plans = [('B20x6', [r for r in data['B'] if r['lang'] in ('en', 'zh') and r['rep'] <= 6], 'split'),
             ('E20x6', data['E'], 'split'), ('S1_CF21', data['S1_CF21'], 'query'),
             ('S1_OR21', data['S1_OR21'], 'query'), ('S3_color', data['S3_color'], 'split'),
             ('S3_word', data['S3_word'], 'split'), ('S4a', data['S4a'], 'split')]
    rows, coverage = [], []
    for name, source, mode in plans:
        keys = collections.Counter(k for r in source for k in r)
        ukeys = collections.Counter(k for r in source for k in (r.get('usage') or {}))
        coverage.append({'cohort': name, 'records': len(source), 'root_fields': dict(keys), 'usage_fields': dict(ukeys),
                         'direct_cost_records': sum(any('cost' in k.lower() and isinstance(v, (float, int)) for k, v in (r.get('usage') or {}).items()) for r in source)})
        for target in sorted({r['target_id'] for r in source}):
            allrows = [r for r in source if r['target_id'] == target]
            roles = [('enrollment', [r for r in allrows if r['rep'] % 2]), ('query', [r for r in allrows if not r['rep'] % 2])] if mode == 'split' else [('query', allrows)]
            for role, rs in roles:
                ordered = sorted(rs, key=lambda r: (r['task_id'], r['lang'], r['rep']))
                durations = [float(r['latency_ms']) for r in ordered if isinstance(r.get('latency_ms'), (int, float))]
                stamps = [dt.datetime.fromisoformat(r['timestamp_utc']).timestamp() for r in rs]
                ti = sum((r.get('usage') or {}).get('input_tokens') or 0 for r in rs)
                to = sum((r.get('usage') or {}).get('output_tokens') or 0 for r in rs)
                rows.append({'cohort': name, 'target': target, 'role': role, 'calls': len(rs),
                             'input_tokens': ti, 'output_tokens': to,
                             'input_token_observed_calls': sum(isinstance((r.get('usage') or {}).get('input_tokens'), (int, float)) for r in rs),
                             'output_token_observed_calls': sum(isinstance((r.get('usage') or {}).get('output_tokens'), (int, float)) for r in rs),
                             'cached_input_tokens': sum((r.get('usage') or {}).get('cached_tokens') or 0 for r in rs),
                             'latency_records': len(durations), 'call_latency_p50_ms': float(np.median(durations)),
                             'call_latency_p95_ms': float(np.quantile(durations, .95)),
                             'logged_completion_span_seconds': max(stamps) - min(stamps),
                             'estimated_c1_seconds': schedule_estimate(durations, 1),
                             'estimated_c8_seconds': schedule_estimate(durations, 8),
                             'estimated_c16_seconds': schedule_estimate(durations, 16),
                             'scenario_usd_at_input1_output5_per_million': (ti + 5 * to) / 1e6,
                             'catalog_scenario_gpt4o_usd': gpt_price[0] * ti + gpt_price[1] * to,
                             'catalog_scenario_llama33_usd': llama_price[0] * ti + llama_price[1] * to})
    aggregates = []
    for cohort in sorted({r['cohort'] for r in rows}):
        for role in ('enrollment', 'query'):
            rr = [r for r in rows if r['cohort'] == cohort and r['role'] == role]
            if not rr:
                continue
            item = {'cohort': cohort, 'role': role, 'n_targets': len(rr)}
            for key in ('calls', 'input_tokens', 'output_tokens', 'scenario_usd_at_input1_output5_per_million',
                        'catalog_scenario_gpt4o_usd', 'catalog_scenario_llama33_usd',
                        'call_latency_p50_ms', 'call_latency_p95_ms', 'estimated_c8_seconds', 'estimated_c16_seconds'):
                vals = [r[key] for r in rr]
                item.update({key + '_median': float(np.median(vals)), key + '_min': float(min(vals)), key + '_max': float(max(vals))})
            aggregates.append(item)
    result = {'protocol': 'Usage and per-request latency come from immutable logs, including invalid responses. '
              'No billed dollar cost is recorded. Cost formula: (input_tokens * input_USD_per_M + output_tokens * output_USD_per_M)/1e6. '
              'The 1/5 USD-per-million column is an explicitly hypothetical price scenario, not an invoice or verified vendor rate; '
              'no cached-input discount assumed. Enrollment and subsequent query costs are separate. '
              'Timestamps are completion times and collection spans include scheduling and retry gaps. '
              'Concurrency estimates replay recorded request durations in deterministic list order on ideal c workers, '
              'assuming duration independence and zero dispatch overhead; these are not measured concurrent audit wall times.',
              'pricing_scenarios': {'accessed': pricing['accessed_date'],
                  'snapshot': 'results/service_audit/current_pricing_snapshot.json',
                  'snapshot_sha256': sha(pricing_path), 'source': pricing['source'],
                  'gpt4o': {'input_USD_per_million': gpt_price[0] * 1e6, 'output_USD_per_million': gpt_price[1] * 1e6, 'catalog_model': 'openai/gpt-4o'},
                  'llama33': {'input_USD_per_million': llama_price[0] * 1e6, 'output_USD_per_million': llama_price[1] * 1e6, 'catalog_model': 'meta-llama/llama-3.3-70b-instruct'},
                  'scope': 'Common catalog price scenarios applied to every observed workload, not endpoint-matched invoices, minimum provider quotes, or historical charges. No account identity or route inferred from aliases.'},
              'field_coverage': coverage, 'per_target': rows, 'aggregate': aggregates}
    save(out / 'overhead.json', result)
    write_csv(out / 'overhead_per_target.csv', rows)
    write_csv(out / 'overhead_summary.csv', aggregates)
    return result


def benchmark(data, out):
    results = []
    for k, nr, nq in [(20, 3, 3), (40, 8, 7), (10, 8, 7)]:
        ref, query, cells = protocol_groups(data['B'], k, nr)
        # First three identities, all valid cells; fixture identity labels omitted from timing summary.
        fixtures = []
        for t in sorted(ref)[:3]:
            pairs = [(arrays(ref[t][c]), arrays(query[t][c][:nq])) for c in cells]
            fixtures.append([(a, b) for a, b in pairs if len(a) and len(b)])
        def energy_run(pairs):
            return sum(energy_score(a, b) for a, b in pairs) / len(pairs)
        def permutation_run(pairs):
            vals = [energy_permutations(a, b, 999, seed_for('timing', j, len(a), len(b))) for j, (a, b) in enumerate(pairs)]
            return float(permutation_p(np.mean(vals, axis=0)))
        for method, func, repeats in [('regularized_energy', energy_run, 60), ('stratified_energy_999_permutations', permutation_run, 30)]:
            for pair in fixtures:
                func(pair)
            durations = []
            for i in range(repeats):
                begin = time.perf_counter_ns()
                func(fixtures[i % len(fixtures)])
                durations.append((time.perf_counter_ns() - begin) / 1e6)
            results.append({'K_planned': k, 'reference_n': nr, 'query_n': nq, 'method': method,
                            'repeats': repeats, 'fixtures': len(fixtures), 'valid_cell_counts': [len(f) for f in fixtures],
                            'median_ms': float(np.median(durations)), 'p95_ms': float(np.quantile(durations, .95)),
                            'min_ms': float(min(durations)), 'max_ms': float(max(durations))})
    report = {'environment': {'OS_family': platform.system(), 'architecture': platform.machine(),
                             'logical_cpu_count': os.cpu_count(), 'python': platform.python_version(),
                             'numpy': np.__version__, 'blas_threads_requested': os.environ.get('OPENBLAS_NUM_THREADS')},
              'scope': 'Measured wall time of already-loaded one-reference/one-query scoring only, warm-up excluded. '
              'Includes per-cell distance calculation and, for permutation, 999 null samples and aggregation. '
              'Excludes API/network, parsing, disk I/O, enrollment and full all-pairs search; hardware/load-dependent.',
              'results': results}
    save(out / 'local_timing.json', report)
    write_csv(out / 'local_timing.csv', results)
    return report


def report(out, families, routes, overhead, timing):
    lines = ['# Offline Service-Audit Analyses', '',
             'All outputs are new. Original responses and prior frozen results remain untouched. No model/API calls.', '',
             '## Same-family negative pairs', '',
             'Pairs are distinct declared labels within a versioned family/vendor map, not verified or ordered tier downgrades. B rows are calibration resubstitution; A/B share 480 original responses, so A is not an independent calibration holdout. Threshold transfers to other cohorts can mismatch sample sizes.', '',
             '| Cohort | Same-family negatives | Energy EER | Frozen FAR / FRR | Hybrid EER |',
             '| --- | ---: | ---: | ---: | ---: |']
    for scenario in ('A_fresh', 'B20x6', 'B_full', 'E', 'S3_color_within'):
        rr = [r for r in families['results'] if r['scenario'] == scenario and r['negative_group'] == 'same_family']
        e = next(r for r in rr if r['metric'] == 'energy_reg')
        h = next(r for r in rr if r['metric'] == 'hybrid')
        lines.append(f"| {scenario} | {e['n_directed_negative']} | {e['eer']:.2%} | {e['far']:.2%} / {e['frr']:.2%} | {h['eer']:.2%} |")
    lines += ['', '## Offline mixed routing', '',
              'Twenty fixed seeds; 5–95% ranges quantify simulation variability, not confidence intervals over independent deployments. p=1 is genuine rejection. The simulation does not establish a universal sample requirement for 20% fallback.', '',
              '| Protocol | Query calls | Detection at 20% fallback | Seed range | Pure-clean FRR |',
              '| --- | ---: | ---: | ---: | ---: |']
    for r in routes['results']:
        if r['subgroup'] == 'all_distinct_labels' and r['p_honest'] == .8:
            lines.append(f"| {r['protocol']} | {r['query_calls']} | {r['rejection_mean']:.2%} | {r['rejection_seed_p05']:.2%}–{r['rejection_seed_p95']:.2%} | {r['genuine_frr_mean']:.2%} |")
    lines += ['', 'Full probability grids, subgroup values and per-pair simulation outcomes are in routing.csv/routing_seeds.csv/routing_pairs.csv.', '',
              '## Operational overhead', '', overhead['protocol'], '',
              'Two common-rate scenarios additionally use the saved OpenRouter catalog snapshot accessed 2026-11-13: GPT-4o input/output $2.50/$10 per million, and Llama-3.3 input/output $0.71/$0.71 per million. These are current catalog rate scenarios, not the actual aliases\' rates, minimum-provider quotes or historical bills. No cached-input discount is applied.', '',
              '| Query cohort | Median calls | Median input/output tokens | Median GPT-4o-rate USD | Median Llama-rate USD | Estimated c=8 seconds |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in overhead['aggregate']:
        if r['role'] == 'query':
            lines.append(f"| {r['cohort']} | {r['calls_median']:.0f} | {r['input_tokens_median']:.1f} / {r['output_tokens_median']:.1f} | {r['catalog_scenario_gpt4o_usd_median']:.5f} | {r['catalog_scenario_llama33_usd_median']:.5f} | {r['estimated_c8_seconds_median']:.2f} |")
    lines += ['', 'Each column summarizes target-level values independently. Enrollment is separate in overhead_per_target.csv. Formula-based price scenarios must not be described as measured billed costs. Concurrent times are ideal scheduling estimates, not actual concurrent audit measurements.', '',
              '## Local timing', '', timing['scope'], '', '| Budget | Method | Median ms | P95 ms |', '| --- | --- | ---: | ---: |']
    for r in timing['results']:
        lines.append(f"| {r['K_planned']} cells, {r['reference_n']}v{r['query_n']} | {r['method']} | {r['median_ms']:.3f} | {r['p95_ms']:.3f} |")
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=OUT)
    args = ap.parse_args()
    out = args.output.resolve()
    if out == ROOT:
        ap.error('Output must be a subdirectory')
    out.mkdir(parents=True, exist_ok=True)
    protected = json.loads((ROOT / 'results/integrity_manifest.json').read_text())['files']
    before = {rel: sha(ROOT / rel) for rel in protected}
    assert before == protected, 'Protected evidence differed before execution'
    sys.addaudithook(guard)
    data = {name: load(path) for name, path in FILES.items()}
    families = family_analysis(out)
    routes = routing_analysis(data, out)
    overhead = overhead_analysis(data, out)
    timing = benchmark(data, out)
    report(out, families, routes, overhead, timing)
    after = {p: sha(ROOT / p) for p in before}
    assert after == protected, 'Protected evidence changed'
    save(out / 'manifest.json', {'protocol': 'service_audit_offline_v1', 'seeds': list(SEEDS),
          'protected_sha256': before, 'all_protected_unchanged': True,
          'raw_logs_protected': sum(p.endswith('.jsonl') for p in before), 'live_api_calls': 0,
          'source_sha256': {str(Path(__file__).relative_to(ROOT)): sha(__file__),
                            'config/family_map.json': sha(ROOT / 'config/family_map.json'),
                            'extensions/live_validation_20261111/configs/targets.s3_20models_locked64.json': sha(ROOT / 'extensions/live_validation_20261111/configs/targets.s3_20models_locked64.json'),
                            'results/service_audit/current_pricing_snapshot.json': sha(ROOT / 'results/service_audit/current_pricing_snapshot.json'),
                            'tests/test_service_statistics.py': sha(ROOT / 'tests/test_service_statistics.py'),
                            'analyze.py': sha(ROOT / 'analyze.py'),
                            'scripts/hueprint_audit/core.py': sha(ROOT / 'scripts/hueprint_audit/core.py')},
          'output_sha256': {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != 'manifest.json'}})
    shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print('completed', str(shown), flush=True)


if __name__ == '__main__':
    main()
