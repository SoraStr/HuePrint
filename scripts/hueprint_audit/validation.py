"""Independent numerical and artifact checks for the offline repair."""
from __future__ import annotations
import colorsys
import itertools
import json
import math
import numpy as np
import analyze as an
from .core import (ROOT, SEED, METRICS, SRGB_SEAM, XYZ_MATRIX, WHITE, LAB_MATRIX,
                   rgb100_to_lab, lab_lipschitz_bounds, permutation_p, energy_permutations)
from .baselines import categorical_permutations


def numerical_checks(scale=1.):
    rng = np.random.default_rng(SEED)
    bounds = lab_lipschitz_bounds(scale)
    x = rng.uniform(0, 100, (10000, 3)); y = rng.uniform(0, 100, (10000, 3))
    ratio = np.linalg.norm(scale*(rgb100_to_lab(x)-rgb100_to_lab(y)), axis=1)/np.linalg.norm(x-y, axis=1)
    assert ratio.min() >= bounds['L_min'] and ratio.max() <= bounds['L_max']
    d = 6/29
    f_seam_error = abs(d-(d**3/(3*d*d)+4/29))
    assert f_seam_error < 1e-14
    seam_error = abs(SRGB_SEAM/12.92-((SRGB_SEAM+.055)/1.055)**2.4)
    assert seam_error < 1e-16
    u = np.arange(256)/255
    standard = np.where(u <= .04045, u/12.92, ((u+.055)/1.055)**2.4)
    continuous = np.where(u <= SRGB_SEAM, u/12.92, ((u+.055)/1.055)**2.4)
    np.testing.assert_array_equal(standard, continuous)
    np.testing.assert_allclose(rgb100_to_lab([[0, 0, 0], [100, 100, 100]]), [[0, 0, 0], [100, 0, 0]], atol=1e-12)
    worst = 0.
    for _ in range(500):
        a, b = rng.uniform(0, 100, (5, 3)), rng.uniform(0, 100, (7, 3))
        pert = np.clip(b+rng.uniform(-.5, .5, b.shape), 0, 100)
        a1, b1, p1 = [scale*rgb100_to_lab(v) for v in (a, b, pert)]
        observed = abs(an.energy_distance_3d(a1, b1)[2]-an.energy_distance_3d(a1, p1)[2])
        eps = np.max(np.linalg.norm(b-pert, axis=1))
        bound = min(1., 2*bounds['L_max']*eps/15)
        assert observed <= bound+1e-12
        worst = max(worst, observed/max(bound, 1e-30))
    # Exact JSD and support membership after an injective, unrounded chart map.
    colors = np.unique(rng.integers(0, 256, (300, 3)), axis=0)
    lab = scale*rgb100_to_lab(colors*100/255)
    assert len({tuple(p) for p in lab}) == len(colors)
    p = {tuple(c): int(w) for c, w in zip(colors[:200], rng.integers(1, 10, 200))}
    q = {tuple(c): int(w) for c, w in zip(colors[100:], rng.integers(1, 10, len(colors)-100))}
    lookup = {tuple(c): tuple(l) for c, l in zip(colors, lab)}
    pt = {lookup[c]: w for c, w in p.items()}; qt = {lookup[c]: w for c, w in q.items()}
    assert abs(an.jsd_base2(p, q)-an.jsd_base2(pt, qt)) < 1e-12
    assert sum(w for c, w in q.items() if c not in p) == sum(w for c, w in qt.items() if c not in pt)
    # MMD U-statistic against direct off-diagonal equality kernels.
    xstr, ystr = ['a', 'a', 'b'], ['a', 'c', 'c']
    ka = np.array([[x == y for y in xstr] for x in xstr], dtype=float)
    kb = np.array([[x == y for y in ystr] for x in ystr], dtype=float)
    kab = np.array([[x == y for y in ystr] for x in xstr], dtype=float)
    oracle = (ka.sum()-np.trace(ka))/6+(kb.sum()-np.trace(kb))/6-2*kab.mean()
    actual = categorical_permutations(xstr, ystr, 99, SEED)
    assert abs(actual['string_mmd_u'][0]-oracle) < 1e-12
    assert abs(actual['string_tv'][0]-2/3) < 1e-12
    # Energy V test versus direct pair distances with unequal sample sizes.
    a, b = rng.uniform(size=(3, 3)), rng.uniform(size=(5, 3))
    direct = 2*np.linalg.norm(a[:, None]-b[None, :], axis=-1).mean()-np.linalg.norm(a[:, None]-a[None, :], axis=-1).mean()-np.linalg.norm(b[:, None]-b[None, :], axis=-1).mean()
    vals = energy_permutations(a, b, 99, SEED)
    assert abs(vals[0]-3*5/8*direct) < 1e-12
    assert permutation_p(np.ones(100)) == 1.
    assert permutation_p(np.r_[2., np.zeros(99)]) == .01
    # Exhaustive six-observation binary null, with exact conditional permutations:
    # the rejection fraction under each pooled composition is at most alpha.
    null_rates = []
    for successes in range(7):
        pool = np.r_[np.ones(successes), np.zeros(6-successes)]
        statistics = []
        for ix in itertools.combinations(range(6), 3):
            aa = pool[list(ix)]; bb = np.delete(pool, list(ix))
            pa, pb = aa.mean(), bb.mean()
            statistics.append(abs(pa-pb))
        stat = np.array(statistics)
        ps = np.mean(stat[None, :] >= stat[:, None]-1e-12, axis=1)
        rate = float(np.mean(ps <= .05)); null_rates.append(rate)
        assert rate <= .05+1e-12
    jac = np.column_stack([(rgb100_to_lab(np.array([50., 50., 50.])+np.eye(3)[i]*1e-4)-rgb100_to_lab(np.array([50., 50., 50.])-np.eye(3)[i]*1e-4))/(2e-4) for i in range(3)])
    sv = np.linalg.svd(jac, compute_uv=False)
    assert sv[0]/sv[-1] > 1.01
    hue_gap = abs(colorsys.rgb_to_hsv(.500001, .5, .5)[0]-colorsys.rgb_to_hsv(.5, .500001, .5)[0])
    assert abs(hue_gap-1/3) < 1e-12
    return {'certified_lab_bounds': bounds, 'random_pair_count': len(x),
            'sampled_length_ratio_min_max': [float(ratio.min()), float(ratio.max())],
            'stability_cloud_fixtures': 500, 'max_observed_over_certified_bound': worst,
            'continuous_seam_residual': seam_error,
            'rounded_IEC_seam_jump': ((.04045+.055)/1.055)**2.4-.04045/12.92,
            'all_256_channel_levels_identical_to_rounded_IEC': True,
            'gray_jacobian_singular_values_native_Lab': sv.tolist(),
            'gray_local_anisotropy': float(sv[0]/sv[-1]),
            'exact_categorical_null_type1_rates_by_composition': null_rates,
            'mmd_and_energy_independent_formula_checks': True,
            'jsd_and_support_escape_relabeling_checks': True,
            'hsv_hue_gap_at_rgb_separation_sqrt2_e_minus6': hue_gap,
            'scope': 'finite numerical fixtures corroborate the separate analytic proof; they do not prove a continuum-wide bound'}


