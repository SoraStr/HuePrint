"""Raw-completion two-sample tests, adapted to a fixed prompt-stratified design.

Gao, Liang & Guestrin, ICLR 2025: one-hot kernel (Eq. 6), unbiased
MMD (Eq. 4), multinomial L1 (Eq. 8), and permutation calibration.
We average per-cell conditional statistics and permute within each cell;
we do not pool different prompt distributions or call a model/tokenizer.
"""
from __future__ import annotations
from fractions import Fraction
import itertools
import numpy as np
import analyze as an
from .core import (SEED, JITTER_SEEDS, METRICS, seed_for, group, summarize, jitter_group,
                   permutation_weights, permutation_p, stats, pvalue_stats, cell_scores, save)
from .experiments import b20

BASELINES = ('string_mmd_u', 'string_tv')


def exact_mmd_u_permutations(x, y, count, seed):
    """Exact integer numerators and denominator for discrete one-hot MMD-U."""
    n, m = len(x), len(y)
    if min(n, m) < 2:
        raise ValueError('Unbiased MMD needs two raw completions per side')
    strings = x + y
    categories = {s: i for i, s in enumerate(sorted(set(strings)))}
    features = np.zeros((len(strings), len(categories)), dtype=np.int64)
    features[np.arange(len(strings)), [categories[s] for s in strings]] = 1
    mask = np.rint(permutation_weights(n, m, count, np.random.default_rng(seed))).astype(np.int64)
    a = mask @ features
    b = features.sum(axis=0) - a
    if n == m:
        h = n
        num = h * ((a * (a - 1) + b * (b - 1)).sum(axis=1)) - 2 * (h - 1) * ((a * b).sum(axis=1))
        den = h * h * (h - 1)
    else:
        sa = (a * (a - 1)).sum(axis=1)
        sb = (b * (b - 1)).sum(axis=1)
        sab = (a * b).sum(axis=1)
        num = sa * (m * (m - 1)) + sb * (n * (n - 1)) - 2 * sab * ((n - 1) * (m - 1))
        den = n * (n - 1) * m * (m - 1)
    return num, den, a, b


def exact_mmd_u_cell(x, y) -> Fraction:
    """Exact rational one-hot MMD-U for a single probe cell (supports arbitrary n, m >= 2)."""
    n, m = len(x), len(y)
    if min(n, m) < 2:
        raise ValueError('Unbiased MMD needs two raw completions per side')
    cats = set(x) | set(y)
    ca = {s: 0 for s in cats}
    cb = {s: 0 for s in cats}
    for s in x:
        ca[s] += 1
    for s in y:
        cb[s] += 1
    if n == m:
        h = n
        t_val = h * sum(ca[s] * (ca[s] - 1) + cb[s] * (cb[s] - 1) for s in cats) - 2 * (h - 1) * sum(ca[s] * cb[s] for s in cats)
        return Fraction(t_val, h * h * (h - 1))
    sa = sum(ca[s] * (ca[s] - 1) for s in cats)
    sb = sum(cb[s] * (cb[s] - 1) for s in cats)
    sab = sum(ca[s] * cb[s] for s in cats)
    return Fraction(sa, n * (n - 1)) + Fraction(sb, m * (m - 1)) - Fraction(2 * sab, n * m)


