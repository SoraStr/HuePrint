"""Shared deterministic scoring, enrollment calibration and conditional tests."""
from __future__ import annotations

import collections
import hashlib
import itertools
import json
import re
from pathlib import Path

import numpy as np

import analyze as an
from collect import HEX_RE, parse_color_response
from reproduce_all import load_jsonl_clean, perturb_row_rgb

ROOT = Path(__file__).resolve().parents[2]
SEED = 20261112
JITTER_SEEDS = tuple(range(20261021, 20261031))
METRICS = ('hex_jsd', 'voxel_jsd', 'soft_voxel_jsd', 'energy_norm',
           'energy_reg', 'hybrid', 'hybrid_reg', 'robust_manifold', 'side_jsd')
CAL_METRICS = ('energy_reg', 'hybrid', 'hybrid_reg', 'robust_manifold')
SRGB_SEAM = 0.0404482362771082  # Larger root of u/12.92=((u+.055)/1.055)^2.4.
XYZ_MATRIX = np.array([[506752/1228815, 87881/245763, 12673/70218],
                       [87098/409605, 175762/245763, 12673/175545],
                       [7918/409605, 87881/737289, 1001167/1053270]])
WHITE = XYZ_MATRIX @ np.ones(3)
LAB_MATRIX = np.array([[0., 116., 0.], [500., -500., 0.], [0., 200., -200.]])


def seed_for(*parts):
    return int.from_bytes(hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).digest()[:8], 'little')


def load(path):
    return load_jsonl_clean(str(path))[0]


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n')


def rgb100_to_lab(x):
    """Continuous-seam sRGB -> D65-relative CIELAB; no Bradford/D50 adaptation."""
    u = np.asarray(x, dtype=float)/100.
    if np.any(u < -1e-12) or np.any(u > 1+1e-12):
        raise ValueError('RGB100 coordinates outside the cube')
    linear = np.where(u <= SRGB_SEAM, u/12.92, ((u+.055)/1.055)**2.4)
    xyz = (linear @ XYZ_MATRIX.T)/WHITE
    d = 6/29
    f = np.where(xyz <= d**3, xyz/(3*d*d)+4/29, np.cbrt(xyz))
    return f @ LAB_MATRIX.T + np.array([-16., 0., 0.])


def lab_lipschitz_bounds(scale=1.):
    c = XYZ_MATRIX/WHITE[:, None]
    a_s = np.linalg.svd(LAB_MATRIX, compute_uv=False)
    c_s = np.linalg.svd(c, compute_uv=False)
    return {'L_min': float(scale*a_s[-1]*c_s[-1]/(3*12.92*100)),
            'L_max': float(scale*a_s[0]*c_s[0]*(29/6)**2/3*(2.4/1.055)/100)}


def group(rows, target_map=None, task_map=None):
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        if abs(float(r.get('temperature', 1.))-1.) > 1e-4:
            continue
        tid = (target_map or {}).get(r['target_id'], r['target_id'])
        task = (task_map or {}).get(r['task_id'], r['task_id'])
        out[tid][f"{task}|{r['lang']}"].append(r)
    # Keep saved within-cell order: historical jitter seeds were assigned in
    # that order, including retries that occur later in the immutable log.
    return {t: {c: rs for c, rs in sorted(cs.items())}
            for t, cs in sorted(out.items())}


def split(rows):
    return group([r for r in rows if r['rep'] % 2]), group([r for r in rows if not r['rep'] % 2])


def summarize(g):
    return {t: {c: an.summarize_cell_samples(rs) for c, rs in cs.items()} for t, cs in g.items()}


def cell_scores(a, b):
    """Use the canonical implementation, including legacy edge conventions."""
    d = an.compute_cell_distance(a, b)
    return {m: d[m] for m in METRICS}


