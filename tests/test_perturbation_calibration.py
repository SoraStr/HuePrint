"""Unit tests for mathematical perturbation bounds, LaTeX ASCII cleanliness, and Zenodo bundle invariants."""
from __future__ import annotations

import json
import re
import sys
import unittest
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def energy_ratios_all(u: np.ndarray, v: np.ndarray, delta0: float = 15.0) -> tuple[float, float, float]:
    n, m = len(u), len(v)
    duv = float(np.linalg.norm(u[:, None, :] - v[None, :, :], axis=-1).mean())
    duu_v = float(np.linalg.norm(u[:, None, :] - u[None, :, :], axis=-1).mean())
    dvv_v = float(np.linalg.norm(v[:, None, :] - v[None, :, :], axis=-1).mean())
    v_reg = max(0.0, duv - 0.5 * (duu_v + dvv_v)) / (duv + delta0)

    duu_u = float(np.linalg.norm(u[:, None, :] - u[None, :, :], axis=-1).sum() / (n * (n - 1)))
    dvv_u = float(np.linalg.norm(v[:, None, :] - v[None, :, :], axis=-1).sum() / (m * (m - 1)))
    au = duv - 0.5 * (duu_u + dvv_u)
    u_signed = au / (duv + delta0)
    u_clipped = max(0.0, au) / (duv + delta0)
    return v_reg, u_signed, u_clipped