def exact_mmd_roc_eer(genuine_exact, impostor_exact) -> dict:
    """Order-invariant ROC AUC and linear/discrete EER on exact discrete (int or Fraction) scores."""
    g_list = list(genuine_exact)
    i_list = list(impostor_exact)
    n_g, n_i = len(g_list), len(i_list)
    if not n_g or not n_i:
        raise ValueError('ROC needs both classes')
    unique_scores = sorted(set(g_list) | set(i_list))
    g_counts = {u: 0 for u in unique_scores}
    i_counts = {u: 0 for u in unique_scores}
    for v in g_list:
        g_counts[v] += 1
    for v in i_list:
        i_counts[v] += 1

    # Mann-Whitney U AUC with exact half-weight on ties: P(g < i) + 0.5 * P(g == i)
    imp_Remaining = n_i
    win_twice = 0
    for u in unique_scores:
        gc = g_counts[u]
        ic = i_counts[u]
        imp_strictly_greater = imp_Remaining - ic
        win_twice += gc * (2 * imp_strictly_greater + ic)
        imp_Remaining -= ic
    auc = win_twice / (2.0 * n_g * n_i)

    # Exact ROC curve points: start at (FAR=0, FRR=1), then step once per unique exact threshold group
    far_vec = [0.0]
    frr_vec = [1.0]
    cum_g = 0
    cum_i = 0
    for u in unique_scores:
        cum_g += g_counts[u]
        cum_i += i_counts[u]
        far_vec.append(cum_i / n_i)
        frr_vec.append((n_g - cum_g) / n_g)

    far_arr = np.asarray(far_vec, dtype=np.float64)
    frr_arr = np.asarray(frr_vec, dtype=np.float64)
    gaps = np.abs(frr_arr - far_arr)
    best_idx = int(np.argmin(gaps))
    best_eer = float(0.5 * (frr_arr[best_idx] + far_arr[best_idx]))

    diff = far_arr - frr_arr
    cross_indices = np.flatnonzero(diff >= 0.0)
    if len(cross_indices) == 0:
        eer_linear = best_eer
    else:
        ix = int(cross_indices[0])
        if ix == 0 or abs(diff[ix] - diff[ix - 1]) < 1e-12:
            eer_linear = float(far_arr[ix])
        else:
            w = -diff[ix - 1] / (diff[ix] - diff[ix - 1])
            eer_linear = float(far_arr[ix - 1] + w * (far_arr[ix] - far_arr[ix - 1]))

    return {
        'auc': auc,
        'eer': eer_linear,
        'eer_discrete': best_eer,
        'n_threshold_groups': len(unique_scores),
    }


def exact_mmd_stats(exact_mat, float_mat=None, positive=None, negative=None) -> dict:
    """Compute verification metrics on a 2D matrix of exact (int or Fraction) MMD-U scores."""
    n = len(exact_mat)
    pos = np.eye(n, dtype=bool) if positive is None else np.asarray(positive, dtype=bool)
    neg = ~pos if negative is None else np.asarray(negative, dtype=bool)
    g_ex = [exact_mat[i][j] for i in range(n) for j in range(n) if pos[i, j]]
    i_ex = [exact_mat[i][j] for i in range(n) for j in range(n) if neg[i, j]]
    roc = exact_mmd_roc_eer(g_ex, i_ex)
    if float_mat is None:
        fmat = np.array([[float(exact_mat[i][j]) for j in range(n)] for i in range(n)], dtype=np.float64)
    else:
        fmat = np.asarray(float_mat, dtype=np.float64)
    unique_all = sorted({exact_mat[i][j] for i in range(n) for j in range(n)})
    rmap = {v: idx for idx, v in enumerate(unique_all)}
    rank_mat = np.array([[rmap[exact_mat[i][j]] for j in range(n)] for i in range(n)], dtype=np.int64)
    return {
        'auc': roc['auc'],
        'eer': roc['eer'],
        'eer_discrete': roc['eer_discrete'],
        'n_genuine': len(g_ex),
        'n_impostor': len(i_ex),
        'genuine_mean': float(fmat[pos].mean()),
        'impostor_mean': float(fmat[neg].mean()),
        'top1': float(np.mean(np.argmin(rank_mat, axis=0) == np.arange(n))),
    }


def categorical_permutations(x, y, count, seed):
    n, m = len(x), len(y)
    num, den, a, b = exact_mmd_u_permutations(x, y, count, seed)
    mmd = num.astype(np.float64) / float(den)
    tv = .5 * np.abs(a / n - b / m).sum(axis=1)
    return {'string_mmd_u': mmd, 'string_tv': tv, 'string_mmd_u_num': num, 'string_mmd_u_den': den}


def cell_subsets(total, k, count=40):
    combinations = list(itertools.combinations(range(total), k))
    if len(combinations) <= count:
        return combinations
    rng = np.random.default_rng(seed_for(SEED, 'cell-subsets', total, k))
    ix = sorted(rng.choice(len(combinations), size=count, replace=False))
    return [combinations[j] for j in ix]


