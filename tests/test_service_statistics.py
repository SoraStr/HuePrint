"""Independent checks for offline routing arithmetic and budget accounting."""
import itertools
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import service_audit_analysis as sa


def row(rgb):
    return {'parsed': {'status': 'valid' if rgb is not None else 'invalid', 'rgb': rgb}}


def direct_score(a, b):
    # Separate explicit loops, not the vectorized production expression.
    x = [np.array(r['parsed']['rgb']) * 100 / 255 for r in a if r['parsed']['status'] == 'valid']
    y = [np.array(r['parsed']['rgb']) * 100 / 255 for r in b if r['parsed']['status'] == 'valid']
    if not x or not y:
        return None
    xy = sum(np.linalg.norm(u-v) for u in x for v in y) / (len(x)*len(y))
    xx = sum(np.linalg.norm(u-v) for u in x for v in x) / len(x)**2
    yy = sum(np.linalg.norm(u-v) for u in y for v in y) / len(y)**2
    return max(0., xy-(xx+yy)/2) / (xy+15)


class ServiceStatisticsTests(unittest.TestCase):
    def test_batch_matches_scalar_with_invalid_budget_slots(self):
        ref = [row([0, 20, 255]), row([80, 90, 100]), row(None)]
        genuine = [row([2, 22, 250]), row(None), row([78, 90, 102]), row([45, 45, 50])]
        fallback = [row([255, 0, 0]), row([190, 15, 3]), row(None), row([210, 20, 12])]
        og = np.array([[0, 1, 2], [3, 2, 0]])
        of = np.array([[2, 0, 3], [1, 2, 0]])
        uniforms = np.array([[.1, .45, .9], [.25, .55, .75]])
        scores, valid, counts = sa.batch_mixed_scores(ref, genuine, fallback, 3, og, of, uniforms)
        for s, pidx in itertools.product(range(2), range(len(sa.PROBS))):
            p = sa.PROBS[pidx]
            mixed = [genuine[og[s, j]] if uniforms[s, j] < p else fallback[of[s, j]] for j in range(3)]
            expected = direct_score(ref, mixed)
            self.assertEqual(valid[s, pidx], expected is not None)
            self.assertAlmostEqual(scores[s, pidx], expected, places=13)
            self.assertEqual(counts[s, pidx], sum(uniforms[s] >= p))
        self.assertTrue(np.all(counts[:, 0] == 3))
        self.assertTrue(np.all(counts[:, -1] == 0))

    def test_invalid_query_is_excluded_not_black(self):
        ref = [row([0, 0, 0]), row([0, 0, 0])]
        pool = [row(None), row(None)]
        scores, valid, counts = sa.batch_mixed_scores(ref, pool, pool, 2,
            np.array([[0, 1]]), np.array([[0, 1]]), np.array([[.3, .7]]))
        self.assertFalse(np.any(valid))
        self.assertTrue(np.all(np.isfinite(scores)))
        self.assertEqual(counts[0, 0], 2)

    def test_reference_missingness_and_constant_energy(self):
        x = [row([12, 34, 56]), row([12, 34, 56])]
        self.assertAlmostEqual(direct_score(x, x), 0.)
        score, valid, fallback = sa.batch_mixed_scores([row(None)], x, x, 2,
            np.array([[0, 1]]), np.array([[0, 1]]), np.array([[.3, .7]]))
        self.assertFalse(np.any(valid))
        self.assertEqual(fallback[0, 0], 2)
        self.assertEqual(fallback[0, -1], 0)

    def test_schedule_is_explicit_list_scheduling(self):
        self.assertAlmostEqual(sa.schedule_estimate([1000, 2000, 3000, 4000], 1), 10.)
        self.assertAlmostEqual(sa.schedule_estimate([1000, 2000, 3000, 4000], 2), 6.)
        self.assertAlmostEqual(sa.schedule_estimate([1000, 2000, 3000, 4000], 4), 4.)


if __name__ == '__main__':
    unittest.main()
