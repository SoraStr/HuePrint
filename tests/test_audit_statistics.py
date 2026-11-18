"""Tests for statistical formulas, leakage boundaries and color charts."""
import copy
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import analyze as an
from collect import parse_color_response
from hueprint_audit.core import (SEED, enrollment_mu, select_alpha_bcv,
    energy_permutations, permutation_p, rgb100_to_lab, rewrite_color_literal,
    group, thresholds)
from hueprint_audit.baselines import categorical_permutations
from hueprint_audit.validation import numerical_checks


def row(text, rep=1, target='a', fmt='hex'):
    return {'trial_key': f'{target}/{rep}', 'target_id': target, 'task_id': 'probe',
            'lang': 'en', 'format': fmt, 'rep': rep, 'temperature': 1.,
            'raw_text': text, 'parsed': parse_color_response(text, fmt)}


class AuditStatisticsTests(unittest.TestCase):
    def test_independent_numerical_oracles_and_chart_bounds(self):
        result = numerical_checks(.8)
        self.assertTrue(result['mmd_and_energy_independent_formula_checks'])

    def test_new_hybrid_preserves_composite_components(self):
        a = an.summarize_cell_samples([row('#000000')])
        b = an.summarize_cell_samples([row('#010000')])
        d = an.compute_cell_distance(a, b)
        self.assertAlmostEqual(d['hybrid'], .35*d['voxel_jsd']+.25*d['hex_jsd']+.25*d['energy_norm']+.15*d['side_jsd'])
        self.assertAlmostEqual(d['hybrid_reg'], d['hybrid']+.25*(d['energy_reg']-d['energy_norm']))
        self.assertLess(d['hybrid_reg'], d['hybrid'])
        # Regularizing energy does NOT remove the hybrid's exact-JSD jump.
        self.assertGreaterEqual(d['hybrid_reg'], .25)

    def test_bootstrap_depends_only_on_own_reference_and_repeats_exactly(self):
        ref = group([row('#000000', 1), row('#112233', 3), row('#445566', 5)])
        before = copy.deepcopy(ref)
        mu1, detail1 = enrollment_mu(ref, 3, 32)
        other = copy.deepcopy(ref)
        other['b'] = {'probe|en': [row('#FFFFFF', 1, 'b'), row('#EEEEEE', 3, 'b')]}
        mu2, detail2 = enrollment_mu(other, 3, 32)
        self.assertEqual(mu1['a'], mu2['a']); self.assertEqual(detail1['a'], detail2['a'])
        self.assertEqual((mu1, detail1), enrollment_mu(ref, 3, 32))
        self.assertEqual(before, ref)

    def test_cv_rule_and_threshold_tie_semantics(self):
        mat = np.full((5, 5), .8); np.fill_diagonal(mat, .1)
        alpha, trace = select_alpha_bcv(mat, np.full((5, 5), .05))
        self.assertEqual(alpha, 1.)
        self.assertTrue(all(r['cv_balanced_error'] == 0 for r in trace))
        self.assertLess(thresholds(mat)['tau_u0'], .8)
        self.assertEqual(float(np.nextafter(thresholds(mat)['tau_u0'], np.inf)), .8)

    def test_categorical_no_collisions_is_powerless_not_significant(self):
        values = categorical_permutations(['a', 'b', 'c'], ['d', 'e', 'f'], 99, SEED)
        np.testing.assert_array_equal(values['string_mmd_u'], 0.)
        np.testing.assert_allclose(values['string_tv'], 1.)
        self.assertEqual(permutation_p(values['string_mmd_u']), 1.)
        self.assertEqual(permutation_p(values['string_tv']), 1.)

    def test_permutation_repeats_exactly_and_handles_degenerate_clouds(self):
        a = np.zeros((3, 3)); b = np.ones((5, 3))
        np.testing.assert_array_equal(energy_permutations(a, b, 99, SEED), energy_permutations(a, b, 99, SEED))
        self.assertEqual(permutation_p(energy_permutations(a, a, 99, SEED)), 1.)
        self.assertGreaterEqual(permutation_p(energy_permutations(a, b, 99, SEED)), .01)

    def test_raw_perturbation_updates_literal_and_not_source(self):
        a = row('<think>ignore #000000</think>#Ab1234'); before = copy.deepcopy(a)
        b = copy.deepcopy(a); b['parsed']['rgb'] = [17, 34, 51]; b['parsed']['canonical_hex'] = '#112233'
        got = rewrite_color_literal(a, b)
        self.assertEqual(got['raw_text'], '<think>ignore #000000</think>#112233')
        self.assertEqual(parse_color_response(got['raw_text'], 'hex')['rgb'], [17, 34, 51])
        self.assertEqual(a, before)

    def test_ambiguous_bare_hex_is_retained_and_flagged(self):
        a = row('B0C4DE'); b = copy.deepcopy(a)
        b['parsed']['rgb'] = [171, 188, 219]; b['parsed']['canonical_hex'] = '#ABBCDB'
        got = rewrite_color_literal(a, b)
        self.assertEqual(got['raw_text'], 'ABBCDB')
        self.assertFalse(got['egress_raw_reparse_valid'])

    def test_original_within_cell_log_order_is_preserved(self):
        rs = [row('#000000', 5), row('#FFFFFF', 1), row('#000001', 3)]
        self.assertEqual([r['rep'] for r in group(rs)['a']['probe|en']], [5, 1, 3])


if __name__ == '__main__': unittest.main()
