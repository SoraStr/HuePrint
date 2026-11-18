"""Cohort comparisons and B-only reference normalization experiments."""
from __future__ import annotations
import collections
import copy
import itertools
import json
from pathlib import Path
import numpy as np
import analyze as an
from .core import (ROOT, METRICS, CAL_METRICS, SEED, JITTER_SEEDS, load, save, group,
                   split, summarize, matrix, stats, thresholds, operating, jitter_group,
                   enrollment_mu, mu_for_matrix, select_alpha_bcv, energy_test_matrix,
                   pvalue_stats, rgb100_to_lab, cell_scores)

EXT = 'extensions/live_validation_20261111/'
FILES = {'A': 'data/census_40models.jsonl', 'B': 'data/exp_40u15r.jsonl',
         'C': 'data/exp_paraphrase.jsonl', 'D': 'data/exp_bruckner_baseline.jsonl',
         'E': 'data/exp_heldout_confirm.jsonl',
         'S1_CF21': EXT+'data/s1a_cf_t21d.jsonl', 'S1_OR21': EXT+'data/s1b_or_crossgateway.jsonl',
         'S2': EXT+'data/s2_multiprovider.jsonl', 'S3_color': EXT+'data/s3a_hueprint_locked64_n30.jsonl',
         'S3_word': EXT+'data/s3b_bruckner_locked64_n30.jsonl',
         'S4a': EXT+'data/s4_implicit_css.jsonl', 'S4b': EXT+'data/s4b_implicit_v5_exact.jsonl'}


def within(rows, min_split=1):
    a, b = split(rows)
    for t in sorted(set(a) & set(b)):
        valid = {c for c in set(a[t]) & set(b[t])
                 if sum(r['parsed']['status'] == 'valid' for r in a[t][c]) >= min_split
                 and sum(r['parsed']['status'] == 'valid' for r in b[t][c]) >= min_split}
        a[t] = {c: r for c, r in a[t].items() if c in valid}
        b[t] = {c: r for c, r in b[t].items() if c in valid}
    return a, b


def b20(rows):
    return [r for r in rows if r['lang'] in ('en', 'zh') and r['rep'] <= 6]


def make_s1(data):
    mapping = {t['id']: t['paired_cf_id'] for t in json.loads((ROOT/EXT/'configs/targets.s1_or_crossgateway.json').read_text())['targets']}
    ids = {r['target_id'] for r in data['S1_CF21']}
    enroll = [r for r in b20(data['B']+data['E']) if r['target_id'] in ids]
    return group(enroll), group(data['S1_CF21']), group(data['S1_OR21'], target_map=mapping)


def fit_lab_scale(ref):
    rgb_total = lab_total = 0.
    for cs in summarize(ref).values():
        for s in cs.values():
            x = s['rgb_arr']; y = rgb100_to_lab(x)
            rgb_total += np.linalg.norm(x[:, None]-x[None, :], axis=-1).sum()
            lab_total += np.linalg.norm(y[:, None]-y[None, :], axis=-1).sum()
    scale = float(rgb_total/lab_total)
    return {'scale': scale, 'delta_lab_native': 15/scale, 'delta_in_scaled_lab': 15.,
            'source': 'B-20x6 odd enrollment only; ratio of summed within-cell pair distances',
            'rgb_distance_sum': float(rgb_total), 'lab_distance_sum': float(lab_total),
            'clipping_or_channelwise_scaling': False}


def family_scores(rows, fmap, minimum):
    full = group(rows)
    for t in full:
        full[t] = {c: rs for c, rs in full[t].items() if sum(r['parsed']['status'] == 'valid' for r in rs) >= minimum}
    ids, mats, _ = matrix(full, full)
    counts = collections.Counter(fmap[t]['family'] for t in ids if not fmap.get(t, {}).get('is_singleton', True))
    out = {}
    for m, mat in mats.items():
        mat = mat.copy(); np.fill_diagonal(mat, np.inf)
        records = []
        for j, t in enumerate(ids):
            if fmap.get(t, {}).get('is_singleton', True) or counts[fmap[t]['family']] < 2:
                continue
            pred = ids[int(np.argmin(mat[:, j]))]
            records.append({'target': t, 'prediction': pred, 'hit': fmap[pred]['family'] == fmap[t]['family']})
        out[m] = {'correct': sum(r['hit'] for r in records), 'n': len(records), 'records': records}
    return out