def validate(out):
    comp = json.loads((out/'comparisons.json').read_text())
    frozen = json.loads((ROOT/'data/reproduce_all_rgb_summary.json').read_text())
    old = {'A_fresh': frozen['dataset_A_56models']['fresh_raw_only_no_legacy_meta']['roc_raw'],
           'A_legacy_reasoning_control': frozen['dataset_A_56models']['with_legacy_reasoning_meta']['roc_raw'],
           'B_full': frozen['dataset_B_40u15r']['roc_raw']}
    checked = 0
    for name, rocs in old.items():
        for m in METRICS:
            if m == 'hybrid_reg': continue
            for key, rk in [('auc', 'auc_raw'), ('eer', 'eer_linear_raw')]:
                assert abs(comp[name]['metrics'][m][key]-rocs[m][rk]) < 1e-10, (name, m, key)
                checked += 1
    fits = json.loads((out/'frozen_calibration.json').read_text())
    for m in ('energy_reg', 'hybrid', 'robust_manifold'):
        expected = frozen['dataset_E_heldout_confirmation']['frozen_transfer_from_dev_B'][m]['frozen_dev_midpoint_tau_raw']
        assert abs(fits['B3v3']['models'][m]['variants']['raw']['tau_mid']-expected) < 1e-12
    scores = json.loads((out/'calibration_scores.json').read_text())
    eids = set(scores['E_clean@B3v3']['ids'])
    assert not eids & set(fits['B3v3']['enrollment_ids'])
    assert set(fits['B3v3']['enrollment_ids']) == set(fits['B6v6']['enrollment_ids']) == set(fits['B8v7']['enrollment_ids'])
    for d in comp.values():
        if 'matrices' not in d: continue
        mats = {m: np.array(v) for m, v in d['matrices'].items()}
        np.testing.assert_allclose(mats['hybrid_reg'], mats['hybrid']+.25*(mats['energy_reg']-mats['energy_norm']), atol=1e-14)
    charts = json.loads((out/'color_spaces.json').read_text())
    b = json.loads((out/'baseline_results.json').read_text())
    configs = {(r['dataset'], r['n_total_per_cell'], r['K'], r['condition']) for r in b['results']}
    for dataset in ('S3_color', 'S3_word'):
        for n in (6, 10, 20, 30):
            for k in range(1, 11):
                assert (dataset, n, k, 'clean') in configs
                if dataset == 'S3_color': assert (dataset, n, k, 'jitter8') in configs
    for dataset in ('B20x6', 'D'):
        assert {r['n_total_per_cell'] for r in b['results'] if r['dataset'] == dataset} == {6}
    rows = json.loads((out/'calibration_results.json').read_text())['operating_points']
    # Same historical input ordering and jitter seeds reproduce the published FRR.
    for scenario, expected in [('E_clean', .30), ('E_jitter8', .51)]:
        subset = [r for r in rows if r['scenario'].startswith(scenario) and r['metric'] == 'energy_reg' and r['variant'] == 'raw' and r['threshold_kind'] == 'tau_mid']
        assert abs(np.mean([r['frr'] for r in subset])-expected) < 1e-12, scenario
    for label, fit in [('B_40x15', 'B8v7'), ('B_20x6', 'B3v3')]:
        for m in ('energy_reg', 'hybrid', 'robust_manifold'):
            expected = frozen['attack_suites'][label]['clean_thresholds'][m]['midpoint']
            assert abs(fits[fit]['models'][m]['variants']['raw']['tau_mid']-expected) < 1e-12
    for scenario, expected in [('Bfull_jitter15', .56), ('Bfull_routing0.5', 28/90)]:
        subset = [r for r in rows if r['scenario'].startswith(scenario) and r['metric'] == 'energy_reg' and r['variant'] == 'raw' and r['threshold_kind'] == 'tau_mid']
        assert abs(np.mean([r['frr' if 'jitter' in scenario else 'far'] for r in subset])-expected) < 1e-12, scenario
    budget = json.loads((out/'B_budget.json').read_text())['results']
    old_grid = frozen['dataset_B_40u15r']['grid_2d_n_by_k']['grid_hybrid']
    for row in budget:
        assert row['missing_pair_cells'] == 0
        if row['metric'] == 'hybrid':
            expected = old_grid[str(row['n_total_per_cell'])][str(row['K'])]['tie_stable_12dp_linear_eer_pct']
            assert round(100*row['eer_12dp'], 2) == expected
    return {'legacy_metric_fields_reproduced': checked, 'legacy_B3v3_thresholds_reproduced': True,
            'legacy_B_48_budget_cells_reproduced': True,
            'legacy_E_clean_and_jitter_FRR_reproduced': True,
            'legacy_redteam_thresholds_jitter15_and_routing_reproduced': True,
            'heldout_E_id_disjoint_from_B_calibration': True,
            'hybrid_reg_component_identity_verified': True,
            'budget_coverage_verified': True,
            'numerical': numerical_checks(charts['lab_scale']['scale'])}
