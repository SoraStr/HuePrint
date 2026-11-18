# Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services

**English** | [简体中文](README-ZH.md)

Official implementation, empirical corpus (**34,528 deduplicated cloud calls**), and offline replication package for **HuePrint**, a lightweight black-box behavioral consistency auditing framework for aggregated large language model (MaaS / multi-provider gateway) services.

HuePrint elicits compact multilingual color coordinates (`#RRGGBB` and `R,G,B`) and compares empirical distributions in a continuous RGB geometric space (`RGB100`) without requiring model weights, hidden states, or honest token log-probabilities.

---

## Manuscript & Documentation

- **Main Manuscript (12 pages, IEEE Computer Society format)**: [paper/MANUSCRIPT_EN.md](paper/MANUSCRIPT_EN.md) · [paper/ieee/main.pdf](paper/ieee/main.pdf) · Chinese sync: [paper/MANUSCRIPT_ZH.md](paper/MANUSCRIPT_ZH.md)
- **Supplementary Material (16 pages, Proofs, Inventories & Extended Tables)**: [paper/SUPPLEMENT_EN.md](paper/SUPPLEMENT_EN.md) · [paper/supplement/main.pdf](paper/supplement/main.pdf) · Chinese sync: [paper/SUPPLEMENT_ZH.md](paper/SUPPLEMENT_ZH.md)
- **RGB100 Protocol & Validation**: [docs/RGB_PROTOCOL.md](docs/RGB_PROTOCOL.md) · [docs/RGB_MIGRATION_VALIDATION.md](docs/RGB_MIGRATION_VALIDATION.md)
- **LaTeX Build & Packaging Guide**: [paper/LATEX_README.md](paper/LATEX_README.md) · **34-Reference Audit**: [REFERENCE_AUDIT.md](REFERENCE_AUDIT.md)

---

## Key Empirical Highlights (34,528 Cloud Calls, 56 Endpoints, 12 Backends)

- **Low-budget separation**: At 30 calls per side ($K=10$), HuePrint's structured color protocol lowers clean equal error rates (EERs) from `4.52%–5.23%` for a single-word battery to `0.94%–1.00%` on the development cohort (`B-20x6` vs. `D`) and from `6.25%–8.04%` to `3.49%–5.00%` across 20 locked endpoints (Study S3, 12,000 calls), reaching `0.00%` at deeper budgets.
- **Continuous & multi-scale RGB gains**: Regularized energy $\tilde D_{\mathrm{E\text{-}reg}}$ halves shallow 56-endpoint census EER relative to exact-hex JSD (`5.36%` vs. `10.71%` on Dataset A), while multi-scale $D_{\mathrm{hyb}}$ cuts cross-provider open-weight EER across 12 pinned backends from `16.67%` to `5.93%` (Study S2). Across two snapshots three weeks apart and two gateways (`Cloudflare` and `OpenRouter`, Study S1), score-based auditing keeps `0.00%` ranking EER where strict equality tests ($p \le 0.05$) reject up to `42.86%` of genuine pairs.
- **Theoretical bounds & zero-bootstrap U-ratios**: Unified Lipschitz bounds ($2\epsilon/\delta_0$ one-sided, $4\epsilon/\delta_0$ two-sided) cover both V-statistic and U-statistic regularized energy ratios. Enrollment self-centering cuts clean held-out Dataset E FRR from `30.00%` to `10.00%` (at `0.00%` FAR), and U-statistic energy ratios eliminate the 256-draw enrollment bootstrap.
- **Out-of-band overhead & structured canaries**: Median estimated query cost is below `$0.04` per audit (`$0.0077–$0.0345` across 150-call S3 catalog scenarios), warm single-pair CPU scoring medians are `0.08–0.31 ms` (`2.39–10.15 ms` for 999 stratified permutations), and CSS/JSON schema-constrained canaries (Study S4a) achieve `99.75%` (`3,192/3,200`) valid unflagged pass rate with `0.00%` energy EER.

---

## Repository Structure

