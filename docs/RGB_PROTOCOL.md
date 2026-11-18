# 当前 RGB 分析协议

协议版本：**`rgb100_v1_20261111`**，定版日期：2026-11-11。代码中的完整协议元数据位于 `analyze.ANALYSIS_PROTOCOL`。本文说明主线采集、核验和线上扩展的坐标约定。

## 1. 从响应到特征

`collect.parse_color_response` 使用 **parser `3.0`**，从响应提取规范色号、原始 RGB 整数及语法和推理元数据。解析结果不生成 `lab` 字段。主线加载器兼容旧版归档输入，并从原始响应文本重新解析；任何旧版缓存字段均不参与几何计算，也无需改写原始 JSONL。

对颜色 `c = (R, G, B)`，原始通道范围为 `{0, …, 255}`，连续几何采用：

```text
x = 100 × c / 255
x ∈ [0, 100]³
```

本文将此坐标单位简称为 **RGB100**。这仍是编码后的 sRGB 通道，仅作全局线性缩放：没有 sRGB 伽马逆展开、XYZ 变换或 CIELAB 变换。原始 RGB 和 RGB100 之间的距离排序与角度由这种统一缩放保留，但 RGB100 欧氏距离不是感知色差，也不使用 `ΔE` 或 JND 名称。

## 2. 指标及尺度

| 指标或参数 | 当前定义与单位 |
| --- | --- |
| `hex_jsd` | 在规范色号类别上计算 JSD；不依赖连续坐标。 |
| `voxel_jsd` | 保留原始 RGB255 网格，每通道宽度 `32`，共 `8 × 8 × 8` 个硬体素。 |
| `soft_voxel_jsd` | 保留原始 RGB255 网格与三线性分配，网格宽度 `48`。 |
| Energy 几何 | 在 RGB100 点云上计算两点欧氏距离、交叉均距与组内均距。 |
| `energy_reg` 的 `delta0` | 固定为 `15.0` **RGB100 长度单位**。 |
| Gaussian Bures–Wasserstein 协方差正则 | 固定为 `1e-3 × I`，系数单位是 **RGB100 长度单位的平方**。 |
| `w2_norm` | `1 − exp(−W2 / 50.0)`；`50.0` 的单位是 **RGB100 长度单位**。 |
| `hybrid`、`robust_manifold` | 多尺度组合相异度，其中 Energy 分量使用上述 RGB100 几何；两者均不包含 W2 分量。 |

令 `dAB` 为两组点云的交叉平均距离，`dAA`、`dBB` 为各自的组内平均距离，正则化能量相异度为：

```text
energy_reg = max(0, dAB − (dAA + dBB) / 2) / (dAB + delta0)
```

它是有界统计相异度；此处不宣称归一化后满足三角不等式。原始 `energy_raw` 返回 `sqrt(max(0, 2 × dAB − dAA − dBB))`，不能把它的量纲与普通 RGB100 点间距离混为一谈。

## 3. 理论与解释边界

Energy 非负性与分布判别性，以及正则化形式的连续性论证，仅依赖所选欧氏空间的性质，不要求使用非线性色度图。若查询侧每个点在 **RGB100 欧氏距离**下移动不超过 `epsilon`，三角不等式推导给出 `energy_reg` 变化不超过 `2 × epsilon / delta0`；若两侧都发生这种幅度的扰动，相应上界为 `4 × epsilon / delta0`。

这类结论描述的是**输出坐标和统计量的数值稳定性**。它们不证明颜色读出保持模型隐藏状态的拓扑或充分信息，也不证明端点行为相似就等于真实权重相同。对原始 RGB 的固定逐通道扰动，须先转换单位再代入上述上界；例如三个通道各变化不超过 `a`，则 RGB100 欧氏位移不超过 `sqrt(3) × 100 × a / 255`。

## 4. 离线复现与校验

以下命令从项目根目录运行，将输出写入独立临时目录（保留归档文件不变），基于 12 份正式语料 JSONL 响应进行离线重算，不发起任何模型请求：

```bash
OUT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hueprint-rgb.XXXXXX")"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B reproduce_all.py --output "$OUT_DIR/reproduce_all_rgb_summary.json"
UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 uv run --offline --no-project --with numpy python -B extensions/live_validation_20261111/lv_analyze.py --dev-summary "$OUT_DIR/reproduce_all_rgb_summary.json" --output "$OUT_DIR/lv_rgb_results.json" --manifest "$OUT_DIR/lv_rgb_manifest.json"
```

| 用途 | RGB 协议输出文件 |
| --- | --- |
| 主线数据集（Datasets A–E）与预算、扰动分析 | `data/reproduce_all_rgb_summary.json` |
| 线上 S1–S4 扩展分析 | `extensions/live_validation_20261111/lv_rgb_results.json` |
| 语料与基准完整性哈希清单 | `results/integrity_manifest.json` |

读取结果报告时应检查 `analysis_protocol` 与 `analyze.ANALYSIS_PROTOCOL` 一致。线性 EER 使用 `eer_linear_raw`，离散 EER 使用 `eer_raw`，AUC 使用 `auc_raw`。检查范围与验证摘要见 [RGB 迁移验证记录](RGB_MIGRATION_VALIDATION.md)，关联文稿见 [中文主稿](../paper/MANUSCRIPT_ZH.md) 与 [英文主稿](../paper/MANUSCRIPT_EN.md)。
