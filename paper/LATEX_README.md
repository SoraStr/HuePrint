# 主稿、补充材料与 Zenodo 预印本构建说明

## 权威源文件与交付产物

英文权威源稿为 `MANUSCRIPT_EN.md`（中文同步稿为 `MANUSCRIPT_ZH.md`），独立补充材料源稿为 `SUPPLEMENT_EN.md`（中文同步稿为 `SUPPLEMENT_ZH.md`）。主构建产物为：

- `ieee/main.pdf`：`IEEEtran`（`\documentclass[10pt,journal,compsoc]{IEEEtran}`，原生行距与 `8pt` `\footnotesize` 表格），署名来自 `direct_replacements/author.tex` 与 `author_metadata.json`，共 **12 页**（含参考文献与作者简介，0 `Overfull \hbox`，0 `Underfull \vbox`）；
- `supplement/main.pdf`：A–L 节合并带目录的独立英文补充材料（XeTeX/fontspec 排印中/英/俄/阿四语原始探针），共 **16 页**（0 `Overfull \hbox`，0 `Underfull \vbox`）；
- `../zenodo_release/HuePrint_Preprint.pdf`：主稿与补充材料无损合并的 **28 页完整预印本 PDF**，配套独立主稿/补充 PDF 与脱敏复现包 `../zenodo_release/HuePrint_Replication_Package.zip`。

LaTeX 文件由 `build_latex.py` 与 `build_supplement.py` 从可编辑 Markdown 机械生成，请勿直接手改派生的 `*.tex` 文件。全部 12 份正式语料 JSONL 日志、提示配置与冻结统计基准（共 58 个文件）受 `../results/integrity_manifest.json` 的 SHA-256 哈希保护。

### 源文件与同步组件

- **主稿与补充材料**：
  - `MANUSCRIPT_EN.md` / `MANUSCRIPT_ZH.md`：包含 9 张正文统计表与图 1–图 6。
  - `SUPPLEMENT_EN.md` / `SUPPLEMENT_ZH.md`：包含 A–L 共 12 节与表 S1–S9（含 CIELAB 对照、能量/混合量正则化与纯文本侧信道去混杂消融、56 端点清单、40 核心探针与 32 个 S4 金丝雀单元原文、命题 1–2 与引理 1 的稳定性证明、Bootstrap 区间、改写池与精度组详情、离线复现与协议取证说明，以及受控数值扰动与二十种子混合路由置换检验对照）。
- **文献池一致性**：四份 Markdown 共用 34 条文献池（`[1]`–`[34]`，结构化 BibTeX 为 `references.bib`，逐条核验见根目录 `../REFERENCE_AUDIT.md`）。主稿 PDF 按正文首次出现顺序排印 `[1]`–`[29]`，补充材料 PDF 排印实际引用的 `[24]`–`[34]`（其中 `[24]`–`[29]` 沿用主稿编号，`[30]`–`[34]` 为补充材料专用文献）。
- **表块同步器**：
  - `sync_supplement_inventory.py`：同步补充材料 C–F 节的端点清单与多语言探针原文；
  - `sync_benchmark_tables.py`：从 `../results/benchmark/`、`../results/corpus_stats/` 与 `../results/diagnostics/` 同步主稿与补充材料中的命名统计表块（`BENCH_TABLE_*`）；
  - `sync_service_tables.py`：从 `../results/service_audit/` 与 `../results/energy_u/` 同步同家族、V/U 对照、S1 迁移与运行开销表块（`AUDIT_TABLE_*`）。

## 标准构建、Zenodo 打包与端到端校验流程

在项目根目录依次执行：

```bash
python3 -B paper/sync_supplement_inventory.py --check
python3 -B paper/sync_benchmark_tables.py --check
python3 -B paper/sync_service_tables.py --check
python3 -B paper/build_latex.py
python3 -B paper/build_latex.py --check
tools/tectonic --only-cached --keep-logs paper/ieee/main.tex
tools/tectonic --only-cached --keep-logs paper/supplement/main.tex
python3 -B scripts/build_zenodo_package.py
python3 -B scripts/verify_manuscript.py
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B -m unittest discover -s tests -p 'test_*.py'
```

构建使用 Tectonic 0.17.0（版本溯源见 `../tools/tectonic_provenance.json`；平台二进制文件不打入公开归档包）。`build_supplement.py` 内置跨平台字体回退（macOS 原生字体不存在时自动回退至 `Noto Sans CJK SC` / `Noto Naskh Arabic` / 随附 `DejaVuSans.ttf`）。`scripts/build_zenodo_package.py` 在 `../zenodo_release/` 生成全套 Zenodo 预印本上传产物与校验清单，并自动清理构建过程临时 `.log` 日志。

## 图件清单

主稿图 1–图 6 依次对应 `../figs/` 下的矢量 PDF/SVG：
1. `fig1_service_audit.pdf`
2. `fig2_rgb_geometry_vs_words.pdf`
3. `fig3_stability_bounds.pdf`
4. `fig4_budget_and_drift.pdf`
5. `fig5_geometry_and_calibration.pdf`
6. `fig6_mixed_routing.pdf`
