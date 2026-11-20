"""Unit tests for manuscript integrity, exact rational MMD-U, corpus hygiene, and release readiness."""
from __future__ import annotations

from fractions import Fraction
import json
import random
import re
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from hueprint_audit.baselines import exact_mmd_roc_eer, exact_mmd_u_cell


class ManuscriptIntegrityTests(unittest.TestCase):
    def test_subset_mmd_diagnostics_and_s3_truncation_audit(self):
        diag = json.loads(
            (ROOT / "results" / "diagnostics" / "subset_mmd_diagnostics.json").read_text(encoding="utf-8")
        )
        self.assertEqual(diag["protected_files_verified"], 58)
        trunc = diag["s3_truncation_audit"]
        self.assertEqual(trunc["total_calls"], 12000)
        self.assertEqual(trunc["total_valid_parsed"], 11985)
        self.assertEqual(trunc["total_length_limit_count"], 3)
        self.assertEqual(trunc["total_length_limit_valid_parsed"], 1)
        self.assertEqual([r["line"] for r in trunc["arms"]["S3_color"]["length_limit_records"]], [1847, 3774])
        self.assertEqual([r["line"] for r in trunc["arms"]["S3_word"]["length_limit_records"]], [602])

        k10 = diag["b20x6_vs_d_budget_reconciliation"]["k10_40subsets_30calls_per_side"]
        self.assertAlmostEqual(k10["B20x6_color_mmd_u"]["eer"], 0.009361111111111112, places=12)
        self.assertAlmostEqual(k10["D_word_mmd_u"]["eer"], 0.04516919191919192, places=12)

        k20 = diag["b20x6_vs_d_budget_reconciliation"]["k20_full_battery_60calls_per_side"]
        self.assertEqual(k20["B20x6"]["raw_mmd_u"]["eer"], 0.0)
        self.assertEqual(k20["D"]["raw_mmd_u"]["eer"], 0.0)
        self.assertAlmostEqual(k20["D"]["canonical_jsd"]["eer"], 1.0 / 90.0, places=9)

        s3 = diag["s3_canonical_vs_raw_decontamination"]
        self.assertAlmostEqual(s3["N=6"]["S3_color"]["raw_mmd_u"]["eer"], 3.0 / 86.0, places=12)
        self.assertAlmostEqual(s3["N=6"]["S3_word"]["raw_mmd_u"]["eer"], 0.08043478260869566, places=12)
        self.assertAlmostEqual(s3["N=6"]["S3_color"]["canonical_mmd_u"]["eer"], 0.05, places=9)
        self.assertAlmostEqual(s3["N=6"]["S3_word"]["canonical_mmd_u"]["eer"], 27.0 / 290.0, places=12)
        self.assertEqual(s3["N=30"]["S3_color"]["raw_mmd_u"]["eer"], 0.0)
        self.assertAlmostEqual(s3["N=30"]["S3_word"]["raw_mmd_u"]["eer"], 5.0 / 380.0, places=12)
        self.assertEqual(s3["N=30"]["S3_color"]["canonical_mmd_u"]["eer"], 0.0)
        self.assertAlmostEqual(s3["N=30"]["S3_word"]["canonical_mmd_u"]["eer"], 2.0 / 380.0, places=9)

    def test_exact_mmd_u_distinct_count_combinations_tie_and_order_invariance(self):
        c_zero_1 = exact_mmd_u_cell(["A", "A", "A"], ["A", "A", "B"])
        c_zero_2 = exact_mmd_u_cell(["A", "B", "C"], ["D", "E", "F"])
        self.assertEqual(c_zero_1, Fraction(0, 1))
        self.assertEqual(c_zero_2, Fraction(0, 1))

        u_1 = exact_mmd_u_cell(["A", "A", "B", "C"], ["A", "D", "E"])
        u_2 = exact_mmd_u_cell(["A", "A", "A", "B"], ["A", "A", "C"])
        self.assertEqual(u_1, Fraction(-1, 6))
        self.assertEqual(u_2, Fraction(-1, 6))

        combo_a = (
            exact_mmd_u_cell(["A", "A", "B"], ["A", "C", "D"])
            + exact_mmd_u_cell(["A", "A", "B"], ["C", "C", "D"])
            + exact_mmd_u_cell(["A", "A", "B"], ["A", "B", "B"])
        ) / 3
        combo_b = (
            exact_mmd_u_cell(["A", "A", "B"], ["D", "E", "F"])
            + c_zero_1
            + c_zero_2
        ) / 3
        f_a = ((-1.0 / 9.0) + (2.0 / 3.0) + (-2.0 / 9.0)) / 3.0
        f_b = ((1.0 / 3.0) + 0.0 + 0.0) / 3.0
        self.assertNotEqual(f_a, f_b)
        self.assertEqual(combo_a, Fraction(1, 9))
        self.assertEqual(combo_b, Fraction(1, 9))

        genuine = [Fraction(0, 1), combo_a, combo_b, Fraction(2, 9)]
        impostor = [combo_b, combo_a, Fraction(1, 3), Fraction(1, 2)]
        base_roc = exact_mmd_roc_eer(genuine, impostor)
        self.assertEqual(base_roc["n_threshold_groups"], 5)

        rng = random.Random(20261118)
        for _ in range(100):
            g_perm = list(genuine)
            i_perm = list(impostor)
            rng.shuffle(g_perm)
            rng.shuffle(i_perm)
            perm_roc = exact_mmd_roc_eer(g_perm, i_perm)
            self.assertEqual(perm_roc["n_threshold_groups"], 5)
            self.assertEqual(perm_roc["auc"], base_roc["auc"])
            self.assertEqual(perm_roc["eer"], base_roc["eer"])
            self.assertEqual(perm_roc["eer_discrete"], base_roc["eer_discrete"])

    def test_titles_hueprint_intro_and_table3_disclosures(self):
        en_ms = (ROOT / "paper" / "MANUSCRIPT_EN.md").read_text(encoding="utf-8")
        zh_ms = (ROOT / "paper" / "MANUSCRIPT_ZH.md").read_text(encoding="utf-8")
        en_supp = (ROOT / "paper" / "SUPPLEMENT_EN.md").read_text(encoding="utf-8")

        self.assertTrue(
            en_ms.startswith("# Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services\n")
        )
        self.assertTrue(
            en_supp.startswith(
                '# Supplementary Material for "Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services"\n'
            )
        )
        self.assertIn("We present HuePrint, a black-box framework that audits brokered endpoint consistency", en_ms)
        self.assertIn(
            "In this paper, we introduce HuePrint, a lightweight black-box consistency signal for brokered LLM endpoints.",
            en_ms,
        )

        for needle in (
            "| 6 | Color MMD-U | 25.32% | 10.03% | 3.49% | 50.01% |",
            "| 6 | Color $D_{\\mathrm{hex}}$ |",
            "| 6 | Word MMD-U | 32.14% | 14.87% | 8.04% | — |",
            "| 6 | Word JSD |",
            "| 30 | Color $D_{\\mathrm{hex}}$ |",
            "1.11% Word JSD",
            "4.52–5.23 to 0.94–1.00 percent",
            "3.49–5.00 percent across 20 locked endpoints",
            "5.36 vs. 10.71 percent",
            "relative to LLMmap, it also avoids safety-triggering probes and runs over 15,000 times faster locally",
            "Sections 3.4–3.5",
            r"3v3: 19.78\%",
            "Matched 15v15 parity benchmark against Bruckner with a 64-token cap",
            "Three of 12,000 S3 responses reached the length limit",
            "controlled numerical continuity stress test",
            r"eight-query multi-token classifiers~\cite{ref16}",
            "Provider-side watermarks, instructional backdoors, and IP ownership fingerprints [11]–[13]",
            "38,688",
            "34.39% within-family EER",
            "4,701.9 ms",
            "95% q1",
            "pp. 3663–3678, 2022.",
            "J. Kleinberg and M. Raghavan,",
        ):
            self.assertIn(needle, en_ms)
        for supp_needle in (
            "| 6 | Color MMD-U | 25.32% | 16.99% | 10.03% | 6.58% | 4.95% | 3.49% | 50.01% |",
            "| 6 | Word MMD-U | 32.14% | 22.81% | 14.87% | 10.99% | 8.34% | 8.04% | — |",
            "TABLE S8: Complete Study S3 Matched-Budget",
            "TABLE S9: Matched V/U Comparison on E; FAR Is Zero Throughout",
            "TABLE S10: Median Per-Endpoint Query Overhead",
            "TABLE S11: B 40×15 Post-Processing EER",
            "TABLE S12a: Twenty-Seed Mixed-Routing Detection",
            "TABLE S12b: Private Prompt-Pool Subsampling",
            "TABLE S13: Study S5 Mixed-Routing Detection",
            "TABLE S14: Study S5 Nine-Day Longitudinal OpenRouter Transfer",
        ):
            self.assertIn(supp_needle, en_supp)
        supp_table_nums = re.findall(r"^\*\*TABLE (S\d+[ab]?):", en_supp, flags=re.M)
        self.assertEqual(
            supp_table_nums,
            ["S1", "S2", "S3", "S4a", "S4b", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12a", "S12b", "S13", "S14"],
        )
        self.assertNotIn("reviewer_defense", en_ms)
        self.assertNotIn("reviewer_defense", en_supp)
        self.assertNotIn("reviewer_defense", zh_ms)
        self.assertNotIn("reviewer_defense", (ROOT / "paper" / "SUPPLEMENT_ZH.md").read_text(encoding="utf-8"))
        supp_main_tex = (ROOT / "paper" / "supplement" / "main.tex").read_text(encoding="utf-8")
        self.assertIn("References ([4], [16], [24]--[29] match main manuscript; [30]--[34] supplement-only)", supp_main_tex)
        self.assertNotIn("Zero-truncation", en_ms)
        self.assertNotIn("3663-36 2022", en_ms)
        self.assertNotIn("and and", en_ms)
        self.assertNotIn("4.47", en_ms)
        self.assertNotIn("4.47", zh_ms)
        self.assertNotIn("(Section 2.2)", en_ms)
        self.assertNotIn("见第 2.2 节", zh_ms)
        self.assertIn("3.49%–5.00%", zh_ms)
        self.assertIn("受控数值连续性压力测试", zh_ms)
        self.assertIn("3 条触及长度上限", zh_ms)
        self.assertIn("subset_mmd_diagnostics.json", en_supp)
        self.assertIn("finite-cluster resampling", en_supp)
        self.assertNotIn("52.71%", en_supp)
        self.assertNotIn("97.32%", en_supp)
        self.assertIn(r"\section*{Acknowledgments}", en_ms)
        self.assertNotIn("Vicky Li", en_ms)
        self.assertIn("Siqi Li", en_ms)
        self.assertIn("## 致谢", zh_ms)
        self.assertNotIn("Vicky Li", zh_ms)
        self.assertIn("Siqi Li", zh_ms)
        self.assertIn("5.18 percent within-family EER", en_ms)
        self.assertIn("14 to 1 across 100 same-label windows", en_ms)
        self.assertNotIn("0.00–5.26 percent", en_ms)
        self.assertNotIn("97.32%", en_ms)
        self.assertNotIn("15-rep reference", en_supp)
        self.assertNotIn("15 次重复参考", (ROOT / "paper" / "SUPPLEMENT_ZH.md").read_text(encoding="utf-8"))
        self.assertIn("across-split dispersion", en_supp)
        author_tex = (ROOT / "paper" / "direct_replacements" / "author.tex").read_text(encoding="utf-8")
        self.assertIn("Siqi~Li", author_tex)
        self.assertIn("lisiqi-vicky@foxmail.com", author_tex)
        self.assertIn("0009-0000-9194-7563", author_tex)

    def test_propositions_and_clean_supplement(self):
        en_ms = (ROOT / "paper" / "MANUSCRIPT_EN.md").read_text(encoding="utf-8")
        zh_ms = (ROOT / "paper" / "MANUSCRIPT_ZH.md").read_text(encoding="utf-8")
        en_supp = (ROOT / "paper" / "SUPPLEMENT_EN.md").read_text(encoding="utf-8")
        zh_supp = (ROOT / "paper" / "SUPPLEMENT_ZH.md").read_text(encoding="utf-8")
        for k in (1, 2):
            self.assertIn(f"**Proposition {k}", en_ms)
            self.assertIn(f"**命题 {k}", zh_ms)
            self.assertIn(f"*Proof of Proposition {k}.*", en_supp)
            self.assertIn(f"*命题 {k} 的证明。*", zh_supp)
        self.assertIn("**Lemma 1", en_supp)
        self.assertIn("**引理 1", zh_supp)
        self.assertIn("*Proof*. On each interval of width $w$", en_supp)
        self.assertIn("*引理 1 的证明。*", zh_supp)
        self.assertNotIn("**Proposition 3", en_ms)
        self.assertNotIn("**命题 3", zh_ms)
        self.assertNotIn("*Proof of Proposition 3.*", en_supp)
        self.assertNotIn("*命题 3 的证明。*", zh_supp)
        self.assertNotIn(r"3\epsilon/\delta_0", en_ms)
        self.assertNotIn(r"3\epsilon/\delta_0", en_supp)
        self.assertNotIn(r"6\epsilon/\delta_0", en_supp)
        self.assertNotIn(r"3\epsilon/\delta_0", zh_ms)
        self.assertNotIn(r"3\epsilon/\delta_0", zh_supp)
        self.assertNotIn("Theorem", en_ms)
        self.assertNotIn("定理", zh_ms)
        self.assertNotIn("Theorem", en_supp)
        self.assertNotIn("定理", zh_supp)
        self.assertIn("regularized multi-scale composite", en_supp)
        self.assertNotIn("12-decimal tie stabilization", en_ms)
        self.assertNotIn("0.0404482362771082", en_supp)
        self.assertNotIn("obsolete `8 tasks / 32 cells`", en_supp)

    def test_corpus_hygiene_and_zero_internal_revision_remnants(self):
        manifest = json.loads((ROOT / "results" / "integrity_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["corpus_jsonl_count"], 12)
        self.assertEqual(len(manifest["files"]), 58)
        s5_manifest = json.loads(
            (ROOT / "extensions" / "competitor_benchmark_20261120" / "s5_integrity_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(s5_manifest["corpus_jsonl_count"], 3)
        self.assertEqual(len(s5_manifest["files"]), 10)
        repo_jsonls = sorted(
            str(p.relative_to(ROOT))
            for p in ROOT.rglob("*.jsonl")
            if ".git" not in p.parts
        )
        manifest_jsonls = sorted(
            [k for k in manifest["files"] if k.endswith(".jsonl")]
            + [k for k in s5_manifest["files"] if k.endswith(".jsonl")]
        )
        self.assertEqual(repo_jsonls, manifest_jsonls)
        self.assertEqual(len(repo_jsonls), 15)

        for doc_rel in ("paper/MANUSCRIPT_EN.md", "paper/MANUSCRIPT_ZH.md", "paper/SUPPLEMENT_EN.md", "paper/SUPPLEMENT_ZH.md"):
            text = (ROOT / doc_rel).read_text(encoding="utf-8")
            for banned in (
                "repair_results",
                "table-repair",
                "table_repairs",
                "hueprint_repair",
                "tsc_analysis",
                "tsc_round",
                "paper_revision",
                "Round-5",
                "Round-6",
                "13 historical smoke",
                "historical filename",
            ):
                self.assertNotIn(banned, text, f"Found {banned!r} in {doc_rel}")

    def test_zenodo_bundle_and_metadata_integrity(self):
        zenodo_meta = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
        self.assertEqual(zenodo_meta["upload_type"], "publication")
        self.assertEqual(zenodo_meta["publication_type"], "preprint")
        self.assertEqual(zenodo_meta["license"], "cc-by-4.0")
        self.assertTrue((ROOT / "CITATION.cff").is_file())
        self.assertTrue((ROOT / "LICENSE").is_file())

        zenodo_dir = ROOT / "zenodo_release"
        if zenodo_dir.is_dir():
            z_manifest = json.loads((zenodo_dir / "zenodo_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(z_manifest["pages"]["main_manuscript"], 12)
            self.assertEqual(z_manifest["pages"]["supplementary_material"], 20)
            self.assertEqual(z_manifest["pages"]["combined_preprint"], 32)

            zip_path = zenodo_dir / "HuePrint_Replication_Package.zip"
            self.assertTrue(zip_path.is_file())
            with zipfile.ZipFile(zip_path) as zf:
                for name in ("main.tex", "body.tex", "references.tex", "biography.tex"):
                    raw = zf.read(f"HuePrint/paper/ieee/{name}").decode("utf-8")
                    self.assertTrue(all(ord(c) < 128 for c in raw), f"Non-ASCII in {name}")
                    if name != "main.tex":
                        self.assertNotIn("../", raw)

    def test_reference_audit_updated_to_34_entries(self):
        ref_audit = (ROOT / "REFERENCE_AUDIT.md").read_text(encoding="utf-8")
        self.assertIn("34-Reference Inventory", ref_audit)
        found = [int(n) for n in re.findall(r"^### \[(\d+)\]", ref_audit, re.M)]
        self.assertEqual(found, list(range(1, 35)))

    def test_consistency_and_de_remnant_audit(self):
        en_ms = (ROOT / "paper" / "MANUSCRIPT_EN.md").read_text(encoding="utf-8")
        zh_ms = (ROOT / "paper" / "MANUSCRIPT_ZH.md").read_text(encoding="utf-8")
        en_supp = (ROOT / "paper" / "SUPPLEMENT_EN.md").read_text(encoding="utf-8")
        zh_supp = (ROOT / "paper" / "SUPPLEMENT_ZH.md").read_text(encoding="utf-8")

        for banned in ("adversarial bound", "Filter Bypass", "Input bypass", "Output bypass", "leaked reference histogram"):
            self.assertNotIn(banned, en_ms)
            self.assertNotIn(banned, en_supp)
        for banned_zh in ("对抗上界", "浅预算指纹", "过滤器规避率", "输入绕过率", "输出绕过率", "已泄露参考直方图", "s3-gpt-oss-120b"):
            self.assertNotIn(banned_zh, zh_ms)
            self.assertNotIn(banned_zh, zh_supp)
        for marker in ("REPAIR_TABLE_redteam", "HUEPRINT_OFFLINE_REPAIR_MANUSCRIPT"):
            self.assertNotIn(marker, en_supp)
            self.assertNotIn(marker, zh_supp)

        self.assertIn(r"0.00\%--10.00\% for $\Dereg{}$", en_ms)
        self.assertIn(r"3.33\%--4.44\% when perturbing individual $\Dhyb{}$ weights", en_ms)
        self.assertIn("Unflagged input", en_ms)
        self.assertIn("Regularized-Energy ($\\tilde D_{\\mathrm{E-reg}}$) Model-Cluster Bootstrap Intervals", en_supp)
        self.assertIn("12 active corpus JSONL logs", en_supp)
        self.assertIn("20261111 through 20261120", en_supp)
        self.assertIn("s3-mistral-small-3.2", en_supp)
        self.assertIn("s3-mistral-small-3.2", zh_supp)
        self.assertIn("routing_permutation.csv", en_supp)
        self.assertIn("routing_permutation.csv", zh_supp)

        # Mathematical, quantization, token-budget, and non-duplication invariants
        self.assertIn("step-32 channel quantization", en_ms)
        self.assertIn("64-call", en_ms)
        self.assertIn("U-statistic energy ratios", en_ms)
        self.assertIn("Quantization (step 32)", en_supp)
        self.assertIn(r"\frac{h+\delta_0}{(d+\delta_0)^2}", en_supp)
        self.assertIn(r"\frac{h+\delta_0}{(d+\delta_0)^2}", zh_supp)
        self.assertIn(r"0\le[F(d,h)]_+\le d/(d+\delta_0)<1", en_supp)
        self.assertIn(r"0\le[F(d,h)]_+\le d/(d+\delta_0)<1", zh_supp)
        self.assertIn("(n-1)/n", en_ms)
        self.assertIn("(n-1)/n", zh_ms)
        self.assertNotIn("(n-1)/n", en_supp)
        self.assertNotIn("(n-1)/n", zh_supp)
        self.assertIn("up to 7,719 in $P_1$ and 7,023 in $P_2$", en_supp)
        for overclaim in (
            "first-order directional variations cancel",
            "by construction",
            "32-level quantization",
            "d_{PP} < d_{PR}",
            r"[0,d_{UV})",
            "drift exceeds",
            "signed cleanly, clipped under jitter",
            "worst-case aligned displacements",
        ):
            self.assertNotIn(overclaim, en_ms)
            self.assertNotIn(overclaim, en_supp)
        for overclaim_zh in (
            "一阶方向变化在期望中抵消",
            "按构造即",
            "在构造上即精确匹配",
            "32 级量化",
            "良性网关漂移超过了",
            "清洁排序用带符号形式，扰动下用零截断形式",
            "同向最坏位移",
        ):
            self.assertNotIn(overclaim_zh, zh_ms)
            self.assertNotIn(overclaim_zh, zh_supp)

        # Verify Table S4b contains all 8 non-duplicate additional baseline rows
        m_s4 = re.search(r"<!-- RGB_TABLE_6 -->\n([\s\S]*?)\n<!-- /RGB_TABLE_6 -->", en_supp)
        self.assertIsNotNone(m_s4)
        self.assertEqual(len(m_s4.group(1).splitlines()), 10)  # header + separator + 8 data rows

    def test_sensitivity_checks_and_scope_reconciliations(self):
        self.assertNotIn(r"\textbackslash", (ROOT / "paper" / "ieee" / "body.tex").read_text(encoding="utf-8"))
        self.assertNotIn(r"\textbackslash", (ROOT / "paper" / "supplement" / "body.tex").read_text(encoding="utf-8"))

        sc = json.loads((ROOT / "results" / "diagnostics" / "sensitivity_checks.json").read_text(encoding="utf-8"))
        self.assertEqual(sc["protected_files_verified"], 58)

        s3_two = sc["s3_two_color_probe_posthoc"]["budgets"]
        self.assertAlmostEqual(s3_two["N6_3v3"]["color_hex"]["eer_linear_raw"], 0.17916666666666667, places=12)
        self.assertEqual(s3_two["N6_3v3"]["color_hex"]["eer_linear_pct"], 17.92)
        self.assertAlmostEqual(s3_two["N6_3v3"]["word_color"]["eer_linear_raw"], 0.20208333333333334, places=12)
        self.assertEqual(s3_two["N6_3v3"]["word_color"]["eer_linear_pct"], 20.21)
        self.assertAlmostEqual(s3_two["N30_15v15"]["color_hex"]["eer_linear_raw"], 20.0 / 380.0, places=12)
        self.assertAlmostEqual(s3_two["N30_15v15"]["word_color"]["eer_linear_raw"], 0.05, places=12)

        da = sc["dataset_a_pair_eligibility_sensitivity"]
        self.assertEqual(da["changed_directed_negative_pairs"], 163)
        self.assertEqual(da["total_directed_negative_pairs"], 3080)
        self.assertEqual(da["changed_genuine_pairs"], 0)
        self.assertAlmostEqual(
            da["historical_both_halves_per_target"]["metrics"]["energy_norm"]["eer_linear_raw"],
            0.04772727272727273,
            places=12,
        )
        self.assertAlmostEqual(
            da["side_independent_pair_intersection"]["metrics"]["energy_norm"]["eer_linear_raw"],
            0.04155844155844156,
            places=12,
        )
        self.assertAlmostEqual(
            da["historical_both_halves_per_target"]["metrics"]["energy_reg"]["eer_linear_raw"],
            3.0 / 56.0,
            places=12,
        )
        self.assertAlmostEqual(
            da["side_independent_pair_intersection"]["metrics"]["energy_reg"]["eer_linear_raw"],
            3.0 / 56.0,
            places=12,
        )

        s1_nine = sc["s1_standard9_cf0_cf21_audit"]
        self.assertEqual(len(s1_nine["false_accepts"]), 1)
        self.assertEqual(s1_nine["n_directed_impostors"], 72)
        self.assertAlmostEqual(s1_nine["far_raw"], 1.0 / 72.0, places=12)
        self.assertEqual(s1_nine["frr_raw"], 0.0)
        self.assertEqual(s1_nine["eer_linear_raw"], 0.0)
        self.assertEqual(s1_nine["false_accepts"][0]["reference"], "gw-gpt-4.1")
        self.assertEqual(s1_nine["false_accepts"][0]["query"], "gw-gpt-4o")

        s4a = sc["side_channel_stepwise_ablations"]
        self.assertAlmostEqual(s4a["S4a_5v5_min1"]["archived"]["hybrid"]["eer"], 6.0 / 380.0, places=12)
        self.assertAlmostEqual(s4a["S4a_5v5_min1"]["content_only_no_envelope"]["hybrid"]["eer"], 11.0 / 380.0, places=12)
        self.assertAlmostEqual(s4a["S4a_5v5_min1"]["pure_content_syntax"]["hybrid"]["eer"], 10.0 / 380.0, places=12)
        self.assertAlmostEqual(s4a["S1_CF0_to_OR21_6v6"]["archived"]["side_jsd"]["genuine_mean"], 0.1117752095006721, places=12)
        self.assertAlmostEqual(s4a["S1_CF0_to_OR21_6v6"]["content_only_no_envelope"]["side_jsd"]["genuine_mean"], 0.016098488336461984, places=12)
        self.assertAlmostEqual(s4a["S1_CF0_to_OR21_6v6"]["pure_content_syntax"]["side_jsd"]["genuine_mean"], 0.006400222733565713, places=12)

        mix = sc["mixed_routing_point_mass_example"]
        self.assertEqual(mix["unnormalized_ratio_pct"], 4.0)
        self.assertAlmostEqual(mix["regularized_ratio_raw"], 23.0 / 175.0, places=12)

    def test_ieee_tsc_abstract_limit_and_operational_diagnostics(self):
        en_ms = (ROOT / "paper" / "MANUSCRIPT_EN.md").read_text(encoding="utf-8")
        m_abs = re.search(r"^\*\*Abstract\*\*—([\s\S]*?)\n\n\*\*Index Terms\*\*", en_ms, re.M)
        self.assertIsNotNone(m_abs)
        abs_text = m_abs.group(1).strip()
        ws_words = abs_text.split()
        hy_words = [w for w in re.split(r"[\s—–-]+", abs_text) if w]
        self.assertGreaterEqual(len(ws_words), 100)
        self.assertLessEqual(len(ws_words), 200)
        self.assertGreaterEqual(len(hy_words), 100)
        self.assertLessEqual(len(hy_words), 200)

        rdd = json.loads(
            (ROOT / "results" / "diagnostics" / "operational_diagnostics.json").read_text(encoding="utf-8")
        )
        self.assertEqual(rdd["protected_baseline_files_verified"], 58)
        self.assertEqual(rdd["protected_s5_files_verified"], 10)
        self.assertEqual(rdd["study_s5c_all_balanced_3v3_splits"]["n_balanced_partitions"], 10)
        s5_sum = rdd["study_s5c_all_balanced_3v3_splits"]["summary"]
        self.assertEqual(s5_sum["energy_reg_all_eer_pct"]["mean"], 3.48)
        self.assertEqual(s5_sum["energy_reg_within_fam_eer_pct"]["mean"], 5.18)
        self.assertEqual(
            rdd["study_s2_side_decontamination"]["6v6"]["content_only_no_envelope"]["hybrid"]["eer_pct"],
            5.93,
        )
        self.assertEqual(
            rdd["study_s2_side_decontamination"]["6v6"]["pure_content_syntax"]["hybrid"]["eer_pct"],
            5.56,
        )
        self.assertEqual(
            rdd["private_pool_subsampling"]["B_40cell_pool"]["q3_reps"]["k=10_of_40"]["mean_eer_pct"],
            0.65,
        )
        self.assertEqual(
            rdd["two_stage_sequential_cascade"]["S3_5window_stream_matched_B10_u_clipped"]["two_stage_frr_pct"],
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