def matrix(a, b, lab_scale=None):
    aa, bb = summarize(a), summarize(b)
    ids = sorted(set(aa) & set(bb))
    mats = {m: np.zeros((len(ids), len(ids))) for m in METRICS}
    if lab_scale is not None:
        mats['energy_reg_lab'] = np.zeros((len(ids), len(ids)))
        al = {t: {c: lab_scale*rgb100_to_lab(s['rgb_arr']) for c, s in cs.items()} for t, cs in aa.items()}
        bl = {t: {c: lab_scale*rgb100_to_lab(s['rgb_arr']) for c, s in cs.items()} for t, cs in bb.items()}
    counts = np.zeros((len(ids), len(ids)), dtype=int)
    for i, t in enumerate(ids):
        for j, u in enumerate(ids):
            cells = sorted(set(aa[t]) & set(bb[u]))
            cells = [c for c in cells if aa[t][c]['n_valid'] and bb[u][c]['n_valid']]
            if not cells:
                raise ValueError(f'No valid shared cells: {t}, {u}')
            counts[i, j] = len(cells)
            vals = [cell_scores(aa[t][c], bb[u][c]) for c in cells]
            for m in METRICS:
                # Preserve canonical Python summation order. Pairwise numpy
                # reductions can split exact ties in saturated discrete JSD.
                mats[m][i, j] = sum(v[m] for v in vals)/len(vals)
            if lab_scale is not None:
                mats['energy_reg_lab'][i, j] = sum(an.energy_distance_3d(al[t][c], bl[u][c])[2] for c in cells)/len(cells)
    return ids, mats, counts


def stats(mat, positive=None, negative=None):
    mat = np.asarray(mat)
    positive = np.eye(len(mat), dtype=bool) if positive is None else positive
    negative = ~positive if negative is None else negative
    g, i = mat[positive], mat[negative]
    if not len(g) or not len(i):
        raise ValueError('ROC needs both classes')
    r = an.compute_roc_eer(g.tolist(), i.tolist())
    return {'auc': r['auc_raw'], 'eer': r['eer_linear_raw'], 'eer_discrete': r['eer_raw'],
            'n_genuine': len(g), 'n_impostor': len(i), 'genuine_mean': float(g.mean()),
            'impostor_mean': float(i.mean()), 'top1': float(np.mean(np.argmin(mat, axis=0) == np.arange(len(mat))))}


def thresholds(mat):
    g = np.diag(mat); i = mat[~np.eye(len(mat), dtype=bool)]
    return {'tau_mid': float(.5*g.max()+.5*i.min()),
            'tau_u0': float(np.nextafter(i.min(), -np.inf))}


def operating(mat, tau):
    g = np.diag(mat); i = mat[~np.eye(len(mat), dtype=bool)]
    return {'frr': float(np.mean(g > tau)), 'far': float(np.mean(i <= tau)),
            'false_rejects': int(np.sum(g > tau)), 'false_accepts': int(np.sum(i <= tau)),
            'n_genuine': len(g), 'n_impostor': len(i)}


def jitter_group(g, amplitude=8, seed=SEED, mode='uniform_jitter', raw=False):
    rng = np.random.default_rng(seed)
    out = {}
    for t, cs in sorted(g.items()):
        out[t] = {}
        for c, rows in sorted(cs.items()):
            out[t][c] = []
            for row in rows:
                r = perturb_row_rgb(row, mode, amplitude, rng)
                if raw and r['parsed']['rgb'] != row['parsed']['rgb']:
                    r = rewrite_color_literal(row, r)
                out[t][c].append(r)
    return out