def comparisons(data, out):
    results = {}; pairs = []
    fmap = json.loads((ROOT/'config/family_map.json').read_text())['families']
    def add(name, ref, query, family=False):
        ids, mats, counts = matrix(ref, query)
        entry = {'ids': ids, 'shared_valid_cells_min_max': [int(counts.min()), int(counts.max())],
                 'metrics': {m: stats(mat) for m, mat in mats.items()},
                 'matrices': {m: mat.tolist() for m, mat in mats.items()}}
        if family:
            for label, key in [('cross_sublineage', 'sublineage'), ('cross_family', 'family')]:
                neg = np.array([[fmap.get(t, {}).get(key, t) != fmap.get(u, {}).get(key, u) for u in ids] for t in ids])
                entry[label] = {m: stats(mat, negative=neg) for m, mat in mats.items()}
        results[name] = entry
        for i, t in enumerate(ids):
            for j, u in enumerate(ids):
                pairs.append({'scenario': name, 'reference': t, 'query': u, 'genuine': i == j,
                              'valid_cells': int(counts[i, j]), **{m: float(mat[i, j]) for m, mat in mats.items()}})
        print('comparison', name, flush=True)
        return ids, mats
    for name, rows, minimum in [('A_fresh', data['A'], 2), ('B_full', data['B'], 5), ('B20x6', b20(data['B']), 1), ('E', data['E'], 1)]:
        add(name, *within(rows, minimum), family=True)
        results[name]['loo_family'] = family_scores(rows, fmap, 4 if name == 'A_fresh' else 10 if name == 'B_full' else 2)
    from reproduce_all import load_jsonl_clean
    add('A_legacy_reasoning_control', *within(load_jsonl_clean(FILES['A'], True)[0], 2))
    for prefix in ('p1_', 'p2_'):
        rows = [r for r in data['C'] if r['task_id'].startswith(prefix)]
        add('C_'+prefix[:2]+'_within', *within(rows))
    tasks = {'hex_favorite', 'rgb_favorite', 'hex_ocean', 'hex_warm'}
    ref = group([r for r in data['B'] if r['task_id'] in tasks and r['lang'] in ('en', 'zh') and r['rep'] <= 8])
    for name, prefixes in [('P1', ('p1_',)), ('P2', ('p2_',)), ('P1_P2', ('p1_', 'p2_'))]:
        rows = [r for r in data['C'] if r['task_id'][:3] in prefixes]
        add('C_P0_to_'+name, ref, group(rows, task_map={r['task_id']: r['task_id'][3:] for r in rows}))
    # D contains words; parsed RGB=[0,0,0] is a parser placeholder, not color data.
    results['D'] = {'color_metrics': 'not_applicable: single-word responses', 'raw_baselines': 'baseline_grid.csv'}
    cf0, cf21, or21 = make_s1(data)
    for label, a, b in [('CF0_CF21', cf0, cf21), ('CF21_OR21', cf21, or21), ('CF0_OR21', cf0, or21)]:
        add('S1_'+label+'_6v6', a, b)
    for name in ('S1_CF21', 'S1_OR21', 'S3_color', 'S4a', 'S4b'):
        add(name+'_within', *within(data[name]))
    add('S4b_explicit_to_implicit', group([r for r in data['S3_color'] if r['rep'] <= 6]), group([r for r in data['S4b'] if r['lang'] == 'en']))
    meta = {t['id']: t for t in json.loads((ROOT/EXT/'configs/targets.s2_multiprovider.json').read_text())['targets']}
    for label, ref, query in [('6v6', group(data['S2']), group(data['S2'])), ('3v3', *within(data['S2']))]:
        ids, mats, _ = matrix(ref, query)
        positive = np.array([[t != u and meta[t]['weight_group'] == meta[u]['weight_group'] for u in ids] for t in ids])
        negative = np.array([[meta[t]['weight_group'] != meta[u]['weight_group'] for u in ids] for t in ids])
        metrics = {}
        for m, mat in mats.items():
            s = stats(mat, positive, negative); masked = mat.copy(); np.fill_diagonal(masked, np.inf)
            s['top1'] = float(np.mean([meta[ids[int(np.argmin(masked[:, j]))]]['weight_group'] == meta[t]['weight_group'] for j, t in enumerate(ids)]))
            metrics[m] = s
        results['S2_cross_provider_'+label] = {'ids': ids, 'metrics': metrics, 'matrices': {m: a.tolist() for m, a in mats.items()}}
        if label == '6v6':
            regimes = {}
            def regime(t, u):
                x, y = meta[t]['quant'], meta[u]['quant']
                if x not in ('bf16', 'fp8', 'int4', 'fp4') or y not in ('bf16', 'fp8', 'int4', 'fp4'): return 'unspecified_precision'
                if x == y: return 'matched'
                if {x, y} == {'bf16', 'fp8'}: return 'moderate'
                return 'aggressive'
            for reg in ('matched', 'moderate', 'aggressive', 'unspecified_precision'):
                pos = [(i, j) for i, j in itertools.combinations(range(len(ids)), 2) if positive[i, j] and regime(ids[i], ids[j]) == reg]
                queries = [j for j, t in enumerate(ids) if any(positive[i, j] and regime(u, t) == reg for i, u in enumerate(ids))]
                neg = [(i, j) for j in queries for i in range(len(ids)) if negative[i, j]]
                regimes[reg] = {}
                for m, mat in mats.items():
                    roc = an.compute_roc_eer([mat[i, j] for i, j in pos], [mat[i, j] for i, j in neg])
                    hits = []
                    for j in queries:
                        eligible = [i for i in range(len(ids)) if negative[i, j] or (positive[i, j] and regime(ids[i], ids[j]) == reg)]
                        best = min(eligible, key=lambda i: (mat[i, j], ids[i])); hits.append(bool(positive[best, j]))
                    regimes[reg][m] = {'auc': roc['auc_raw'], 'eer': roc['eer_linear_raw'], 'top1': float(np.mean(hits)), 'n_genuine': len(pos), 'n_impostor': len(neg)}
            results['S2_precision_regimes'] = regimes
            clean = []; low = []
            for i, t in enumerate(ids):
                for j, u in enumerate(ids):
                    if positive[i, j] and meta[t]['quant'] in ('bf16', 'fp8'):
                        if meta[u]['quant'] in ('bf16', 'fp8'): clean.append((i, j))
                        elif meta[u]['quant'] in ('int4', 'fp4'): low.append((i, j))
            results['S2_T1b'] = {}
            for m, mat in mats.items():
                r = an.compute_roc_eer([mat[i, j] for i, j in clean], [mat[i, j] for i, j in low])
                results['S2_T1b'][m] = {'auc': r['auc_raw'], 'eer': r['eer_linear_raw'], 'n_control': len(clean), 'n_lowbit': len(low)}
    save(out/'comparisons.json', results)
    return results, pairs


