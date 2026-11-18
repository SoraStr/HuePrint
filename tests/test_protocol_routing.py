"""Unit tests for protocol-audit, mixed-routing permutation, typographic, and Zenodo release invariants."""
from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path
import unittest
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import protocol_routing_analysis as pra


def make_row(rgb):
    return {"parsed": {"status": "valid" if rgb is not None else "invalid", "rgb": rgb}}


def scalar_vreg_score(ref_rows, qry_rows) -> float:
    x = [np.array(r["parsed"]["rgb"], dtype=float) * 100.0 / 255.0 for r in ref_rows if r["parsed"]["status"] == "valid"]
    y = [np.array(r["parsed"]["rgb"], dtype=float) * 100.0 / 255.0 for r in qry_rows if r["parsed"]["status"] == "valid"]
    xy = sum(float(np.linalg.norm(u - v)) for u in x for v in y) / (len(x) * len(y))
    xx = sum(float(np.linalg.norm(u - v)) for u in x for v in x) / (len(x) ** 2)
    yy = sum(float(np.linalg.norm(u - v)) for u in y for v in y) / (len(y) ** 2)
    return max(0.0, xy - 0.5 * (xx + yy)) / (xy + 15.0)


def scalar_cell_energy_stat(ref_rows, qry_rows) -> float:
    x = [np.array(r["parsed"]["rgb"], dtype=float) * 100.0 / 255.0 for r in ref_rows if r["parsed"]["status"] == "valid"]
    y = [np.array(r["parsed"]["rgb"], dtype=float) * 100.0 / 255.0 for r in qry_rows if r["parsed"]["status"] == "valid"]
    n, m = len(x), len(y)
    xy = sum(float(np.linalg.norm(u - v)) for u in x for v in y) / (n * m)
    xx = sum(float(np.linalg.norm(u - v)) for u in x for v in x) / (n * n)
    yy = sum(float(np.linalg.norm(u - v)) for u in y for v in y) / (m * m)
    return max(0.0, (n * m / (n + m)) * (2.0 * xy - xx - yy))


