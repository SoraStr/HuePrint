# 空谈无益，亮出颜色：面向聚合式大语言模型服务的低预算一致性审计

[English](README.md) | **简体中文**

本仓库为黑盒行为一致性审计框架 **HuePrint** 的官方实现、实证语料库（**34,528 条去重云端调用**）与全量离线复现包，对应论文《*Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services*》。

HuePrint 通过多语种结构化短颜色探针（`#RRGGBB` 与 `R,G,B`）采集模型输出分布，并在连续三维 RGB 几何空间（`RGB100`）上进行分布比对与假设检验，**无需模型权重、隐藏状态或服务端词元对数概率**，即可持续核验聚合网关端点是否兑现声明检查点（pinned-checkpoint）SLA 承诺。

---

## 论文与文档入口

- **英文主稿（12 页，IEEE Computer Society 排版）**：[paper/MANUSCRIPT_EN.md](paper/MANUSCRIPT_EN.md) · [paper/ieee/main.pdf](paper/ieee/main.pdf)（中文同步稿：[paper/MANUSCRIPT_ZH.md](paper/MANUSCRIPT_ZH.md)）
- **独立补充材料（16 页，完整数学证明、端点清单与扩展对照表）**：[paper/SUPPLEMENT_EN.md](paper/SUPPLEMENT_EN.md) · [paper/supplement/main.pdf](paper/supplement/main.pdf)（中文同步稿：[paper/SUPPLEMENT_ZH.md](paper/SUPPLEMENT_ZH.md)）
- **RGB100 坐标协议与迁移验证**：[docs/RGB_PROTOCOL.md](docs/RGB_PROTOCOL.md) · [docs/RGB_MIGRATION_VALIDATION.md](docs/RGB_MIGRATION_VALIDATION.md)
- **LaTeX 构建与预印本打包说明**：[paper/LATEX_README.md](paper/LATEX_README.md) · **34 篇参考文献核验清单**：[REFERENCE_AUDIT.md](REFERENCE_AUDIT.md)

---

## 核心实证结果速览（34,528 条云端响应，56 端点，12 个锁定后端）

- **浅预算高效区分**：在每侧 30 次调用（$K=10$）下，结构化颜色协议将清洁等错误率（EER）在开发队列（`B-20x6` 对照 `D`）上从单词基线题组的 `4.52%–5.23%` 降至 `0.94%–1.00%`，在 20 个锁参端点基准（Study S3，12,000 次调用）上从 `6.25%–8.04%` 降至 `3.49%–5.00%`，并在中等采样深度达到 `0.00%`。
- **连续与多尺度几何增益**：正则化能量距离 $\tilde D_{\mathrm{E\text{-}reg}}$ 在 56 端点浅层普查（Dataset A）上将精确色号离散散度（$D_{\mathrm{hex}}$）的 EER 减半（`5.36%` 对 `10.71%`）；多尺度混合量 $D_{\mathrm{hyb}}$ 将跨 12 家异构推理后端（Study S2）的开放权重 EER 从 `16.67%` 压低至 `5.93%`。在相隔约三周、跨越 `Cloudflare` 与 `OpenRouter` 双网关的复测（Study S1）中，基于距离分数的审计保持 `0.00%` 排序错误（而严格分布相等检验 $p\le 0.05$ 误拒最高 `42.86%` 的同模型对）。
- **理论扰动界与零 bootstrap U 比值**：统一的 Lipschitz 稳定性上界（单侧 $2\epsilon/\delta_0$、双侧 $4\epsilon/\delta_0$）同时覆盖 V 统计量与带符号/截断 U 统计量比值；注册自中心化将清洁持出集 E 误拒率从 `30.00%` 降至 `10.00%`（零误受），U 统计量比值则省去了 256 次注册 bootstrap 抽样。
- **低成本带外运行与隐式金丝雀**：单次审计查询估算 API 费用中位数低于 `0.04 USD`（150 次调用的 S3 情景中位数为 `0.0077–0.0345 USD`），预热后本地单线程 CPU 单对评分中位数仅 `0.08–0.31 ms`（999 次分层能量置换检验为 `2.39–10.15 ms`）；嵌入单行 CSS 与单字段 JSON 令牌的金丝雀探针（Study S4a）取得 `99.75%`（`3,192/3,200`）合法未触发通过率与 `0.00%` 能量核验 EER。

---

## 仓库目录结构

```text
HuePrint/
├── collect.py                    # 异步探针采集脚本（支持 OpenAI CC / Anthropic Messages）
├── analyze.py                    # 核心 RGB100 分析器（协议 rgb100_v1_20261111，解析器 3.0）
├── reproduce_all.py              # 离线基准复现入口（Datasets A–E）
├── config/                       # 探针题组（prompts*.json）、家族谱系映射与目标配置模板
├── data/                         # 5 份只读基准语料 JSONL（11,888 条唯一调用）
├── extensions/
│   └── live_validation_20261111/ # 7 份只读线上研究语料 JSONL（S1–S4，22,640 条调用）与 lv_analyze.py
├── scripts/                      # 离线统计审计、矢量图表绘制、完整性校验与 Zenodo 打包脚本
├── results/                      # 归档 CSV/JSON 结果与 integrity_manifest.json（58 个 SHA-256 锁定文件）
├── paper/                        # 中英文主稿/补充材料权威 Markdown、同步脚本与编译 PDF
├── figs/                         # 论文矢量图（图 1–图 6，PDF/SVG）
├── tests/                        # 40 项统计口径与文稿完整性单元测试
└── docs/                         # RGB100 坐标协议与迁移校验记录
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

支撑论文全部图表的 **12 份只读 JSONL 原始日志**、提示词/目标配置与冻结基准结果（共 **58 个受保护文件**）均由 [results/integrity_manifest.json](results/integrity_manifest.json) 的 SHA-256 摘要锁定（线上扩展源码校验见 [extensions/live_validation_20261111/lv_rgb_integrity_manifest.json](extensions/live_validation_20261111/lv_rgb_integrity_manifest.json)）。`scripts/` 下的离线分析脚本通过 `sys.addaudithook` 阻断网络与子进程调用，在运行前后校验受保护摘要，并通过 `--output` 写入独立路径而不覆盖归档结果。

在项目根目录直接运行以下命令，即可将全部复算产物输出到独立临时目录，完成文稿与表格校验并执行全部 40 项单元测试：

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

如需核验表块同步与 LaTeX 源码一致性（完整构建指南见 [paper/LATEX_README.md](paper/LATEX_README.md)）：

```bash
python3 -B paper/sync_supplement_inventory.py --check
python3 -B paper/sync_benchmark_tables.py --check
python3 -B paper/sync_service_tables.py --check
python3 -B paper/build_latex.py --check
```

---

## 引用与许可

- **软件与分析脚本**：[MIT License](LICENSE)
- **论文文稿、图表、文档与实证 JSONL 数据集**：[CC BY 4.0](LICENSE)

机器可读引用元数据位于 [CITATION.cff](CITATION.cff) 与 [.zenodo.json](.zenodo.json)：

```bibtex
@misc{he2026hueprint,
  author       = {He, Xiguan},
  title        = {Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services},
  year         = {2026},
  howpublished = {Preprint and replication package},
  url          = {https://github.com/SoraStr/HuePrint}
}
```