def aggregate_exact_mmd_u(mmd_num, mmd_den, ix):
    """Aggregate per-cell exact MMD-U numerators/denominators across cell indices ix."""
    sub_num = mmd_num[:, :, ix, :]
    sub_den = mmd_den[:, :, ix]
    nids = sub_num.shape[0]
    k_cells = len(ix)
    n_draws = sub_num.shape[-1]
    d0 = int(sub_den[0, 0, 0])
    if bool(np.all(sub_den == d0)):
        sum_t = sub_num.sum(axis=2, dtype=np.int64)
        total_den = d0 * k_cells
        obs_exact = sum_t[:, :, 0].tolist()
        obs_float = sum_t[:, :, 0].astype(np.float64) / float(total_den)
        pval = (1 + np.sum(sum_t[:, :, 1:] >= sum_t[:, :, :1], axis=2)) / float(n_draws)
        return obs_exact, obs_float, pval
    obs_exact = [[Fraction(0, 1) for _ in range(nids)] for _ in range(nids)]
    obs_float = np.zeros((nids, nids), dtype=np.float64)
    pval = np.zeros((nids, nids), dtype=np.float64)
    for i in range(nids):
        for j in range(nids):
            cell_dens = [int(sub_den[i, j, c]) for c in range(k_cells)]
            if len(set(cell_dens)) == 1:
                st = sub_num[i, j].sum(axis=0, dtype=np.int64)
                obs_exact[i][j] = Fraction(int(st[0]), cell_dens[0] * k_cells)
                obs_float[i, j] = float(obs_exact[i][j])
                pval[i, j] = (1 + int(np.sum(st[1:] >= st[0]))) / float(n_draws)
            else:
                draws = [
                    sum((Fraction(int(sub_num[i, j, c, b]), cell_dens[c]) for c in range(k_cells)), Fraction(0, 1)) / k_cells
                    for b in range(n_draws)
                ]
                obs_exact[i][j] = draws[0]
                obs_float[i, j] = float(draws[0])
                pval[i, j] = (1 + sum(1 for v in draws[1:] if v >= draws[0])) / float(n_draws)
    return obs_exact, obs_float, pval


def run_one(ref, query, count):
    ids = sorted(set(ref) & set(query)); cells = sorted(set.intersection(*(set(ref[t]) & set(query[t]) for t in ids)))
    nids, ncells = len(ids), len(cells)
    permutations = {m: np.zeros((nids, nids, ncells, count+1)) for m in BASELINES}
    permutations['string_mmd_u_num'] = np.zeros((nids, nids, ncells, count+1), dtype=np.int64)
    permutations['string_mmd_u_den'] = np.zeros((nids, nids, ncells), dtype=np.int64)
    color = {m: np.zeros((nids, nids, ncells)) for m in METRICS}
    color_applicable = all(r['format'] != 'single_word' for t in ids for c in cells for r in ref[t][c])
    aa, bb = summarize(ref), summarize(query)
    valid = np.ones((nids, nids, ncells), dtype=bool)
    for i, t in enumerate(ids):
        for j, u in enumerate(ids):
            for k, ck in enumerate(cells):
                x = [r.get('raw_text') or '' for r in ref[t][ck]]
                y = [r.get('raw_text') or '' for r in query[u][ck]]
                p = categorical_permutations(x, y, count, seed_for(SEED, 'strings', t, u, ck, len(x), len(y)))
                for m in BASELINES:
                    permutations[m][i, j, k] = p[m]
                permutations['string_mmd_u_num'][i, j, k] = p['string_mmd_u_num']
                permutations['string_mmd_u_den'][i, j, k] = p['string_mmd_u_den']
                if color_applicable:
                    valid[i, j, k] = aa[t][ck]['n_valid'] > 0 and bb[u][ck]['n_valid'] > 0
                    d = cell_scores(aa[t][ck], bb[u][ck])
                    for m in METRICS:
                        color[m][i, j, k] = d[m]
                else:
                    color['hex_jsd'][i, j, k] = an.jsd_base2(aa[t][ck]['hex_counts'], bb[u][ck]['hex_counts'])
    return ids, cells, permutations, color, valid, color_applicable