def rewrite_color_literal(old, new):
    """Modify only the parsed color span in a raw completion, in memory."""
    p = old['parsed']; text = old.get('raw_text') or ''; visible = p['visible_text']
    offset = text.rfind(visible)
    if offset < 0:
        raise ValueError('Cannot locate visible response in raw text')
    rgb = new['parsed']['rgb']
    if old['format'] == 'hex':
        candidates = [m for m in HEX_RE.finditer(visible) if '#'+m.group(2).upper() == p['canonical_hex']]
        if not candidates:
            raise ValueError('Cannot locate parsed hex span')
        match = candidates[0]
        digits = ''.join(f'{v:02X}' for v in rgb)
        old_digits = match.group(2)
        if old_digits.lower() == old_digits:
            digits = digits.lower()
        else:
            digits = ''.join(ch.lower() if oc.islower() else ch for ch, oc in zip(digits, old_digits))
        start, end = match.span(2)
        replacement = digits
    elif old['format'] == 'rgb_triplet':
        match = re.search(r'(\d{1,3})(\s*,\s*)(\d{1,3})(\s*,\s*)(\d{1,3})', visible)
        if not match:
            raise ValueError('Cannot locate parsed RGB span')
        start, end = match.span()
        replacement = f'{rgb[0]}{match.group(2)}{rgb[1]}{match.group(4)}{rgb[2]}'
    else:
        raise ValueError('RGB perturbation is undefined for word completions')
    raw_text = text[:offset+start]+replacement+text[offset+end:]
    parsed = parse_color_response(raw_text, old['format'], old.get('explicit_reasoning', ''))
    # A bare hex token can become six letters after jitter. The existing parser
    # intentionally rejects it as ambiguous with a word. Retain the actual raw
    # text and flag this, while color scoring follows the original parsed-color
    # egress experiment (its injected RGB value is known).
    ambiguous = old['format'] == 'hex' and not p['syntax']['has_hash'] and replacement.isalpha()
    if parsed['rgb'] != rgb and not ambiguous:
        raise AssertionError('Perturbed raw string and RGB geometry disagree')
    # Preserve the original side-channel metadata to isolate color egress effects,
    # exactly as in the original red-team protocol. Raw-string tests see new text.
    return dict(new, raw_text=raw_text, egress_raw_reparse_valid=parsed['status'] == 'valid')


def enrollment_mu(ref, planned_query_n, repeats=256):
    """Matched-size plug-in bootstrap, using enrollment ONLY; not query values.

    Both bootstrap draws are independent samples from each enrollment empirical
    distribution. Sampling with replacement can underestimate unseen diversity.
    planned_query_n is a protocol constant, never inferred from test outcomes.
    """
    result = {}; cell_details = {}
    for tid, cells in sorted(ref.items()):
        cell_details[tid] = {}
        for ck, rows in sorted(cells.items()):
            valid = [r for r in rows if r['parsed']['status'] == 'valid']
            if not valid:
                continue
            n = len(valid)
            signature = [(r['trial_key'], r['parsed'], r.get('usage')) for r in valid]
            rng = np.random.default_rng(seed_for('enrollment-bootstrap', SEED, signature, planned_query_n))
            values = {m: [] for m in CAL_METRICS}
            cache = {}
            def summary(ix):
                key = tuple(sorted(ix))
                if key not in cache:
                    cache[key] = an.summarize_cell_samples([valid[k] for k in key])
                return cache[key]
            # Deterministic cells require no random work, but side channels may vary.
            for _ in range(repeats):
                aa = summary(rng.integers(n, size=n))
                bb = summary(rng.integers(n, size=planned_query_n))
                d = cell_scores(aa, bb)
                for m in CAL_METRICS:
                    values[m].append(d[m])
            cell_details[tid][ck] = {m: {'mu': float(np.mean(v)), 'mc_se': float(np.std(v, ddof=1)/np.sqrt(repeats))}
                                     for m, v in values.items()}
        result[tid] = {m: float(np.mean([v[m]['mu'] for v in cell_details[tid].values()])) for m in CAL_METRICS}
    return result, cell_details


