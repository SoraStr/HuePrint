# 空谈无益，亮出颜色：面向聚合式大语言模型服务的低预算一致性审计

[English](README.md) | **简体中文**

本仓库为黑盒行为一致性审计框架 **HuePrint** 的官方实现、实证语料库（**15 份只读 JSONL 日志，共 38,688 条去重云端调用**）与全量离线复现包，对应论文《*Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services*》。

HuePrint 通过多语种结构化短颜色探针（`#RRGGBB` 与 `R,G,B`）采集模型输出分布，并在连续三维 RGB 几何空间（`RGB100`）上执行分布比对与假设检验，**无需模型权重、隐藏状态或服务端诚实返回的词元对数概率**，即可核验聚合网关端点是否兑现固定检查点（pinned-checkpoint）SLA 承诺。

---

## 论文与文档入口

- **英文主稿（12 页，IEEE Computer Society 排版）**：[paper/MANUSCRIPT_EN.md](paper/MANUSCRIPT_EN.md) · [paper/ieee/main.pdf](paper/ieee/main.pdf)（中文同步稿：[paper/MANUSCRIPT_ZH.md](paper/MANUSCRIPT_ZH.md)）
- **独立补充材料（20 页，A–M 共 13 节、完整证明、端点清单与扩展对照表）**：[paper/SUPPLEMENT_EN.md](paper/SUPPLEMENT_EN.md) · [paper/supplement/main.pdf](paper/supplement/main.pdf)（中文同步稿：[paper/SUPPLEMENT_ZH.md](paper/SUPPLEMENT_ZH.md)）
- **RGB100 坐标协议与迁移验证**：[docs/RGB_PROTOCOL.md](docs/RGB_PROTOCOL.md) · [docs/RGB_MIGRATION_VALIDATION.md](docs/RGB_MIGRATION_VALIDATION.md)
- **LaTeX 构建与预印本打包说明**：[paper/LATEX_README.md](paper/LATEX_README.md) · **33 篇参考文献核验清单**：[REFERENCE_AUDIT.md](REFERENCE_AUDIT.md)

---

## 核心实证结果速览（38,688 条云端响应，56 端点，12 家独立后端）

