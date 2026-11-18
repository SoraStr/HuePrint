"""Supplementary table coverage from saved pair matrices (no new fitting)."""
import json
import numpy as np
import analyze as an
from .core import save, stats, operating


def weighted_roc(g, imp, wg, wi):
    gmask, imask = wg > 0, wi > 0
    g, imp, wg, wi = g[gmask], imp[imask], wg[gmask], wi[imask]
    pairs = wg[:, None]*wi[None, :]
    auc = np.sum(((g[:, None] < imp[None, :])+.5*(g[:, None] == imp[None, :]))*pairs)/pairs.sum()
    ts = np.unique(np.r_[g, imp])
    frr = np.r_[1., (wg[:, None]*(g[:, None] > ts)).sum(axis=0)/wg.sum()]
    far = np.r_[0., (wi[:, None]*(imp[:, None] <= ts)).sum(axis=0)/wi.sum()]
    diff = far-frr; k = int(np.flatnonzero(diff >= 0)[0])
    w = -diff[k-1]/(diff[k]-diff[k-1])
    return float(auc), float(far[k-1]+w*(far[k]-far[k-1]))


def bootstrap(mat, seed=20261111, repeats=2000):
    n = len(mat); mask = ~np.eye(n, dtype=bool); rng = np.random.default_rng(seed)
    vals = []; omitted = 0
    for _ in range(repeats):
        w = rng.multinomial(n, [1/n]*n); wi = (w[:, None]*w[None, :])[mask]
        if wi.sum() == 0:
            omitted += 1; continue
        vals.append(weighted_roc(np.diag(mat), mat[mask], w, wi))
    ar = np.array(vals)
    return {'auc_ci95': np.quantile(ar[:, 0], [.025, .975]).tolist(),
            'eer_ci95': np.quantile(ar[:, 1], [.025, .975]).tolist(),
            'point': stats(mat), 'clusters': n, 'seed': seed, 'requested': repeats,
            'retained': len(vals), 'omitted_one_identity': omitted}


def table_checks(out):
    comp = json.loads((out/'comparisons.json').read_text())
    scores = json.loads((out/'calibration_scores.json').read_text())
    fits = json.loads((out/'frozen_calibration.json').read_text())
    heldout = set(comp['E']['ids'])
    dev = set(fits['B3v3']['enrollment_ids'])
    result = {'cluster_bootstrap': {}, 'S1_subgroups': {}}
    for scenario in ('B_full', 'C_p1_within', 'C_p2_within', 'E', 'S1_CF0_CF21_6v6', 'S1_CF0_OR21_6v6'):
        entry = comp[scenario]; ix = [i for i, t in enumerate(entry['ids']) if not scenario.startswith('S1') or t in heldout]
        label = scenario+('_heldout4' if scenario.startswith('S1') else '')
        result['cluster_bootstrap'][label] = {m: bootstrap(np.array(entry['matrices'][m])[np.ix_(ix, ix)])
                                             for m in ('energy_norm', 'energy_reg', 'hybrid', 'hybrid_reg')}
    for scenario in ('S1_CF0_CF21', 'S1_CF21_OR21', 'S1_CF0_OR21'):
        for fit in ('B3v3', 'B6v6'):
            entry = scores[scenario+'@'+fit]
            for subset, tids in [('heldout4', heldout), ('dev10', dev)]:
                ix = [i for i, t in enumerate(entry['ids']) if t in tids]
                label = scenario+'@'+fit+'@'+subset
                result['S1_subgroups'][label] = {}
                for m in entry['matrices']:
                    for variant, params in fits[fit]['models'][m]['variants'].items():
                        mat = (np.array(entry['matrices'][m])-params['alpha']*np.array(entry['mu'][m]))[np.ix_(ix, ix)]
                        result['S1_subgroups'][label][m+'@'+variant] = {'metrics': stats(mat),
                            'tau_mid': operating(mat, params['tau_mid']), 'tau_u0': operating(mat, params['tau_u0'])}
    # Check cluster-weighted ROC against physically expanded samples.
    rng = np.random.default_rng(20261112)
    for _ in range(100):
        g = rng.integers(0, 6, 5); imp = rng.integers(0, 6, 8)
        wg = rng.integers(1, 5, 5); wi = rng.integers(1, 5, 8)
        a, e = weighted_roc(g, imp, wg, wi)
        oracle = an.compute_roc_eer(np.repeat(g, wg).tolist(), np.repeat(imp, wi).tolist())
        assert abs(a-oracle['auc_raw']) < 1e-12 and abs(e-oracle['eer_linear_raw']) < 1e-12
    result['weighted_roc_expanded_sample_checks'] = 100
    save(out/'table_checks.json', result)
    return result