def mu_for_matrix(ref, query, ids, details, metric):
    """Average enrollment baselines over the same valid cells as the score."""
    aa, bb = summarize(ref), summarize(query)
    mu = np.zeros((len(ids), len(ids)))
    for i, t in enumerate(ids):
        for j, u in enumerate(ids):
            cells = [c for c in sorted(set(aa[t]) & set(bb[u])) if aa[t][c]['n_valid'] and bb[u][c]['n_valid']]
            mu[i, j] = np.mean([details[t][c][metric]['mu'] for c in cells])
    return mu


def select_alpha_bcv(mat, mu):
    """Leave-one-identity-out B CV; thresholds never see the held-out identity."""
    records = []
    for alpha in (0., .25, .5, 1., 1.5, 2.):
        adjusted = mat-alpha*mu
        fold = []
        for hold in range(len(mat)):
            train = [j for j in range(len(mat)) if j != hold]
            tau = thresholds(adjusted[np.ix_(train, train)])['tau_mid']
            g = adjusted[hold, hold]
            negatives = np.r_[adjusted[hold, train], adjusted[train, hold]]
            fold.append(.5*(float(g > tau)+float(np.mean(negatives <= tau))))
        records.append({'alpha': alpha, 'cv_balanced_error': float(np.mean(fold)), 'fold_errors': fold})
    best = min(records, key=lambda r: (r['cv_balanced_error'], abs(r['alpha']-1), r['alpha']))
    return best['alpha'], records


def permutation_weights(n, m, count, rng):
    """Row zero is observed; remaining rows are independent uniform relabelings."""
    mask = np.zeros((count+1, n+m), dtype=float)
    mask[0, :n] = 1.
    order = np.argsort(rng.random((count, n+m)), axis=1)
    mask[np.arange(1, count+1)[:, None], order[:, :n]] = 1.
    return mask


def energy_permutations(x, y, count, seed):
    n, m = len(x), len(y)
    if not n or not m:
        raise ValueError('Energy test requires nonempty cells')
    points = np.concatenate([x, y])
    dist = np.linalg.norm(points[:, None, :]-points[None, :, :], axis=-1)
    mask = permutation_weights(n, m, count, np.random.default_rng(seed))
    weights = mask/n-(1-mask)/m
    # Classical V-statistic energy test: nm/(n+m) * (2dXY-dXX-dYY).
    vals = -np.einsum('bi,ij,bj->b', weights, dist, weights, optimize=True)*n*m/(n+m)
    return np.maximum(vals, 0.)


def permutation_p(values):
    values = np.asarray(values)
    tol = 1e-12*np.maximum(1., np.abs(values[..., :1]))
    return (1+np.sum(values[..., 1:] >= values[..., :1]-tol, axis=-1))/values.shape[-1]


def energy_test_matrix(ref, query, count=999):
    aa, bb = summarize(ref), summarize(query)
    ids = sorted(set(aa) & set(bb)); n = len(ids)
    statistic = np.zeros((n, n)); pval = np.zeros((n, n))
    for i, t in enumerate(ids):
        for j, u in enumerate(ids):
            vals = []
            for ck in sorted(set(aa[t]) & set(bb[u])):
                x, y = aa[t][ck]['rgb_arr'], bb[u][ck]['rgb_arr']
                if len(x) and len(y):
                    vals.append(energy_permutations(x, y, count, seed_for('energy-permutation', SEED, t, u, ck, len(x), len(y))))
            total = np.mean(vals, axis=0)
            statistic[i, j] = total[0]; pval[i, j] = permutation_p(total)
    return ids, statistic, pval


def pvalue_stats(p):
    # Rejection at p<=.05; a non-rejection is NOT a certificate of equality.
    diag = np.eye(len(p), dtype=bool)
    return {'same_model_rejection_rate': float(np.mean(p[diag] <= .05)),
            'different_model_rejection_rate': float(np.mean(p[~diag] <= .05)),
            'different_model_nonrejection_rate': float(np.mean(p[~diag] > .05)),
            'p_score_roc': stats(1-p)}