- **浅预算区分与同日竞品正面对照**：在每侧 30 次调用（$K=10$）下，结构化颜色协议将清洁等错误率（EER）在开发队列（`B-20x6` 对照 `D`）上从单词题组的 `4.52%–5.23%` 降至 `0.94%–1.00%`，在 20 个锁参端点基准（Study S3，12,000 次调用）上从 `6.25%–8.04%` 降至 `3.49%–5.00%`，并在 60–150 次调用下达到 `0.00%`。在同日 20 模型正面对照基准（Study S5，4,160 次调用）中，HuePrint 在全部 10 种平衡 `3v3` 划分上平均全配对 EER 为 `3.48%`（范围 `1.32%–5.00%`）、同家族 EER 为 `5.18%`（范围 `0.00%–7.89%`；匹配划分为 `1.32%` / `0.00%`），单次查询成本仅 `0.0068 USD`，优于开放集 LLMmap（1–3 条轨迹同家族 EER `10.53%–34.39%`、`q1` 拒答率 `95%`、本地 CPU 耗时 `4,701.9 ms`）以及等美元预算的长文本续写核方法（同家族 EER `11.09%–19.47%`）。
- **连续与多尺度几何增益**：正则化能量距离 $\tilde D_{\mathrm{E\text{-}reg}}$ 在 56 端点浅层普查（Dataset A）上将精确色号离散散度（$D_{\mathrm{hex}}$）的 EER 减半（`5.36%` 对 `10.71%`）；多尺度混合量 $D_{\mathrm{hyb}}$ 将跨 12 家指定推理后端（Study S2）的开放权重 EER 从 `16.67%` 压至 `5.93%`（剥离信封与语法混杂后为 `5.56%`）。在相隔 21 天的跨网关迁移（`Cloudflare` 至 `OpenRouter`，Study S1）中，同标签与异标签配对在分数上仍完全可分（`0.00%` EER）且各规则均检出 `182/182` 次替换：预算匹配的 `B6v6` 冻结阈值标记了 `1/14` 个原始同标签配对（自中心化后为 `0/14`），而分层能量置换检验在 $\alpha=0.05$ 下对同一批配对中的 `6/14` 对拒绝了分布相等假设。
- **理论扰动界与零 bootstrap U 比值**：统一的 Lipschitz 稳定性上界（单侧 $2\epsilon/\delta_0$、双侧 $4\epsilon/\delta_0$）同时覆盖 V 统计量与带符号/截断 U 统计量比值；注册自中心化将清洁持出集 E 误拒率从 `30.00%` 降至 `10.00%`（零误受），U 统计量比值省去了 256 次注册 bootstrap 抽样。
- **低开销持续运行与隐式金丝雀**：单次审计查询估算 API 费用中位数低于 `0.04 USD`（150 次调用的 S3 情景中位数为 `0.0077–0.0345 USD`），预热后本地单线程 CPU 单对评分中位数为 `0.08–0.31 ms`（999 次分层能量置换检验为 `2.39–10.15 ms`）；单行 CSS 与单字段 JSON 令牌金丝雀探针（Study S4a）取得 `99.75%`（`3,192/3,200`）合法未触发通过率与 `0.00%` 能量 EER。从预注册私有池随机抽取匹配单元（40 选 10）在降低单单元提示复用率 `4.0x` 的同时保持 `0.65%` / `0.03%` 平均 EER（3 / 7 次重复）；在 S3 的 `100` 个同标签回放窗口中，两阶段序贯复核（`30 -> 60` 次调用）将误报从 `14` 个降至 `1` 个（`1.00%`），并标记 `186/190`（`97.89%`）个同家族替换窗口（期望仅 `38.40` 次调用，`0.0087 USD` 情景 G）。

---

## 仓库目录结构

```text
HuePrint/
├── collect.py                         # 异步探针采集脚本（支持 OpenAI CC / Anthropic Messages）
├── analyze.py                         # 核心 RGB100 分析器（协议 rgb100_v1_20261111，解析器 3.0）
├── reproduce_all.py                   # 离线基准复现入口（Datasets A–E）
├── config/                            # 探针题组（prompts*.json）、家族谱系映射与目标配置模板
├── data/                              # 5 份只读基准语料 JSONL（11,888 条唯一调用）
├── extensions/
│   ├── live_validation_20261111/      # 7 份只读线上研究语料 JSONL（S1–S4，22,640 条调用）与 lv_analyze.py
│   └── competitor_benchmark_20261120/ # 3 份只读 Study S5 语料 JSONL（4,160 条调用）、s5_analyze.py 与 10 项锁定
├── scripts/                           # 离线统计审计、矢量图表绘制、完整性校验与 Zenodo 打包脚本
├── results/                           # 归档 CSV/JSON 结果与 integrity_manifest.json（58 个 SHA-256 锁定文件）
├── paper/                             # 中英文主稿/补充材料权威 Markdown、同步脚本与编译 PDF
├── figs/                              # 论文矢量图（图 1–图 6，PDF/SVG）
├── tests/                             # 统计口径与文稿完整性单元测试套件
└── docs/                              # RGB100 坐标协议与迁移校验记录
```

---

## 快速上手：审计自定义 API 端点

当前默认分析协议为 **`rgb100_v1_20261111`**（`parser_version = "3.0"`）：解析器从回复中提取 `#RRGGBB` 或 `R,G,B` 三元组，将 `0..255` 整数通道线性缩放为 `100 × RGB / 255`（`RGB100`）用于连续能量统计量，硬/软体素与精确色号保持原始编码网格。

1. 安装依赖（需 Python >= 3.11）：
   ```bash
   pip install -r requirements.txt
   ```
