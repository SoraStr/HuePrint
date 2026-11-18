"""Regression checks for RGB-only collection, geometry, and archived input."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import analyze as an
from collect import parse_color_response
from reproduce_all import load_jsonl_clean, perturb_row_rgb, rgb_displacement
from extensions.live_validation_20261111 import lv_analyze as live


def sample(text, fmt="hex"):
    return {"parsed": parse_color_response(text, fmt)}


class RGBPipelineTests(unittest.TestCase):
    def test_parser_keeps_color_and_syntax_without_lab(self):
        for text, fmt, expected in (
            ("<think>#FFFFFF</think>#336699", "hex", [51, 102, 153]),
            ("(51, 102, 153)", "rgb_triplet", [51, 102, 153]),
            ("#000000", "hex", [0, 0, 0]),
            ("#FFFFFF", "hex", [255, 255, 255]),
        ):
            with self.subTest(text=text):
                p = parse_color_response(text, fmt)
                self.assertEqual(p["status"], "valid")
                self.assertEqual(p["rgb"], expected)
                self.assertEqual(p["parser_version"], "3.0")
                self.assertNotIn("lab", p)
        for text in ("256,0,0", "-1,0,0", "1,2", ""):
            self.assertNotEqual(parse_color_response(text, "rgb_triplet")["status"], "valid")

    def test_archived_lab_fields_cannot_affect_current_geometry(self):
        rows = [sample("#336699"), sample("#102030")]
        archived = copy.deepcopy(rows)
        for row in archived:
            row["parsed"].update(parser_version="2.1", lab=[float("nan"), 99999, -99999])
        clean_cell = an.summarize_cell_samples(rows)
        archived_cell = an.summarize_cell_samples(archived)
        np.testing.assert_array_equal(clean_cell["rgb_arr"], [[20, 40, 60], [1600/255, 3200/255, 4800/255]])
        np.testing.assert_array_equal(archived_cell["rgb_arr"], clean_cell["rgb_arr"])
        for score in an.compute_cell_distance(clean_cell, archived_cell).values():
            self.assertAlmostEqual(score, 0, places=6)

    def test_single_color_distances_have_rgb_units(self):
        a = an.summarize_cell_samples([sample("#000000")])
        b = an.summarize_cell_samples([sample("#FF0000")])
        d = an.compute_cell_distance(a, b)
        self.assertAlmostEqual(d["energy_raw"], math.sqrt(200))
        self.assertAlmostEqual(d["energy_norm"], 1)
        self.assertAlmostEqual(d["energy_reg"], 100/115)
        self.assertAlmostEqual(d["w2_raw"], 100)
        self.assertAlmostEqual(d["w2_norm"], 1-math.exp(-2))

    def test_boundary_jitter_updates_rgb_without_mutating_source(self):
        before = sample("#1F1F1F")
        before["parsed"]["lab"] = [999, 999, 999]
        original = copy.deepcopy(before)
        after = perturb_row_rgb(before, "directional_shift", 1, np.random.default_rng(1))
        self.assertEqual(before, original)
        self.assertEqual(after["parsed"]["rgb"], [32, 32, 32])
        self.assertEqual(after["parsed"]["canonical_hex"], "#202020")
        self.assertEqual(after["parsed"]["voxel_bin_8"], "1_1_1")
        self.assertNotIn("lab", after["parsed"])
        self.assertAlmostEqual(rgb_displacement(before, after), math.sqrt(3)*100/255)
        d = an.compute_cell_distance(an.summarize_cell_samples([before]), an.summarize_cell_samples([after]))
        self.assertEqual(d["hex_jsd"], 1)
        self.assertEqual(d["voxel_jsd"], 1)
        self.assertLess(d["soft_voxel_jsd"], 0.01)
        self.assertLess(d["energy_reg"], 0.05)

    def test_reparse_mixed_schema_and_deduplicate(self):
        rows = []
        for rep, version in ((1, "2.1"), (2, "3.0")):
            row = {"trial_key": str(rep), "target_id": "model", "task_id": "color",
                   "lang": "en", "format": "hex", "rep": rep, "temperature": 1.0,
                   "raw_text": "#336699", "parsed": {"parser_version": version, "lab": [999]*3}}
            rows.append(row)
        rows.append(copy.deepcopy(rows[0]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"trials.jsonl"
            path.write_text("".join(json.dumps(r)+"\n" for r in rows))
            original = path.read_bytes()
            loaded, lines, _ = load_jsonl_clean(str(path))
            self.assertEqual(lines, 3)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(path.read_bytes(), original)
            for row in loaded:
                self.assertEqual(row["parsed"]["rgb"], [51, 102, 153])
                self.assertEqual(row["parsed"]["parser_version"], "3.0")
                self.assertNotIn("lab", row["parsed"])

    def test_invalid_samples_do_not_enter_geometry(self):
        cell = an.summarize_cell_samples([sample("nonsense"), sample("")])
        self.assertEqual(cell["n_valid"], 0)
        self.assertEqual(cell["rgb_arr"].shape, (0, 3))
        self.assertTrue(all(math.isfinite(d) for d in an.compute_cell_distance(cell, cell).values()))

    def test_linear_eer_is_distinct_from_discrete_eer(self):
        roc = an.compute_roc_eer([0, 2], [1, 3, 4, 5])
        self.assertAlmostEqual(roc["eer_linear_raw"], 0.25)
        self.assertAlmostEqual(roc["eer_raw"], 0.375)

    def test_live_report_uses_the_linear_roc_intersection(self):
        tids = ["a", "b", "c"]
        cells = {t: {"probe": {"id": t}} for t in tids}
        scores = {(a, b): 3 for a in tids for b in tids}
        scores.update({("a", "a"): 0, ("b", "b"): 2, ("c", "c"): 2, ("a", "b"): 1})
        def distance(a, b):
            return {"energy_reg": scores[a["id"], b["id"]]}
        with patch.object(an, "compute_cell_distance", side_effect=distance):
            result = live.eval_verification_matrix(cells, cells, tids, metrics=["energy_reg"])["energy_reg"]
        self.assertEqual(result["eer_linear_pct"], 16.67)
        self.assertEqual(result["eer_discrete_pct"], 8.33)
        self.assertEqual(result["auc"], 0.888889)

    def test_live_rejects_thresholds_from_a_different_coordinate_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"old_thresholds.json"
            path.write_text(json.dumps({"analysis_protocol": {"color_space": "Lab"}}))
            with patch.object(live, "load_jsonl_clean", return_value=([], 0, "unused")):
                with self.assertRaisesRegex(ValueError, "different analysis protocol"):
                    live.analyze_s1_longitudinal_and_cross_gateway([], [], dev_summary_path=path)


if __name__ == "__main__":
    unittest.main()