class ProtocolRoutingTests(unittest.TestCase):
    def test_cell_mixed_scores_and_perms_match_scalar_oracle(self):
        ref = [make_row([10, 20, 240]), make_row([12, 22, 238]), make_row([8, 18, 242])]
        gen = [make_row([11, 21, 241]), make_row([9, 19, 239]), make_row([13, 23, 237]), make_row([10, 20, 240])]
        fb = [make_row([245, 15, 10]), make_row([240, 10, 12]), make_row([250, 20, 8]), make_row([242, 12, 14])]
        n_seeds = len(pra.SEEDS)
        og = np.tile(np.array([[0, 1, 2]]), (n_seeds, 1))
        of = np.tile(np.array([[2, 0, 1]]), (n_seeds, 1))
        unif = np.tile(np.array([[0.15, 0.55, 0.85]]), (n_seeds, 1))
        ww_cache = {}
        vreg, perm_vals, valid_mask, fb_counts = pra.eval_mixed_cell_vreg_and_perm(
            ref, gen, fb, og, of, unif, ww_cache, "unit_proto", "cell_0"
        )
        self.assertTrue(np.all(valid_mask))
        for si, pi in itertools.product((0, 5, 19), range(len(pra.PROBS))):
            p = pra.PROBS[pi]
            mixed = [gen[og[si, j]] if unif[si, j] < p else fb[of[si, j]] for j in range(3)]
            self.assertAlmostEqual(float(vreg[si, pi]), scalar_vreg_score(ref, mixed), places=12)
            self.assertAlmostEqual(float(perm_vals[si, pi, 0]), scalar_cell_energy_stat(ref, mixed), places=11)
            self.assertEqual(int(fb_counts[si, pi]), sum(unif[si] >= p))

    def test_citation_first_appearance_order_and_typography(self):
        body = (ROOT / "paper" / "ieee" / "body.tex").read_text(encoding="utf-8")
        refs = (ROOT / "paper" / "ieee" / "references.tex").read_text(encoding="utf-8")
        main_tex = (ROOT / "paper" / "ieee" / "main.tex").read_text(encoding="utf-8")

        seen = []
        for match in re.finditer(r"\\cite\{([^}]+)\}", body):
            for key in match.group(1).split(","):
                num = int(re.fullmatch(r"ref(\d+)", key.strip()).group(1))
                if num not in seen:
                    seen.append(num)
        self.assertEqual(seen, list(range(1, 30)), f"Citations out of order: {seen}")

        self.assertRegex(main_tex, r"\\usepackage\{[^}]*\bcite\b[^}]*\}")
        non_math_body = re.sub(r"\$[^$]*\$|\\begin\{equation\}[\s\S]*?\\end\{equation\}|\\\[[\s\S]*?\\\]", "", body)
        self.assertIsNone(re.search(r"\[[1-9]\d*,\s*[1-9]\d*\]", non_math_body))
        self.assertNotIn(r"\resizebox{\columnwidth}{!}", body)
        self.assertNotIn("%[cite:", body)
        self.assertNotIn("%[cite:", refs)
        self.assertNotIn("''FrugalGPT", refs)
        self.assertIn("``FrugalGPT:", refs)
        self.assertIn(r"\texttt{-{}-brand-primary}", body)
        self.assertIn(r"\renewcommand{\rmdefault}{ppl}", main_tex)
        self.assertIn(r"\IEEEPARstart{A}{pplications}", body)
        self.assertIsNone(re.search(r"/\\allowbreak\s+(?!\{\})", body))

    def test_protocol_audit_consistency_with_manuscript_claims(self):
        analysis_dir = ROOT / "results" / "protocol_audit"
        t57 = json.loads((analysis_dir / "table5_vs_table7_cells.json").read_text(encoding="utf-8"))
        self.assertAlmostEqual(t57["table5_min_split_1"]["raw_V_clean_frr"], 0.30, places=6)
        self.assertAlmostEqual(t57["table7_min_split_2"]["raw_V_clean_frr"], 0.20, places=6)
        self.assertAlmostEqual(t57["table5_min_split_1"]["centered_V_jitter_frr"], 0.69, places=6)
        self.assertAlmostEqual(t57["table7_min_split_2"]["centered_V_jitter_frr"], 0.68, places=6)
        self.assertEqual(len(t57["dataset_E_cells_with_min_lt_2"]), 1)
        self.assertEqual(t57["dataset_E_cells_with_min_lt_2"][0]["target_id"], "gw-gemini-3.6-flash")
        self.assertEqual(t57["dataset_E_cells_with_min_lt_2"][0]["cell"], "rgb_warm|zh")

        rp = json.loads((analysis_dir / "routing_permutation.json").read_text(encoding="utf-8"))
        rows = {(r["protocol"], r["subgroup"], r["p_honest"]): r for r in rp["results"]}
        self.assertAlmostEqual(rows[("B40_q7", "all_distinct_labels", 0.8)]["perm_rejection_mean"] * 100.0, 33.28, places=2)
        self.assertAlmostEqual(rows[("B40_q7", "all_distinct_labels", 0.8)]["perm_genuine_frr_mean"] * 100.0, 0.00, places=2)
        self.assertAlmostEqual(rows[("B40_q7", "same_family", 0.8)]["perm_rejection_mean"] * 100.0, 25.75, places=2)
        self.assertAlmostEqual(rows[("S3_10_q7", "all_distinct_labels", 0.8)]["perm_rejection_mean"] * 100.0, 17.57, places=2)
        self.assertAlmostEqual(rows[("S3_10_q3", "all_distinct_labels", 0.8)]["perm_genuine_frr_mean"] * 100.0, 4.75, places=2)
        self.assertAlmostEqual(rows[("S1_CF0_OR21_20_q3", "all_distinct_labels", 0.8)]["perm_genuine_frr_mean"] * 100.0, 16.07, places=2)

        pa = json.loads((analysis_dir / "protocol_hyperparameter_audit.json").read_text(encoding="utf-8"))
        s1_sub = pa["s1_stratified"]
        self.assertAlmostEqual(
            s1_sub["CF21_OR21"]["standard_9_no_reasoning_override"]["perm_same_model_rejection_rate"] * 100.0,
            22.22,
            places=2,
        )
        self.assertAlmostEqual(
            s1_sub["CF0_OR21"]["standard_9_no_reasoning_override"]["perm_same_model_rejection_rate"] * 100.0,
            44.44,
            places=2,
        )
        self.assertAlmostEqual(
            pa["s3_provider_and_cost_audit"]["scenario_G_query_usd_quantiles"]["max_all_20"],
            0.2711,
            places=4,
        )

    def test_zenodo_bundle_hygiene_and_supplement_portability(self):
        self.assertTrue((ROOT / ".zenodo.json").is_file())
        self.assertTrue((ROOT / "CITATION.cff").is_file())
        self.assertTrue((ROOT / "LICENSE").is_file())
        self.assertNotIn(r"\mathsf", (ROOT / "paper" / "ieee" / "main.tex").read_text(encoding="utf-8"))

        supp_tex = (ROOT / "paper" / "supplement" / "main.tex").read_text(encoding="utf-8")
        self.assertIn(r"\IfFileExists{/System/Library/Fonts/STHeiti Medium.ttc}", supp_tex)
        self.assertIn(r"Noto Sans CJK SC", supp_tex)
        self.assertIn(r"Noto Naskh Arabic", supp_tex)

        zenodo_dir = ROOT / "zenodo_release"
        zip_path = zenodo_dir / "HuePrint_Replication_Package.zip"
        if zenodo_dir.is_dir():
            self.assertTrue((zenodo_dir / "HuePrint_Preprint.pdf").is_file())
            self.assertTrue((zenodo_dir / "HuePrint_Main_Manuscript.pdf").is_file())
            self.assertTrue((zenodo_dir / "HuePrint_Supplementary_Material.pdf").is_file())
            self.assertTrue(zip_path.is_file())
            with zipfile.ZipFile(zip_path) as zf:
                names = set(zf.namelist())
                for req in (
                    "HuePrint/.zenodo.json",
                    "HuePrint/CITATION.cff",
                    "HuePrint/LICENSE",
                    "HuePrint/paper/ieee/main.tex",
                    "HuePrint/paper/ieee/body.tex",
                    "HuePrint/paper/ieee/references.tex",
                    "HuePrint/paper/ieee/biography.tex",
                    "HuePrint/paper/ieee/IEEEtran.cls",
                    "HuePrint/figs/fig3_stability_bounds.pdf",
                    "HuePrint/figs/fig6_mixed_routing.pdf",
                ):
                    self.assertIn(req, names)
                for info in zf.infolist():
                    self.assertEqual(info.date_time, (2026, 11, 18, 0, 0, 0))
                    self.assertEqual(info.extra, b"")
                    self.assertNotIn(".git/", info.filename)
                    self.assertNotEqual(info.filename, "HuePrint/tools/tectonic")
                    self.assertFalse(info.filename.endswith(".log"))


if __name__ == "__main__":
    unittest.main()