2. 参考 [config/targets.example.json](config/targets.example.json) 配置目标文件（通过 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY` 等环境变量注入凭证），先用 `--dry-run` 预览调度，再执行采集与离线分析：
   ```bash
   python3 collect.py --targets-config config/targets.example.json --prompts config/prompts.json --reps-t1 6 --reps-t0 0 --output /tmp/hueprint_audit.jsonl --dry-run
   python3 collect.py --targets-config config/targets.example.json --prompts config/prompts.json --reps-t1 6 --reps-t0 0 --output /tmp/hueprint_audit.jsonl
   python3 analyze.py --input /tmp/hueprint_audit.jsonl --output-json /tmp/hueprint_report.json
   ```

---

## 数据完整性与全量离线复现

支撑论文全部图表的 **15 份只读 JSONL 原始日志**（12 份基线 + 3 份 Study S5）、提示词/目标配置与冻结统计结果均由 [results/integrity_manifest.json](results/integrity_manifest.json)（**58 个基线文件**）、[extensions/live_validation_20261111/lv_rgb_integrity_manifest.json](extensions/live_validation_20261111/lv_rgb_integrity_manifest.json) 与 [extensions/competitor_benchmark_20261120/s5_integrity_manifest.json](extensions/competitor_benchmark_20261120/s5_integrity_manifest.json)（**10 个 Study S5 文件**）的 SHA-256 摘要锁定。`scripts/` 下的离线分析脚本安装 `sys.addaudithook` 阻断网络与子进程调用，在运行前后校验受保护摘要，并通过 `--output` 写入独立路径而不覆盖归档结果。

在项目根目录直接运行以下命令，即可将全部复算产物输出到独立临时目录，完成文稿与表格校验并执行全部单元测试：

```bash
OUT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hueprint-repro.XXXXXX")"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B reproduce_all.py --output "$OUT_DIR/reproduce_all_rgb_summary.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B extensions/live_validation_20261111/lv_analyze.py --dev-summary "$OUT_DIR/reproduce_all_rgb_summary.json" --output "$OUT_DIR/lv_rgb_results.json" --manifest "$OUT_DIR/lv_rgb_manifest.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B extensions/competitor_benchmark_20261120/s5_analyze.py --output "$OUT_DIR/s5_results.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/service_audit_analysis.py --output "$OUT_DIR/service_audit"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/energy_u_analysis.py --output "$OUT_DIR/energy_u"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/protocol_routing_analysis.py --output "$OUT_DIR/protocol_audit"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/perturbation_calibration_analysis.py --output "$OUT_DIR/perturbation_diagnostics.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/mmd_truncation_analysis.py --output "$OUT_DIR/subset_mmd_diagnostics.json" --exact-mmd-output "$OUT_DIR/exact_mmd_baselines.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/sensitivity_checks.py --output "$OUT_DIR/sensitivity_checks.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B scripts/operational_diagnostics.py --output "$OUT_DIR/operational_diagnostics.json"
python3 -B scripts/verify_manuscript.py
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B -m unittest discover -s tests -p 'test_*.py'
```

如需核验表块同步与 LaTeX 源码一致性（完整构建指南见 [paper/LATEX_README.md](paper/LATEX_README.md)）：

```bash
python3 -B paper/sync_supplement_inventory.py --check
python3 -B paper/sync_benchmark_tables.py --check
python3 -B paper/sync_service_tables.py --check
python3 -B paper/sync_s5_tables.py --check
python3 -B paper/build_latex.py --check
```

---

## 引用与许可

- **软件与分析脚本**：[MIT License](LICENSE)
- **论文文稿、图表、文档与实证 JSONL 数据集**：[CC BY 4.0](LICENSE)

机器可读引用元数据位于 [CITATION.cff](CITATION.cff) 与 [.zenodo.json](.zenodo.json)：

```bibtex
@misc{he2026hueprint,
  author       = {He, Xiguan and Li, Siqi},
  title        = {Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services},
  year         = {2026},
  howpublished = {Preprint and replication package},
  url          = {https://github.com/SoraStr/HuePrint}
}
```