def calibration_fit(ref, query, planned_n, repeats):
    ids, mats, _ = matrix(ref, query)
    mu, details = enrollment_mu(ref, planned_n, repeats)
    models = {}
    for m in CAL_METRICS:
        mus = mu_for_matrix(ref, query, ids, details, m)
        alpha, cv = select_alpha_bcv(mats[m], mus)
        models[m] = {'cv': cv, 'selected_alpha': alpha, 'variants': {}}
        for name, a in [('raw', 0.), ('self_alpha1', 1.), ('self_Bcv', alpha)]:
            adjusted = mats[m]-a*mus
            models[m]['variants'][name] = {'alpha': a, **thresholds(adjusted), 'development_roc': stats(adjusted)}
    return {'planned_query_n': planned_n, 'enrollment_ids': ids, 'bootstrap_repeats': repeats,
            'enrollment_mu': mu, 'cell_details': details, 'models': models}


def calibration(data, out, permutations=999, repeats=256):
    b3 = within(b20(data['B']))
    # Table VIII's original attack suite uses >=1 valid sample on either side.
    # Table II/B verification uses >=5 and drops a few concentrated-failure
    # cells. Reusing its threshold here would silently change the experiment.
    bfull = within(data['B'], 1)
    b6 = (group([r for r in data['B'] if r['lang'] in ('en', 'zh') and r['rep'] <= 6]),
          group([r for r in data['B'] if r['lang'] in ('en', 'zh') and 7 <= r['rep'] <= 12]))
    fits = {}
    for name, pair, nq in [('B3v3', b3, 3), ('B6v6', b6, 6), ('B8v7', bfull, 7)]:
        fits[name] = calibration_fit(*pair, nq, repeats)
        print('calibration frozen', name, flush=True)
    # Freeze this artifact before evaluating any held-out scenario; no fitting below.
    save(out/'frozen_calibration.json', fits)
    rows = []; p_rows = []; score_records = {}; mus_saved = {}; cache = {}
    def evaluate(name, ref, query, fit_name, planned_n, use_p=True, attack=None, diag_override=None):
        fit = fits[fit_name]
        key = (id(ref), planned_n)
        if key not in cache:
            cache[key] = enrollment_mu(ref, planned_n, repeats)
        mu, details = cache[key]
        mus_saved[name] = mu
        ids, mats, _ = matrix(ref, query)
        entry = {'ids': ids, 'matrices': {m: mats[m].tolist() for m in CAL_METRICS}, 'mu': {}}
        for m in CAL_METRICS:
            mus = mu_for_matrix(ref, query, ids, details, m)
            entry['mu'][m] = mus.tolist()
            for variant, params in fit['models'][m]['variants'].items():
                adjusted = mats[m]-params['alpha']*mus
                s = stats(adjusted)
                for threshold in ('tau_mid', 'tau_u0'):
                    op = operating(adjusted, params[threshold])
                    r = {'scenario': name, 'calibration': fit_name, 'metric': m, 'variant': variant,
                         'alpha': params['alpha'], 'threshold_kind': threshold, 'threshold': params[threshold],
                         **s, **op, 'attack_acceptance': float(1-op['frr']) if attack == 'replay' else None}
                    if diag_override is not None:
                        # Replay + entropy screen uses the existing, fixed .30/.25 rule.
                        accepted = (np.diag(adjusted) <= params[threshold]) & np.array([diag_override[t] for t in ids])
                        r['attack_acceptance_with_entropy_screen'] = float(accepted.mean())
                    rows.append(r)
        score_records[name+'@'+fit_name] = entry
        if use_p:
            _, statistic, pv = energy_test_matrix(ref, query, permutations)
            p_rows.append({'scenario': name, 'statistic': 'cell_mean_Szekely_Rizzo_energy_V',
                           'permutations': permutations, **pvalue_stats(pv)})
            entry['energy_permutation_p'] = pv.tolist(); entry['energy_test_statistic'] = statistic.tolist()
        print('calibration evaluation', name, fit_name, flush=True)
    # Reference calibration samples and test samples remain distinct.
    for name, pair, nq in [('B3v3', b3, 3), ('B6v6', b6, 6), ('B8v7', bfull, 7)]:
        cache[(id(pair[0]), nq)] = (fits[name]['enrollment_mu'], fits[name]['cell_details'])
        evaluate(name+'_development', *pair, name, nq)
    er, eq = within(data['E'])
    evaluate('E_clean', er, eq, 'B3v3', 3)
    for seed in JITTER_SEEDS:
        evaluate('E_jitter8_seed'+str(seed), er, jitter_group(eq, 8, seed), 'B3v3', 3)
    cf0, cf21, or21 = make_s1(data)
    for label, ref, query in [('CF0_CF21', cf0, cf21), ('CF21_OR21', cf21, or21), ('CF0_OR21', cf0, or21)]:
        for fit in ('B3v3', 'B6v6'):
            evaluate('S1_'+label, ref, query, fit, 6, use_p=fit == 'B6v6')
    for label, (ref, query), fit_name, nq in [('Bfull', bfull, 'B8v7', 7), ('B20x6', b3, 'B3v3', 3)]:
        for amplitude in (1, 2, 4, 8, 15, 31):
            for seed in JITTER_SEEDS:
                # Permutation results for Table VIII scenarios; all geometric sweeps retained.
                use_p = amplitude in (1, 8, 15)
                evaluate(f'{label}_jitter{amplitude}_seed{seed}', ref, jitter_group(query, amplitude, seed), fit_name, nq, use_p=use_p)
        for shift in (-31, -15, -8, 8, 15, 31):
            evaluate(f'{label}_shift{shift}', ref, jitter_group(query, shift, 0, 'directional_shift'), fit_name, nq, use_p=abs(shift) == 8)
        for step in (17, 32):
            evaluate(f'{label}_quant{step}', ref, jitter_group(query, step, 0, 'palette_quant'), fit_name, nq, use_p=step == 32)
        replay = replay_groups(ref, query)
        for mode, fake in replay.items():
            sa, sb = summarize(ref), summarize(fake)
            screen = {}
            for t in ref:
                er0 = np.mean([an.shannon_entropy_bits(s['hex_counts']) for s in sa[t].values()])
                eq0 = np.mean([an.shannon_entropy_bits(s['hex_counts']) for s in sb[t].values()])
                screen[t] = not (er0 > .30 and eq0 < .25*er0)
            evaluate(f'{label}_replay_{mode}', ref, fake, fit_name, nq, attack='replay', diag_override=screen)
        routing = routing_scores(ref, query)
        for fraction, records in routing.items():
            _, details = cache[(id(ref), nq)]
            for m in CAL_METRICS:
                for variant, params in fits[fit_name]['models'][m]['variants'].items():
                    for threshold in ('tau_mid', 'tau_u0'):
                        decisions = []
                        for r in records:
                            mus = np.mean([details[r['reference']][c][m]['mu'] for c in r['cells']])
                            decisions.append(r['scores'][m]-params['alpha']*mus <= params[threshold])
                        rows.append({'scenario': f'{label}_routing{fraction}', 'calibration': fit_name, 'metric': m,
                                     'variant': variant, 'alpha': params['alpha'], 'threshold_kind': threshold,
                                     'threshold': params[threshold], 'far': float(np.mean(decisions)),
                                     'n_impostor': len(decisions), 'attack_acceptance': float(np.mean(decisions))})
    save(out/'calibration_scores.json', score_records)
    save(out/'enrollment_baselines.json', mus_saved)
    save(out/'calibration_results.json', {'operating_points': rows, 'energy_permutation_tests': p_rows})
    return rows, p_rows


