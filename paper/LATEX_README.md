# 主稿、补充材料与 Zenodo 预印本构建说明

## 权威源文件与交付产物

英文权威源稿为 `MANUSCRIPT_EN.md`（中文同步稿为 `MANUSCRIPT_ZH.md`），独立补充材料源稿为 `SUPPLEMENT_EN.md`（中文同步稿为 `SUPPLEMENT_ZH.md`）。主构建产物为：

- `ieee/main.pdf`：`IEEEtran`（`\documentclass[10pt,journal,compsoc]{IEEEtran}`，原生行距与 `8pt` `\footnotesize` 表格），署名来自 `direct_replacements/author.tex` 与 `author_metadata.json`，共 **12 页**（含参考文献与作者简介，148 词 IEEE TSC 合规摘要，0 `Overfull \hbox`，0 `Underfull \vbox`）；
- `supplement/main.pdf`：A–M 共 13 节带目录的独立英文补充材料（XeTeX/fontspec 排印中/英/俄/阿四语原始探针），共 **20 页**（0 `Overfull \hbox`，0 `Underfull \vbox`）；
- `../zenodo_release/HuePrint_Preprint.pdf`：主稿与补充材料无损合并的 **32 页完整预印本 PDF**，配套独立主稿/补充 PDF 与脱敏复现包 `../zenodo_release/HuePrint_Replication_Package.zip`。

LaTeX 文件由 `build_latex.py` 与 `build_supplement.py` 从可编辑 Markdown 机械生成，请勿直接手改派生的 `*.tex` 文件。全部 15 份只读语料 JSONL 日志（12 份基线 + 3 份 Study S5，共 38,688 条云端响应）、提示配置与冻结统计基准分别受 `../results/integrity_manifest.json`（58 个文件）、`../extensions/live_validation_20261111/lv_rgb_integrity_manifest.json` 与 `../extensions/competitor_benchmark_20261120/s5_integrity_manifest.json`（10 个文件）的 SHA-256 哈希保护。

### 源文件与同步组件

- **主稿与补充材料**：
  - `MANUSCRIPT_EN.md` / `MANUSCRIPT_ZH.md`：包含表 1–表 9 共 9 张正文表与图 1–图 6。
  - `SUPPLEMENT_EN.md` / `SUPPLEMENT_ZH.md`：包含 A–M 共 13 节与表 S1–S14（含 `S4a/S4b` 与 `S12a/S12b`：CIELAB 对照、能量/混合量正则化与 S2/S4a 纯文本侧信道去混杂消融、56 端点清单、40 核心探针与 32 个 S4 金丝雀单元原文、命题 1–2 的稳定性证明、S1 全量迁移与 Bootstrap 区间、改写池与精度组详情、S3 全矩阵、持出集 E 匹配 V/U 估计量对照、离线复现与外部 U 统计量核验、运行开销中位数表、受控数值扰动、二十种子混合路由置换检验、私有提示池子抽样与两阶段序贯监测，以及 Study S5 同日竞品基准明细）。
- **文献池一致性**：四份 Markdown 共用 33 条文献池（`[1]`–`[33]`，结构化 BibTeX 为 `references.bib`，逐条核验见根目录 `../REFERENCE_AUDIT.md`）。主稿 PDF 按正文首次出现顺序排印 `[1]`–`[30]`，补充材料 PDF 排印实际引用的 `[4]`、`[16]`、`[25]`–`[33]`（其中 `[4]`、`[16]`、`[25]`–`[30]` 沿用主稿编号，`[31]`–`[33]` 为补充材料专用文献）。
- **表块同步器**：
  - `sync_supplement_inventory.py`：同步补充材料 C–F 节的端点清单与多语言探针原文；
  - `sync_benchmark_tables.py`：从 `../results/benchmark/`、`../results/corpus_stats/` 与 `../results/diagnostics/` 同步主稿与补充材料中的命名统计表块（`BENCH_TABLE_*`、`RGB_TABLE_*`）；
  - `sync_service_tables.py`：从 `../results/service_audit/` 与 `../results/energy_u/` 同步同家族、V/U 对照、S1 迁移与运行开销表块（`AUDIT_TABLE_*`）；
  - `sync_s5_tables.py`：从 `../extensions/competitor_benchmark_20261120/results/` 与 `../results/benchmark/` 同步主稿与补充材料的中英文 Study S3 精简表与 Study S5 竞品对照表（`S3_TABLE_compact`、`S5_TABLE_*`）。

## 标准构建、Zenodo 打包与端到端校验流程

在项目根目录依次执行：

```bash
python3 -B paper/sync_supplement_inventory.py --check
python3 -B paper/sync_benchmark_tables.py --check
python3 -B paper/sync_service_tables.py --check
python3 -B paper/sync_s5_tables.py --check
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