class PerturbationCalibrationTests(unittest.TestCase):
    def test_proposition1_tightness_iff_and_r2_counterexample(self):
        diag = json.loads(
            (ROOT / "results" / "diagnostics" / "perturbation_diagnostics.json").read_text(encoding="utf-8")
        )
        t1 = diag["theorem1_tightness"]
        r1 = t1["point_mass_pref_proportional_q_on_support"]
        r2 = t1["nonuniform_pref_uniform_q_on_support"]
        self.assertAlmostEqual(r1["jsd_actual"], r1["psi_t"], places=12)
        self.assertGreater(r2["jsd_actual"] - r2["psi_t"], 0.02)
        self.assertAlmostEqual(r2["jsd_actual"], 0.829820, places=5)
        self.assertAlmostEqual(r2["psi_t"], 0.805565, places=5)

    def test_unified_energy_ratio_perturbation_bounds(self):
        rng = np.random.default_rng(20261115)
        delta0 = 15.0

        # Deterministic edge cases: (1) strongly negative U, (2) sign-crossing [U]_+, (3) zero cross-distance d_UV = 0
        u_neg = np.array([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]])
        v_neg = np.array([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]])
        v_neg_shift = np.array([[4.0, 0.0, 0.0], [96.0, 0.0, 0.0]])
        _, s_neg0, c_neg0 = energy_ratios_all(u_neg, v_neg, delta0)
        _, s_neg1, c_neg1 = energy_ratios_all(u_neg, v_neg_shift, delta0)
        self.assertLess(s_neg0, -0.7)
        self.assertEqual(c_neg0, 0.0)
        self.assertLessEqual(abs(s_neg1 - s_neg0), 2.0 * 4.0 / delta0 + 1e-12)
        self.assertLessEqual(abs(c_neg1 - c_neg0), 2.0 * 4.0 / delta0 + 1e-12)

        # Sign-crossing from negative U to positive U under eps = 7.0
        u_cross = np.array([[0.0, 0.0, 0.0], [6.0, 0.0, 0.0]])
        v_cross0 = np.array([[0.0, 0.0, 0.0], [6.0, 0.0, 0.0]])
        v_cross1 = np.array([[7.0, 0.0, 0.0], [13.0, 0.0, 0.0]])
        v0, s0, c0 = energy_ratios_all(u_cross, v_cross0, delta0)
        v1, s1, c1 = energy_ratios_all(u_cross, v_cross1, delta0)
        self.assertLess(s0, 0.0)
        self.assertGreater(s1, 0.0)
        self.assertEqual(c0, 0.0)
        self.assertGreater(c1, 0.0)
        for a, b in ((v0, v1), (s0, s1), (c0, c1)):
            self.assertLessEqual(abs(b - a), 2.0 * 7.0 / delta0 + 1e-12)

        # Zero cross-distance d_UV = 0 with unaligned per-point shifts
        u_zero = np.array([[50.0, 50.0, 50.0], [50.0, 50.0, 50.0]])
        v_zero = np.array([[50.0, 50.0, 50.0], [50.0, 50.0, 50.0]])
        v_zero_pert = np.array([[53.0, 50.0, 50.0], [47.0, 50.0, 50.0]])
        vz0, sz0, cz0 = energy_ratios_all(u_zero, v_zero, delta0)
        vz1, sz1, cz1 = energy_ratios_all(u_zero, v_zero_pert, delta0)
        self.assertEqual((vz0, sz0, cz0), (0.0, 0.0, 0.0))
        for a, b in ((vz0, vz1), (sz0, sz1), (cz0, cz1)):
            self.assertLessEqual(abs(b - a), 2.0 * 3.0 / delta0 + 1e-12)

        # Randomized one-sided (2*eps/delta0) and two-sided (4*eps/delta0) checks with arbitrary directions
        for n, m in [(2, 2), (2, 3), (3, 3), (5, 7)]:
            for _ in range(250):
                u = rng.uniform(0.0, 100.0, size=(n, 3))
                v = rng.uniform(0.0, 100.0, size=(m, 3))
                eps = float(rng.uniform(0.05, 8.0))
                u_dirs = rng.normal(size=(n, 3))
                v_dirs = rng.normal(size=(m, 3))
                u_pert = u + u_dirs / np.maximum(np.linalg.norm(u_dirs, axis=-1, keepdims=True), 1e-12) * rng.uniform(0.0, eps, size=(n, 1))
                v_pert = v + v_dirs / np.maximum(np.linalg.norm(v_dirs, axis=-1, keepdims=True), 1e-12) * rng.uniform(0.0, eps, size=(m, 1))

                vr0, us0, uc0 = energy_ratios_all(u, v, delta0)
                vr1, us1, uc1 = energy_ratios_all(u, v_pert, delta0)
                vr2, us2, uc2 = energy_ratios_all(u_pert, v_pert, delta0)
                for c in (vr0, vr1, vr2, uc0, uc1, uc2):
                    self.assertGreaterEqual(c, 0.0)
                    self.assertLess(c, 1.0)
                for x0, x1, x2 in ((vr0, vr1, vr2), (us0, us1, us2), (uc0, uc1, uc2)):
                    self.assertLessEqual(abs(x1 - x0), 2.0 * eps / delta0 + 1e-12)
                    self.assertLessEqual(abs(x2 - x0), 4.0 * eps / delta0 + 1e-12)

    def test_native_ieeetran_spacing_pure_ascii_and_hyphen_macros(self):
        main_tex = (ROOT / "paper" / "ieee" / "main.tex").read_text(encoding="utf-8")
        body_tex = (ROOT / "paper" / "ieee" / "body.tex").read_text(encoding="utf-8")
        refs_tex = (ROOT / "paper" / "ieee" / "references.tex").read_text(encoding="utf-8")
        bio_tex = (ROOT / "paper" / "ieee" / "biography.tex").read_text(encoding="utf-8")

        for name, content in [("main.tex", main_tex), ("body.tex", body_tex), ("references.tex", refs_tex), ("biography.tex", bio_tex)]:
            non_ascii = [ch for ch in content if ord(ch) > 127]
            self.assertEqual(non_ascii, [], f"Non-ASCII chars found in ieee/{name}: {non_ascii[:5]}")

        for banned in (r"\def\tabular", r"\textfloatsep", r"\abovedisplayskip", r"\raggedbottom", r"\scriptsize"):
            self.assertNotIn(banned, main_tex)
            self.assertNotIn(banned, body_tex)

        self.assertIn(r"\newcommand{\Dereg}{\tilde D_{\mathrm{E\mbox{-}reg}}}", main_tex)
        self.assertIn(r"\newcommand{\Dhybreg}{D_{\mathrm{hyb\mbox{-}reg}}}", main_tex)
        self.assertRegex(main_tex, r"\\usepackage\{[^}]*\bcite\b[^}]*\}")
        self.assertIn(r"\cite{ref1,ref2,ref3}", body_tex)
        self.assertIn(r"\cite{ref11,ref12,ref13}", body_tex)
        self.assertIn(r"\cite{ref18,ref19,ref20,ref21}", body_tex)

    def test_supplement_gap_free_references_and_arabic_ltr_isolation(self):
        supp_refs = (ROOT / "paper" / "supplement" / "references.tex").read_text(encoding="utf-8")
        supp_body = (ROOT / "paper" / "supplement" / "body.tex").read_text(encoding="utf-8")

        bibitems = [(int(a), int(b)) for a, b in re.findall(r"\\bibitem\[(\d+)\]\{ref(\d+)\}", supp_refs)]
        self.assertEqual(bibitems, [(4, 4), (16, 16)] + [(n, n) for n in range(25, 34)])

        arabic_lines = [ln for ln in supp_body.splitlines() if r"\textarabic{" in ln]
        self.assertGreaterEqual(len(arabic_lines), 12)
        for ln in arabic_lines:
            if "RRGGBB" in ln:
                self.assertIn(r"\textenglish{\addfontfeatures{Ligatures=TeXOff}\#RRGGBB", ln)
            if "0-255" in ln:
                self.assertIn(r"\textenglish{\addfontfeatures{Ligatures=TeXOff}(0-255)", ln)
            if "R,G,B" in ln:
                self.assertIn(r"\textenglish{\addfontfeatures{Ligatures=TeXOff}R,G,B}", ln)

    def test_zenodo_bundle_ieee_tex_is_pure_ascii(self):
        for name in ("main.tex", "body.tex", "references.tex", "biography.tex"):
            raw = (ROOT / "paper" / "ieee" / name).read_text(encoding="utf-8")
            self.assertTrue(all(ord(c) < 128 for c in raw), f"Non-ASCII in {name}")
            if name != "main.tex":
                self.assertNotIn("../", raw)
        zip_path = ROOT / "zenodo_release" / "HuePrint_Replication_Package.zip"
        if zip_path.is_file():
            with zipfile.ZipFile(zip_path) as zf:
                for name in ("main.tex", "body.tex", "references.tex", "biography.tex"):
                    raw = zf.read(f"HuePrint/paper/ieee/{name}").decode("utf-8")
                    self.assertTrue(all(ord(c) < 128 for c in raw), f"Non-ASCII in {name}")


if __name__ == "__main__":
    unittest.main()
