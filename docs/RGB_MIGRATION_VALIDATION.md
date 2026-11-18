# RGB 协议验证记录

日期：2026-11-11。协议：**`rgb100_v1_20261111`**。

主线采集、分析、复现和线上 S1–S4 统一使用编码 RGB。原始通道保存为 `0..255`，连续几何仅线性缩放为 `100 × RGB / 255`（RGB100）；无伽马逆展开、XYZ 或 CIELAB 转换。

## 已完成验证

- 9 项 RGB 流水线回归测试（`tests/test_rgb_pipeline.py`）通过：解析器 `3.0`、RGB 距离单位、归档字段隔离、边界微扰、新旧版本记录重解析与去重、无效样本隔离、线性 EER 计算、线上 EER 导出与跨协议阈值拒绝。
- 12 份正式语料 JSONL 日志完成离线重算：Datasets A–E 共 11,888 条去重记录，Studies S1–S4 共 22,640 条记录（合计 34,528 条去重响应），零在线模型 API 请求。
- `results/integrity_manifest.json`（58 个受保护文件）与 `extensions/live_validation_20261111/lv_rgb_integrity_manifest.json`（23 个锁定的线上语料与分析脚本，以及新增 `hybrid_reg` 后在 `results/service_audit/manifest.json` 锁定的 `analyze.py`）SHA-256 摘要校验全部一致。

## 重算结果示例

以下均为 `rgb100_v1_20261111` 协议下的 `energy_reg`，EER 使用线性 ROC 交点；固定阈值表现另列，不与重扫 EER 混淆。

| 场景 | AUC | 线性 EER | 补充 |
| --- | ---: | ---: | --- |
| B，40 单元 × 15 次采样 | 1.000000 | 0.00% | 同模型/异模型的奇偶半集比较 |
| S3，20 模型 × 10 探针 × 30 次采样 | 1.000000 | 0.00% | Top-1 20/20 |
| S3，查询端 ±8 RGB 微扰 | 1.000000 | 0.00% | Top-1 20/20；固定种子 |
| S1，同网关跨约三周，14 模型 | 1.000000 | 0.00% | 冻结 B3v3 阈值 FAR 2.20%，FRR 0.00% |
| S1，跨网关且跨约三周，14 模型 | 1.000000 | 0.00% | 冻结 B3v3 阈值 FAR/FRR 均为 0.00% |
| S2，跨供应商 6v6 | 0.926337 | 16.67% | 供应商标签定义的权重组近邻匹配 16/18 |
| S4b，隐式探针 3v3 | 0.991667 | 5.00% | Top-1 20/20 |
| E，持出模型队列 | 0.990000 | 10.00% | 冻结 B3v3 开发阈值 FAR 0.00%，FRR 30.00% |

## 关联文件

- [RGB 分析协议](RGB_PROTOCOL.md)
- [主线 RGB 结果](../data/reproduce_all_rgb_summary.json)
- [线上 RGB 结果](../extensions/live_validation_20261111/lv_rgb_results.json)
- [线上 SHA-256 清单](../extensions/live_validation_20261111/lv_rgb_integrity_manifest.json)
- [仓库完整性哈希清单](../results/integrity_manifest.json)