def baselines(data, out, permutations=999):
    rows = []; full_pairs = []; subset_records = []; raw_reparse_audit = []
    plans = [('S3_color', data['S3_color'], (6, 10, 20, 30)),
             ('S3_word', data['S3_word'], (6, 10, 20, 30)),
             ('B20x6', b20(data['B']), (6,)), ('D', data['D'], (6,))]
    for name, source, ns in plans:
        is_color = name in ('S3_color', 'B20x6')
        for n in ns:
            chosen = [r for r in source if r['rep'] <= n]
            a = group([r for r in chosen if r['rep'] % 2]); clean = group([r for r in chosen if not r['rep'] % 2])
            for jitter_seed in (None, *JITTER_SEEDS) if is_color else (None,):
                b = clean if jitter_seed is None else jitter_group(clean, 8, jitter_seed, raw=True)
                raw_reparse_audit.append({'dataset': name, 'n': n, 'seed': jitter_seed,
                    'ambiguous_bare_hex_after_jitter': sum(r.get('egress_raw_reparse_valid') is False for cs in b.values() for rs in cs.values() for r in rs)})
                ids, cells, null, geometric, valid, applicable = run_one(a, b, permutations)
                condition = 'clean' if jitter_seed is None else 'jitter8'
                for k in range(1, min(10, len(cells))+1):
                    subsets = cell_subsets(len(cells), k)
                    accum = {m: [] for m in (*BASELINES, *(METRICS if applicable else ('word_jsd',)))}
                    for draw, subset in enumerate(subsets):
                        ix = list(subset)
                        if jitter_seed is None:
                            subset_records.append({'dataset': name, 'n': n, 'K': k, 'draw': draw, 'cells': [cells[j] for j in ix]})
                        for m in BASELINES:
                            # Average test statistics, THEN calibrate the joint stratified null.
                            if m == 'string_mmd_u':
                                obs_exact, statistic, pval = aggregate_exact_mmd_u(
                                    null['string_mmd_u_num'], null['string_mmd_u_den'], ix
                                )
                                base_s = exact_mmd_stats(obs_exact, statistic)
                            else:
                                joint = null[m][:, :, ix, :].mean(axis=2)
                                pval = permutation_p(joint)
                                statistic = joint[:, :, 0]
                                base_s = stats(statistic)
                            pstats = pvalue_stats(pval)
                            s = {**base_s,
                                 'p_auc': pstats['p_score_roc']['auc'], 'p_eer': pstats['p_score_roc']['eer'],
                                 'same_model_rejection_rate': pstats['same_model_rejection_rate'],
                                 'different_model_rejection_rate': pstats['different_model_rejection_rate']}
                            accum[m].append(s)
                            if k == min(10, len(cells)) and draw == 0:
                                for i, t in enumerate(ids):
                                    for j, u in enumerate(ids):
                                        full_pairs.append({'dataset': name, 'n': n, 'K': k, 'seed': jitter_seed,
                                                           'condition': condition, 'metric': m, 'reference': t, 'query': u,
                                                           'genuine': i == j, 'statistic': float(statistic[i, j]), 'p_value': float(pval[i, j])})
                        for m in METRICS if applicable else ('word_jsd',):
                            actual = m if applicable else 'hex_jsd'
                            weights = valid[:, :, ix]
                            if np.any(weights.sum(axis=2) == 0):
                                raise ValueError('Selected probe subset has no valid colors for a pair')
                            total = np.zeros((len(ids), len(ids)))
                            for ci in ix:
                                total += geometric[actual][:, :, ci]*valid[:, :, ci]
                            mat = total/weights.sum(axis=2)
                            accum[m].append(stats(mat))
                    for m, values in accum.items():
                        common = set.intersection(*(set(v) for v in values))
                        numeric = {key: float(np.mean([v[key] for v in values])) for key in sorted(common)}
                        rows.append({'dataset': name, 'n_total_per_cell': n, 'n_reference': n//2, 'n_query': n//2,
                                     'K': k, 'reference_calls': k*n//2, 'query_calls': k*n//2,
                                     'condition': condition, 'seed': jitter_seed, 'metric': m,
                                     'subset_draws': len(subsets), 'permutations': permutations if m in BASELINES else None,
                                     **numeric,
                                     'eer_subset_p05': float(np.quantile([v['eer'] for v in values], .05)),
                                     'eer_subset_p95': float(np.quantile([v['eer'] for v in values], .95))})
                print('baseline', name, 'n', n, condition, jitter_seed, flush=True)
    save(out/'baseline_results.json', {'results': rows,
         'raw_reparse_audit': raw_reparse_audit,
         'unavailable_budgets': {'B20x6': [10, 20, 30], 'D': [10, 20, 30]},
         'budget_definition': 'n is total calls per cell across reference and query, split n/2 vs n/2; no replacement or extra calls',
         'invalid_raw_responses': 'all raw strings, including empty and invalid, retained in MMD/TV; color and parsed-word scores use original valid-only protocol',
         'jitter_word_baselines': 'not applicable; RGB-only egress perturbation does not change word completions',
         'source': 'Gao et al., ICLR 2025, equations 4,6,8; conditional prompt-stratified adaptation, not replication of their long-form benchmark',
         'null': 'labels exchangeable within each fixed prompt cell; independent permutations across cells; plus-one Monte Carlo p, reject p<=.05',
         'inference_scope': 'pairwise unadjusted p-values; observed rejection fractions on dependent model pairs, not independent-trial power or evidence of equivalence'})
    save(out/'baseline_subsets.json', subset_records)
    return rows, full_pairs