```text
HuePrint/
├── collect.py                    # Async probe collector (OpenAI CC / Anthropic Messages)
├── analyze.py                    # Core RGB100 analyzer (protocol rgb100_v1_20261111, parser 3.0)
├── reproduce_all.py              # Offline baseline benchmark suite (Datasets A–E)
├── config/                       # Probe batteries (prompts*.json), family map, target templates
├── data/                         # 5 frozen baseline JSONL corpora (11,888 unique calls)
├── extensions/
│   └── live_validation_20261111/ # 7 frozen live-study JSONL corpora (S1–S4, 22,640 calls) & lv_analyze.py
├── scripts/                      # Offline statistical audits, figure generators, verification, Zenodo packager
├── results/                      # Archived CSV/JSON outputs & integrity_manifest.json (58 SHA-256 locks)
├── paper/                        # Authoritative Markdown manuscripts, sync scripts, and compiled PDFs
├── figs/                         # Vector PDF/SVG figures (Figs. 1–6)
├── tests/                        # 40 unit & manuscript-integrity tests
└── docs/                         # RGB100 coordinate protocol & migration verification notes
```

---

## Quick Start: Auditing Custom Endpoints

The active coordinate protocol is **`rgb100_v1_20261111`** (`parser_version = "3.0"`), which extracts `#RRGGBB` or `R,G,B` triplets and linearly scales `0..255` integer channels to `100 × RGB / 255` (`RGB100`) for continuous energy statistics while keeping discrete exact-hex and hard/soft voxel grids in native `0..255` units.

1. Install Python dependencies (Python >= 3.11):
   ```bash
   pip install -r requirements.txt
   ```
2. Configure your targets in a JSON file following [config/targets.example.json](config/targets.example.json) (using environment variables such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for credentials), preview the probe schedule with `--dry-run`, then run collection and analysis:
   ```bash
   python3 collect.py --targets-config config/targets.example.json --prompts config/prompts.json --reps-t1 6 --reps-t0 0 --output /tmp/hueprint_audit.jsonl --dry-run
   python3 collect.py --targets-config config/targets.example.json --prompts config/prompts.json --reps-t1 6 --reps-t0 0 --output /tmp/hueprint_audit.jsonl
   python3 analyze.py --input /tmp/hueprint_audit.jsonl --output-json /tmp/hueprint_report.json
   ```

---

## Offline Reproduction & Verification

All **12 frozen JSONL response logs**, prompt/target configurations, and archived benchmark outputs (**58 protected files**) are SHA-256 locked in [results/integrity_manifest.json](results/integrity_manifest.json) (with live-extension source locks in [extensions/live_validation_20261111/lv_rgb_integrity_manifest.json](extensions/live_validation_20261111/lv_rgb_integrity_manifest.json)). Offline analysis scripts under `scripts/` install `sys.addaudithook` guards blocking network and subprocess calls, verify protected SHA-256 digests before and after execution, and write to `--output` without overwriting archived results.

Run the entire offline reproduction pipeline, manuscript integrity verification, and all 40 unit tests into a fresh temporary directory:

```bash
OUT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hueprint-repro.XXXXXX")"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B reproduce_all.py --output "$OUT_DIR/reproduce_all_rgb_summary.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B extensions/live_validation_20261111/lv_analyze.py --dev-summary "$OUT_DIR/reproduce_all_rgb_summary.json" --output "$OUT_DIR/lv_rgb_results.json" --manifest "$OUT_DIR/lv_rgb_manifest.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/service_audit_analysis.py --output "$OUT_DIR/service_audit"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/energy_u_analysis.py --output "$OUT_DIR/energy_u"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/protocol_routing_analysis.py --output "$OUT_DIR/protocol_audit"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/perturbation_calibration_analysis.py --output "$OUT_DIR/perturbation_diagnostics.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/mmd_truncation_analysis.py --output "$OUT_DIR/subset_mmd_diagnostics.json" --exact-mmd-output "$OUT_DIR/exact_mmd_baselines.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/sensitivity_checks.py --output "$OUT_DIR/sensitivity_checks.json"
python3 -B scripts/verify_manuscript.py
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B -m unittest discover -s tests -p 'test_*.py'
```

To rebuild the LaTeX sources and verify table synchronization (see [paper/LATEX_README.md](paper/LATEX_README.md)):

```bash
python3 -B paper/sync_supplement_inventory.py --check
python3 -B paper/sync_benchmark_tables.py --check
python3 -B paper/sync_service_tables.py --check
python3 -B paper/build_latex.py --check
```

---

## Citation & License

- **Code & analysis scripts**: [MIT License](LICENSE)
- **Manuscript, figures, documentation & empirical JSONL datasets**: [CC BY 4.0](LICENSE)

Machine-readable citation metadata is provided in [CITATION.cff](CITATION.cff) and [.zenodo.json](.zenodo.json):

```bibtex
@misc{he2026hueprint,
  author       = {He, Xiguan},
  title        = {Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services},
  year         = {2026},
  howpublished = {Preprint and replication package},
  url          = {https://github.com/SoraStr/HuePrint}
}
```