def replay_groups(ref, query):
    out = {m: copy.deepcopy(query) for m in ('centroid', 'cyclic', 'resample')}
    rng = np.random.default_rng(20261021)
    for t, cells in sorted(ref.items()):
        for c, rs in sorted(cells.items()):
            valid = [r for r in rs if r['parsed']['status'] == 'valid']
            if not valid: continue
            rgb = np.rint(np.mean([r['parsed']['rgb'] for r in valid], axis=0)).astype(int).tolist()
            for i, old in enumerate(query[t][c]):
                r = dict(old); p = dict(r['parsed'])
                p.update(status='valid', rgb=rgb, canonical_hex='#'+''.join(f'{v:02X}' for v in rgb), voxel_bin_8='_'.join(str(v//32) for v in rgb))
                r['parsed'] = p
                out['centroid'][t][c][i] = r
                out['cyclic'][t][c][i] = valid[i % len(valid)]
                out['resample'][t][c][i] = valid[int(rng.integers(len(valid)))]
    return out


def routing_scores(ref, query):
    rs = summarize(ref); rng = np.random.default_rng(20261021); result = {}
    for frac in (.1, .25, .5):
        records = []
        for t in sorted(ref):
            for u in sorted(query):
                if t == u: continue
                scores = []; common = []
                for c in sorted(set(rs[t]) & set(query[u])):
                    a, b = query[t][c], query[u][c]; n = min(len(a), len(b))
                    if not n or not rs[t][c]['n_valid']: continue
                    mixed = [a[k] if rng.random() < frac else b[k] for k in range(n)]
                    s = an.summarize_cell_samples(mixed)
                    if s['n_valid']:
                        scores.append(cell_scores(rs[t][c], s)); common.append(c)
                records.append({'reference': t, 'query': u, 'cells': common,
                                'scores': {m: float(np.mean([s[m] for s in scores])) for m in CAL_METRICS}})
        result[frac] = records
    return result


def color_spaces(data, out):
    scale = fit_lab_scale(within(b20(data['B']))[0]); rows = []; saved = {}
    for name, source, minimum in [('B_full', data['B'], 5), ('B20x6', b20(data['B']), 1), ('E', data['E'], 1), ('S3', data['S3_color'], 1)]:
        a, b = within(source, minimum)
        for seed in (None, *JITTER_SEEDS):
            query = b if seed is None else jitter_group(b, 8, seed)
            ids, mats, _ = matrix(a, query, lab_scale=scale['scale'])
            for m in ('energy_reg', 'energy_reg_lab'):
                rows.append({'dataset': name, 'condition': 'clean' if seed is None else 'jitter8', 'seed': seed,
                             'chart': 'RGB100' if m == 'energy_reg' else 'scaled_Lab_D65', **stats(mats[m])})
            saved[f'{name}_{seed}'] = {'ids': ids, 'rgb': mats['energy_reg'].tolist(), 'lab': mats['energy_reg_lab'].tolist()}
        print('color comparison', name, flush=True)
    save(out/'color_spaces.json', {'lab_scale': scale, 'results': rows, 'matrices': saved})
    return rows, scale


def b_budget(data, out):
    """Extend all 48 published B grid cells with paired regularized variants.

    Preserve Random(42), 200 subsets, first-n reps and 12-decimal tie statistic.
    Report any unavailable cell, rather than silently presenting equal coverage.
    """
    import random
    rows = []; draws = []
    selected = ('hybrid', 'hybrid_reg', 'energy_norm', 'energy_reg', 'robust_manifold')
    for n in (4, 6, 8, 10, 12, 15):
        a, b = within([r for r in data['B'] if r['rep'] <= n])
        aa, bb = summarize(a), summarize(b); ids = sorted(aa)
        cells = sorted({f"{r['task_id']}|{r['lang']}" for r in data['B']})
        pairs = {}
        for t in ids:
            for u in ids:
                shared = sorted(set(aa[t]) & set(bb[u]))
                pairs[t, u] = {c: cell_scores(aa[t][c], bb[u][c]) for c in shared}
        missing = sum(len(cells)-len(v) for v in pairs.values())
        rng = random.Random(42)
        for k in (1, 2, 4, 8, 16, 24, 32, 40):
            accum = {m: [] for m in selected}
            for draw in range(1 if k == 40 else 200):
                subset = cells if k == 40 else rng.sample(cells, k)
                draws.append({'n': n, 'K': k, 'draw': draw, 'cells': subset})
                for m in selected:
                    # Preserve the published denominator for exact old/new comparison.
                    mat = np.array([[sum(pairs[t, u][c][m] for c in subset if c in pairs[t, u])/len(subset) for u in ids] for t in ids])
                    stat = stats(mat); rounded = stats(np.round(mat, 12))
                    accum[m].append({'eer': stat['eer'], 'eer_discrete': stat['eer_discrete'], 'auc': stat['auc'], 'eer_12dp': rounded['eer']})
            for m, vals in accum.items():
                rows.append({'n_total_per_cell': n, 'n_reference': (n+1)//2, 'n_query': n//2, 'K': k,
                             'metric': m, 'subset_draws': len(vals), 'missing_pair_cells': missing,
                             **{key: float(np.mean([v[key] for v in vals])) for key in vals[0]}})
        print('B budget n', n, flush=True)
    save(out/'B_budget.json', {'results': rows, 'subsets': draws,
                             'legacy_missing_cell_denominator': 'divide by K, same as original; missing counts explicitly exported'})
    return rows
