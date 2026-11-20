# 《空谈无益，亮出颜色：面向聚合式大语言模型服务的低预算一致性审计》补充材料

本补充材料给出色彩坐标敏感性分析、固定权重正则化与旁路去混杂消融、完整端点标签、多语种探针原文、稳定性证明（含软体素平滑与引理 1）及扩展验证表（含 Study S5 同日竞品基准明细）。全部分析基于与主稿一致的 15 份冻结语料日志（12 份基线日志加 3 份 Study S5 日志，去重后共 38,688 条云端响应）。文献 [4]、[16]、[24]–[29] 沿用主稿编号，[30]–[34] 为补充材料专用文献。

## A. 色彩坐标变换与敏感性对照

**单射与 Lipschitz 色彩坐标变换。** 对有限 $256^3$ sRGB 网格上不作坐标舍入或分箱合并的任一单射映射 $\Phi:\Omega_{\mathrm{RGB}}\to\Omega_*\subset\mathbb R^3$，类别单射重命名保持精确色号 JSD（$D_{\mathrm{JSD}}(\Phi_\#P\|\Phi_\#Q)=D_{\mathrm{JSD}}(P\|Q)$）与命题 1 的支撑逃逸事件不变，有界 $\Omega_*$ 上的欧氏距离强负型性质 [26], [30] 则保证 $\tilde D_{\mathrm{E},\delta_*}(\Phi_\#P,\Phi_\#Q)=0\iff P=Q$（$\delta_*>0$）。若 $\|\Phi(x)-\Phi(x')\|_2\le L_{\max}\|x-x'\|_2$（$L_{\max}<\infty$），RGB100 中至多 $\epsilon$ 的位移在 $\Omega_*$ 中至多移动 $L_{\max}\epsilon$；代入命题 2 即得 $D_*(U,V)=\tilde D_{\mathrm{E},\delta_*}(\Phi(U),\Phi(V))$ 的单侧界 $2L_{\max}\epsilon/\delta_*$ 与双侧界 $4L_{\max}\epsilon/\delta_*$（对截断比值再以 $1$ 封顶）。

**统一缩放的 D65 CIELAB 对照。** 标准 D65 相对 sRGB 到 CIELAB 转换 [24], [31], [32]（分段线性/幂次传递，不作 D50 色适应）在 8 比特网格上单射，但其感知非线性形变会相对无形变的 RGB100 坐标（$L_{\max}=1$）改变有限样本能量排序。表 S1 采用仅由 B-20×6 注册集单元内配对距离拟合的单一冻结各向同性缩放因子（$0.7658$），将 $\delta_0=15$ 映射至原生 CIELAB 的 $\delta_*=19.59$，不作逐通道缩放或裁剪。

**表 S1：正则化能量在 RGB100 与统一缩放 CIELAB 中的 EER / AUC**

<!-- BENCH_TABLE_charts -->
| 数据 | 条件 | RGB100 EER / AUC | CIELAB EER / AUC |
| --- | --- | --- | --- |
| B_full | clean | 0.00% / 1.0000 | 0.00% / 1.0000 |
| B_full | ±8 | 0.00% / 1.0000 | 0.00% / 1.0000 |
| B20x6 | clean | 0.00% / 1.0000 | 0.00% / 1.0000 |
| B20x6 | ±8 | 0.44% / 0.9994 | 0.56% / 0.9994 |
| E | clean | 10.00% / 0.9900 | 10.00% / 0.9889 |
| E | ±8 | 10.00% / 0.9882 | 10.00% / 0.9831 |
| S3 | clean | 0.00% / 1.0000 | 0.53% / 0.9997 |
| S3 | ±8 | 0.00% / 1.0000 | 0.53% / 0.9994 |
<!-- /BENCH_TABLE_charts -->



## B. 固定权重的正则化对照

此处 $D_{\mathrm{hyb-reg}} = 0.35 D_{\mathrm{vox}} + 0.25 D_{\mathrm{hex}} + 0.25 \tilde D_{\mathrm{E-reg}} + 0.15 D_{\mathrm{side}}$ 将 $D_{\mathrm{hyb}}$ 中的未正则化能量项 $\bar D_{\mathrm E}$ 替换为 $\tilde D_{\mathrm{E-reg}}$，并保持四项混合权重 $(0.35, 0.25, 0.25, 0.15)$ 不变（主稿第 3.3 节式 (3)）。

**表 S2：固定权重正则化对照的线性 EER**

<!-- BENCH_TABLE_hybrid -->
| 协议 | $\bar D_{\mathrm E}$ | $\tilde D_{\mathrm{E-reg}}$ | $D_{\mathrm{hyb}}$ | $D_{\mathrm{hyb-reg}}$ |
| --- | --- | --- | --- | --- |
| A | 4.77% | 5.36% | 7.14% | 8.93% |
| B 20×6 | 0.00% | 0.00% | 0.00% | 0.00% |
| B 40×15 | 0.00% | 0.00% | 0.00% | 0.00% |
| C P1 within | 0.00% | 0.00% | 0.00% | 0.00% |
| C P2 within | 0.00% | 1.11% | 0.00% | 1.11% |
| C P0 → P1 | 20.00% | 17.78% | 10.00% | 10.00% |
| C P0 → P2 | 20.00% | 11.11% | 10.00% | 7.78% |
| C pooled | 16.67% | 15.56% | 10.00% | 10.00% |
| E | 0.00% | 10.00% | 4.44% | 5.56% |
| S1 CF0 → CF21 | 0.00% | 0.00% | 0.00% | 0.00% |
| S1 CF21 → OR21 | 0.00% | 0.00% | 0.00% | 0.00% |
| S1 CF0 → OR21 | 0.00% | 0.00% | 0.00% | 0.00% |
| S1 CF21 within | 0.55% | 3.85% | 1.65% | 3.30% |
| S1 OR21 within | 0.00% | 0.00% | 0.00% | 0.00% |
| S2 provider 6v6 | 16.67% | 16.67% | 5.93% | 8.15% |
| S2 provider 3v3 | 16.30% | 16.67% | 12.59% | 15.19% |
| S3 color 15v15 | 0.00% | 0.00% | 0.53% | 1.58% |
| S4a 5v5 | 0.00% | 0.00% | 1.58% | 3.95% |
| S4b 3v3 | 5.00% | 5.00% | 8.95% | 10.00% |
| S3a → S4b 6v6 | 15.00% | 15.00% | 13.68% | 12.63% |
<!-- /BENCH_TABLE_hybrid -->

D 为单词响应，颜色能量与颜色混合量在其上无定义。多成员家族端点（A 中 50/56、E 中 9/10，剔除单成员家族模型）上的留一法家族归属表现亦不同于二元核验：将能量正则化（$\bar D_{\mathrm E}\to\tilde D_{\mathrm{E-reg}}$）使准确率在 A 上从 31/50 升至 35/50（两种混合量均为 36/50），在 E 上从 2/9 升至 6/9（两种混合量均为 7/9）。

**语法与推理计费信封去混杂消融。** 在 $D_{\mathrm{side}}$ 中，当有效 `#RRGGBB` 色号仅由数字 `0`–`9` 构成时（占 RGB 立方体的 $10^6/16^6 \approx 5.96\%$），十六进制大小写标签记为 `numeric_only`；推理长度分箱则在 API 计费信封返回 `usage.reasoning_tokens` 时优先读取该字段，否则回退到可见推理字符数（`perturbation_diagnostics.json`）。

第一，仅移除 API 推理元数据（剥离 `explicit_reasoning` 与 `usage.reasoning_tokens`，即 `content_only_no_envelope`）使跨网关 S1（`CF0 → OR21`，其中 OpenRouter 返回 `reasoning_tokens` 而 Cloudflare 省略该字段）的同模型正例均值 $D_{\mathrm{side}}$ 从 0.1118 降至 0.0161。在跨 12 家指定宿主后端的 Study S2 上（`operational_diagnostics.json`），`content_only_no_envelope` 下 6v6 $D_{\mathrm{hyb}}$ EER 维持在 5.93% 不变（0.9864 AUC，17/18 Top-1；3v3 为 12.59% EER），S4a（5v5）上的 $D_{\mathrm{hyb}}$ EER 从 1.58% 升至 2.89%，而 $\tilde D_{\mathrm{E-reg}}$ 保持 0.00%（对应主稿第 5.4 与第 6.2 节）。第二，再把 `numeric_only` 合并到 `upper`（`pure_content_syntax`）时，Study S2 的 6v6 $D_{\mathrm{hyb}}$ EER 为 5.56%（0.9864 AUC，17/18 Top-1；3v3 为 12.96%），S4a 上为 2.63%（$\tilde D_{\mathrm{E-reg}}$ 仍为 0.00%），S1（`CF0 → OR21`）同模型正例均值 $D_{\mathrm{side}}$ 降至 0.0064；单独 $D_{\mathrm{side}}$ 的 AUC/线性 EER 在 Dataset A 上从 0.7804/30.32% 降至 0.6557/36.76%，在 Dataset B（$40\times 15$）上从 0.9722/10.00% 降至 0.6933/36.00%。第三，彻底移除 $D_{\mathrm{side}}$ 并将三项纯颜色距离权重重归一化为 $(0.35, 0.25, 0.25)/0.85$（`color_composite_no_side`）时，Study S2 的 6v6 EER 仍达 9.63%（0.9749 AUC，17/18 Top-1；3v3 为 14.44%），优于单尺度 $\tilde D_{\mathrm{E-reg}}$ 与 Color MMD-U（均为 16.67%）。

<!-- SUPPLEMENT_INVENTORY -->

## C. 完整端点清单与标签来源

本表完整列出数据集 A 的 56 个端点，每端点 48 条响应。标识符、声明模型名与返回模型名均逐字取自冻结 API 响应日志；家族与厂商分组取自版本化的 `config/family_map.json`。

来源：`data/census_40models.jsonl`（56 个端点，2,688 条记录）及 `config/family_map.json`。`CF-W` 表示 Cloudflare Workers AI；`CF-G` 表示 Cloudflare AI Gateway。日志中的 provider 字段在 CF-G 行仅为目标别名，不能据此推断独立后端。

**表 S3：Dataset A 端点标签**

| 端点 ID / 声明模型 | 返回模型标签 | 来源 | 厂商 / 家族 |
| --- | --- | --- | --- |
| `cf-deepseek-v4.1-flash-cot` / `@cf/deepseek-ai/deepseek-v4.1-flash-1017` | `@cf/deepseek-ai/deepseek-v4.1-flash-1017` | CF-W | `deepseek` / `deepseek` |
| `cf-gemma-sea-lion-v4-27b` / `@cf/aisingapore/gemma-sea-lion-v4-27b-it` | `@cf/aisingapore/gemma-sea-lion-v4-27b-it` | CF-W | `aisingapore` / `google-gemma-gemini` |
| `cf-glm-4.7-flash` / `@cf/zai-org/glm-4.7-flash` | `@cf/zai-org/glm-4.7-flash` | CF-W | `zhipu` / `glm` |
| `cf-gpt-oss-120b-cot` / `@cf/openai/gpt-oss-120b` | `@cf/openai/gpt-oss-120b` | CF-W | `openai` / `openai-gpt` |
| `cf-granite-4.0-h-micro` / `@cf/ibm-granite/granite-4.0-h-micro` | `@cf/ibm-granite/granite-4.0-h-micro` | CF-W | `ibm` / `ibm-granite` |
| `cf-kimi-k2.7-code-cot` / `@cf/moonshotai/kimi-k2.7-code` | `@cf/moonshotai/kimi-k2.7-code` | CF-W | `moonshot` / `kimi` |
| `cf-llama-3.1-8b-fp8` / `@cf/meta/llama-3.1-8b-instruct-fp8` | `@cf/meta/llama-3.1-8b-instruct-fp8` | CF-W | `meta` / `meta-llama` |
| `cf-llama-3.1-8b-legacy` / `@cf/meta/llama-3.1-8b-instruct` | `@cf/meta/llama-3.1-8b-fast-v2` | CF-W | `meta` / `meta-llama` |
| `cf-llama-3.2-1b` / `@cf/meta/llama-3.2-1b-instruct` | `@cf/meta/llama-3.2-1b-instruct` | CF-W | `meta` / `meta-llama` |
| `cf-llama-3.2-3b` / `@cf/meta/llama-3.2-3b-instruct` | `@cf/meta/llama-3.2-3b-instruct-v2` | CF-W | `meta` / `meta-llama` |
| `cf-llama-3.3-70b-fp8-fast` / `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | `@cf/meta/llama-3.3-70b-instruct-sd` | CF-W | `meta` / `meta-llama` |
| `cf-llama-4-scout-17b` / `@cf/meta/llama-4-scout-17b-16e-instruct` | `@cf/meta/llama-4-scout-17b-16e-instruct` | CF-W | `meta` / `meta-llama` |
| `cf-mistral-small-3.1-24b` / `@cf/mistralai/mistral-small-3.1-24b-instruct` | `@cf/mistralai/mistral-small-3.1-24b-v2` | CF-W | `mistral` / `mistral` |
| `cf-phonellm-mini-alpha-2` / `@cf/daily-co/phonellm-mini-alpha-2` | `@cf/daily-co/phonellm-mini-alpha-2` | CF-W | `daily-co` / `phonellm` |
| `cf-qwen2.5-coder-32b` / `@cf/qwen/qwen2.5-coder-32b-instruct` | `@cf/qwen/qwen2.5-coder-32b-instruct` | CF-W | `alibaba` / `qwen` |
| `cf-qwen3-30b-a3b-fp8` / `@cf/qwen/qwen3-30b-a3b-fp8` | `@cf/qwen/qwen3-30b-a3b-fp8` | CF-W | `alibaba` / `qwen` |
| `gw-claude-fable-5` / `anthropic/claude-fable-5` | `claude-fable-5` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-fable-5.1` / `anthropic/claude-fable-5.1` | `claude-fable-5-1` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-haiku-4.5` / `anthropic/claude-haiku-4.5` | `claude-haiku-4-5-20251001` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-haiku-5.5` / `anthropic/claude-haiku-5.5` | `claude-haiku-5-5` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-opus-4.5` / `anthropic/claude-opus-4.5` | `claude-opus-4-5-20251101` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-opus-4.6` / `anthropic/claude-opus-4.6` | `claude-opus-4-6` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-opus-4.7` / `anthropic/claude-opus-4.7` | `claude-opus-4-7` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-opus-4.8` / `anthropic/claude-opus-4.8` | `claude-opus-4-8` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-opus-5` / `anthropic/claude-opus-5` | `claude-opus-5` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-opus-5.5` / `anthropic/claude-opus-5.5` | `claude-opus-5-5` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-sonnet-4.5` / `anthropic/claude-sonnet-4.5` | `claude-sonnet-4-5-20250929` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-sonnet-4.6` / `anthropic/claude-sonnet-4.6` | `claude-sonnet-4-6` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-claude-sonnet-5` / `anthropic/claude-sonnet-5` | `claude-sonnet-5` | CF-G | `anthropic` / `anthropic-claude` |
| `gw-gemini-2.5-flash` / `google/gemini-2.5-flash` | `gemini-2.5-flash` | CF-G | `google` / `google-gemma-gemini` |
| `gw-gemini-2.5-flash-lite` / `google/gemini-2.5-flash-lite` | `gemini-2.5-flash-lite` | CF-G | `google` / `google-gemma-gemini` |
| `gw-gemini-2.5-pro` / `google/gemini-2.5-pro` | `gemini-2.5-pro` | CF-G | `google` / `google-gemma-gemini` |
| `gw-gemini-3.1-flash-lite` / `google/gemini-3.1-flash-lite` | `gemini-3.1-flash-lite` | CF-G | `google` / `google-gemma-gemini` |
| `gw-gemini-3.1-pro` / `google/gemini-3.1-pro` | `gemini-3.1-pro-preview` | CF-G | `google` / `google-gemma-gemini` |
| `gw-gemini-3.5-flash` / `google/gemini-3.5-flash` | `gemini-3.5-flash` | CF-G | `google` / `google-gemma-gemini` |
| `gw-gemini-3.6-flash` / `google/gemini-3.6-flash` | `gemini-3.6-flash` | CF-G | `google` / `google-gemma-gemini` |
| `gw-gemini-3.7-flash` / `google/gemini-3.7-flash` | `gemini-3.7-flash` | CF-G | `google` / `google-gemma-gemini` |
| `gw-gemini-3.8-flash` / `google/gemini-3.8-flash` | `gemini-3.8-flash` | CF-G | `google` / `google-gemma-gemini` |
| `gw-gemini-4-argon` / `google/gemini-4-argon` | `gemini-4-argon` | CF-G | `google` / `google-gemma-gemini` |
| `gw-gpt-4.1` / `openai/gpt-4.1` | `gpt-4.1-2025-04-14` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-4.1-mini` / `openai/gpt-4.1-mini` | `gpt-4.1-mini-2025-04-14` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-4o` / `openai/gpt-4o` | `gpt-4o-2024-08-06` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-4o-mini` / `openai/gpt-4o-mini` | `gpt-4o-mini-2024-07-18` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-5.1` / `openai/gpt-5.1` | `gpt-5.1-2025-11-13` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-5.2` / `openai/gpt-5.2` | `gpt-5.2-2025-12-11` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-5.4` / `openai/gpt-5.4` | `gpt-5.4-2026-03-05` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-5.4-mini` / `openai/gpt-5.4-mini` | `gpt-5.4-mini-2026-03-17` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-5.4-nano` / `openai/gpt-5.4-nano` | `gpt-5.4-nano-2026-03-17` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-5.5` / `openai/gpt-5.5` | `gpt-5.5-2026-04-23` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-5.6-luna` / `openai/gpt-5.6-luna` | `gpt-5.6-luna` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-5.6-sol` / `openai/gpt-5.6-sol` | `gpt-5.6-sol` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-5.6-terra` / `openai/gpt-5.6-terra` | `gpt-5.6-terra` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-6-astra` / `openai/gpt-6-astra` | `gpt-6-astra` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-6-luna` / `openai/gpt-6-luna` | `gpt-6-luna` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-6-sol` / `openai/gpt-6-sol` | `gpt-6-sol` | CF-G | `openai` / `openai-gpt` |
| `gw-gpt-6.1-sol` / `openai/gpt-6.1-sol` | `gpt-6.1-sol` | CF-G | `openai` / `openai-gpt` |

## D. 核心 40 单元多语言探针原文

来源：`config/prompts.json`. 10 项任务，4 种语言，40 个单元。以下引文保留原始 Unicode 文本；每个用户提示配合同格式、同语言的系统提示使用。

### 系统提示

**hex**

**en:** You are a direct-response assistant. Respond with ONLY a single hex color code in #RRGGBB format. No words, no explanation, no punctuation.

**zh:** 你是一个直接回答的助手。请仅回复一个 #RRGGBB 格式的十六进制颜色代码。不要包含任何文字、解释或标点符号。

**ru:** Вы — ассистент, отвечающий напрямую. Ответьте ТОЛЬКО одним шестнадцатеричным кодом цвета в формате #RRGGBB. Без слов, без объяснений, без знаков препинания.

**ar:** أنت مساعد يجيب بشكل مباشر. أجب فقط برمز لون سداسي عشري واحد بتنسيق #RRGGBB. بدون كلمات، بدون شرح، بدون علامات ترقيم.

**rgb_triplet**

**en:** You are a direct-response assistant. Respond with ONLY three integers from 0 to 255 separated by commas in R,G,B format. No words, no explanation, no parentheses.

**zh:** 你是一个直接回答的助手。请仅按 R,G,B 格式回复三个用逗号分隔的 0 到 255 之间的整数。不要包含任何文字、解释或括号。

**ru:** Вы — ассистент, отвечающий напрямую. Ответьте ТОЛЬКО тремя целыми числами от 0 до 255 через запятую в формате R,G,B. Без слов, без объяснений, без скобок.

**ar:** أنت مساعد يجيب بشكل مباشر. أجب فقط بثلاثة أعداد صحيحة من 0 إلى 255 مفصولة بفواصل بتنسيق R,G,B. بدون كلمات، بدون شرح، بدون أقواس.

### 用户提示

**hex_random** (hex; random)

**en:** Pick a random color. Reply with only its #RRGGBB hex code.

**zh:** 随机选一种颜色。仅回复它的 #RRGGBB 十六进制代码。

**ru:** Выберите случайный цвет. Ответьте только его кодом #RRGGBB.

**ar:** اختر لونًا عشوائيًا. أجب فقط برمزه #RRGGBB.

**hex_favorite** (hex; favorite)

**en:** What is your favorite color? Reply with only its #RRGGBB hex code.

**zh:** 你最喜欢什么颜色？仅回复它的 #RRGGBB 十六进制代码。

**ru:** Какой ваш любимый цвет? Ответьте только его кодом #RRGGBB.

**ar:** ما هو لونك المفضل؟ أجب فقط برمزه #RRGGBB.

**rgb_random** (rgb_triplet; random)

**en:** Pick a random color. Reply with only its R,G,B values (0-255).

**zh:** 随机选一种颜色。仅回复它的 R,G,B 数值（0-255）。

**ru:** Выберите случайный цвет. Ответьте только его значениями R,G,B (0-255).

**ar:** اختر لونًا عشوائيًا. أجب فقط بقيم R,G,B الخاصة به (0-255).

**rgb_favorite** (rgb_triplet; favorite)

**en:** What is your favorite color? Reply with only its R,G,B values (0-255).

**zh:** 你最喜欢什么颜色？仅回复它的 R,G,B 数值（0-255）。

**ru:** Какой ваш любимый цвет? Ответьте только его значениями R,G,B (0-255).

**ar:** ما هو لونك المفضل؟ أجب فقط بقيم R,G,B الخاصة به (0-255).

**hex_warm** (hex; semantic_anchor)

**en:** Name a warm sunset color. Reply with only its #RRGGBB hex code.

**zh:** 给出一种温暖的日落颜色。仅回复它的 #RRGGBB 十六进制代码。

**ru:** Назовите теплый цвет заката. Ответьте только его кодом #RRGGBB.

**ar:** سمِّ لون غروب دافئ. أجب فقط برمزه #RRGGBB.

**hex_nature** (hex; semantic_anchor)

**en:** Name a forest green color. Reply with only its #RRGGBB hex code.

**zh:** 给出一种森林绿颜色。仅回复它的 #RRGGBB 十六进制代码。

**ru:** Назовите лесной зеленый цвет. Ответьте только его кодом #RRGGBB.

**ar:** سمِّ لونًا أخضر غابيًا. أجب فقط برمزه #RRGGBB.

**hex_ocean** (hex; semantic_anchor)

**en:** Name a deep ocean color. Reply with only its #RRGGBB hex code.

**zh:** 给出一种深海颜色。仅回复它的 #RRGGBB 十六进制代码。

**ru:** Назовите цвет глубокого океана. Ответьте только его кодом #RRGGBB.

**ar:** سمِّ لون المحيط العميق. أجب فقط برمزه #RRGGBB.

**hex_calm** (hex; semantic_anchor)

**en:** What color best represents calmness? Reply with only its #RRGGBB hex code.

**zh:** 什么颜色最能代表平静？仅回复它的 #RRGGBB 十六进制代码。

**ru:** Какой цвет лучше всего олицетворяет спокойствие? Ответьте только его кодом #RRGGBB.

**ar:** ما هو اللون الذي يمثل الهدوء بشكل أفضل؟ أجب فقط برمزه #RRGGBB.

**hex_night** (hex; semantic_anchor)

**en:** Name a midnight sky color. Reply with only its #RRGGBB hex code.

**zh:** 给出一种午夜星空的颜色。仅回复它的 #RRGGBB 十六进制代码。

**ru:** Назовите цвет полуночного неба. Ответьте только его кодом #RRGGBB.

**ar:** سمِّ لون سماء منتصف الليل. أجب فقط برمزه #RRGGBB.

**rgb_warm** (rgb_triplet; semantic_anchor)

**en:** Name a warm sunset color. Reply with only its R,G,B values (0-255).

**zh:** 给出一种温暖的日落颜色。仅回复它的 R,G,B 数值（0-255）。

**ru:** Назовите теплый цвет заката. Ответьте только его значениями R,G,B (0-255).

**ar:** سمِّ لون غروب دافئ. أجب فقط بقيم R,G,B الخاصة به (0-255).


## E. S4a CSS 与 JSON 金丝雀探针原文

来源：`config/prompts.implicit_css.json`. 8 项任务，2 种语言，16 个单元。以下引文保留原始 Unicode 文本；每个用户提示配合同格式、同语言的系统提示使用。

### 系统提示

**hex**

**en:** You are a frontend UI engineer configuring web stylesheets and JSON design tokens. Keep code snippets minimal and practical.

**zh:** 你是一名负责配置网页样式表与 JSON 设计变量的前端 UI 工程师。请保持代码片段简洁实用。

### 用户提示

**imp_brand_primary** (hex; implicit_ui)

**en:** Write a 1-line CSS custom property declaration setting --brand-primary to a 6-digit hex color you find appealing for a modern SaaS workspace.

**zh:** 请写一行 CSS 自定义属性声明，为现代 SaaS 工作台将 --brand-primary 设置为一个你认为耐看的 6 位十六进制色号。

**imp_hero_sunset** (hex; implicit_ui)

**en:** Provide a 1-line CSS variable declaration (--hero-glow: #...;) evoking a warm evening sunset.

**zh:** 请提供一行体现傍晚温暖日落氛围的 CSS 变量声明（--hero-glow: #...;）。

**imp_forest_badge** (hex; implicit_ui)

**en:** Return a compact 1-field JSON token {"badgeFoliage": "#..."} using a deep forest green 6-digit hex shade.

**zh:** 请返回一个使用深邃森林绿 6 位十六进制色号的单字段 JSON 配置 {"badgeFoliage": "#..."}。

**imp_ocean_surface** (hex; implicit_ui)

**en:** Write a single CSS variable declaration (--ocean-surface: #...;) inspired by deep ocean water.

**zh:** 请写一行灵感源自深海海水色彩的 CSS 变量声明（--ocean-surface: #...;）。

**imp_calm_card** (hex; implicit_ui)

**en:** Output a 1-field JSON design token {"calmSurface": "#..."} with a soothing, tranquil 6-digit hex color for a reading app.

**zh:** 请为阅读应用输出一个带有宁静舒缓 6 位十六进制色彩的单字段 JSON 设计变量 {"calmSurface": "#..."}。

**imp_night_canvas** (hex; implicit_ui)

**en:** Provide a 1-line CSS custom property (--night-canvas: #...;) capturing a midnight starlit sky.

**zh:** 请提供一行表现午夜星空色彩的 CSS 自定义属性（--night-canvas: #...;）。

**imp_avatar_tint** (hex; implicit_ui)

**en:** Generate a 1-field JSON snippet {"avatarTint": "#..."} with a fresh 6-digit hex accent color for a default user avatar.

**zh:** 请生成一个带有清新 6 位十六进制点缀色的默认头像单字段 JSON 片段 {"avatarTint": "#..."}。

**imp_cta_warm** (hex; implicit_ui)

**en:** Write a 1-line CSS declaration (--cta-warm: #...;) suitable for an energetic warm call-to-action button.

**zh:** 请写一行适合活力暖色调行动号召按钮的 CSS 属性声明（--cta-warm: #...;）。


## F. S4b 对照探针原文

来源：`config/prompts.implicit_v5_exact.json`. 8 项任务，2 种语言，16 个单元。以下引文保留原始 Unicode 文本；每个用户提示配合同格式、同语言的系统提示使用。

### 系统提示

**hex**

**en:** You are a concise web styling assistant. Reply with only the requested CSS/HTML hexadecimal color literal.

**zh:** 你是一个简洁的网页样式助手。请仅回复所要求的网页十六进制色值。

**rgb_triplet**

**en:** You are a concise graphics assistant. Reply with only the three comma-separated 0-255 channel integers.

**zh:** 你是一个简洁的图形助手。请仅回复三个用逗号分隔的0到255通道整数。

### 用户提示

**hex_favorite** (hex; favorite)

**en:** Write a 6-character CSS hex color value for your favorite shade, prefixed with a hash symbol.

**zh:** 请输出一个代表你最喜欢颜色的6位网页十六进制色号（带井号）。

**hex_ocean** (hex; semantic_anchor)

**en:** Output a web color code (hash followed by six hex digits) representing a deep ocean.

**zh:** 给出一个代表深海颜色的6位HTML十六进制色值。

**hex_warm** (hex; semantic_anchor)

**en:** Give me a warm sunset shade as a standard 6-digit HTML hex string.

**zh:** 用标准6位CSS十六进制颜色代码表示温暖的日落色。

**hex_calm** (hex; semantic_anchor)

**en:** What color represents calmness? Answer only with a CSS hex literal.

**zh:** 什么颜色最代表平静？仅回复带井号的6位十六进制色号。

**hex_nature** (hex; semantic_anchor)

**en:** Provide a forest green shade as a 6-character hexadecimal color literal.

**zh:** 给出一种森林绿的6位网页十六进制颜色值。

**hex_random** (hex; random)

**en:** Pick a random shade and return only its 6-digit CSS hex string.

**zh:** 随机选一种颜色，仅输出其带井号的6位十六进制色值。

**hex_night** (hex; semantic_anchor)

**en:** Name a midnight sky shade as a standard HTML hex color literal.

**zh:** 用带井号的6位十六进制颜色代码表示午夜星空。

**rgb_favorite** (rgb_triplet; favorite)

**en:** Give three comma-separated 8-bit channel values (0 to 255) for your favorite color.

**zh:** 用三个逗号分隔的0到255整数表示你最喜欢的颜色通道值。

<!-- /SUPPLEMENT_INVENTORY -->

## G. 稳定性证明、软体素基线与高斯对照

*命题 1 的证明。* 记 $q=Q^{\mathrm{jitter}}(\Omega\setminus\operatorname{supp}(P_{\mathrm{ref}}))\ge t$；当 $\operatorname{supp}(P_{\mathrm{src}})\subseteq\{a,\ldots,255-a\}^3$ 时，每个源色号产生 $(2a+1)^3$ 个等概率结果，其中至多 $r$ 个落入 $\operatorname{supp}(P_{\mathrm{ref}})$，故 $q\ge\max(0,1-r/(2a+1)^3)$。由 $Q\mapsto D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q)$ 的凸性及 $\mathbb E[\hat Q_n^{\mathrm{jitter}}]=Q^{\mathrm{jitter}}$，Jensen 不等式给出 $\mathbb E[D_{\mathrm{hex}}(P_{\mathrm{ref}},\hat Q_n^{\mathrm{jitter}})]\ge D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})$（主稿图 3(a) 在固定已观察到的清洁查询颜色后对每次观测各加一次独立随机扰动，条件下即将 $P_{\mathrm{src}}$ 取为查询经验直方图并求期望）。以指示映射 $T(x)=\mathbf 1[x\notin\operatorname{supp}(P_{\mathrm{ref}})]$ 作二元粗化，将 $P_{\mathrm{ref}}$ 映射为 $(1,0)$、$Q^{\mathrm{jitter}}$ 映射为 $(1-q,q)$；因 $D_{\mathrm{JSD}}$ 是带严格凸生成元的 Csiszár $f$-散度 [33]，数据处理不等式给出 $D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})\ge D_{\mathrm{JSD}}((1,0)\|(1-q,q))=\psi(q)$（$\psi$ 见主稿式 (1)）。在 $(0,1)$ 上 $\psi'(q)=\tfrac12\big(1-\log_2\tfrac{2(1-q)}{2-q}\big)>\tfrac12>0$，故 $\psi(q)\ge\psi(t)\ge t/2$。等式 $D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})=\psi(t)$ 成立当且仅当 $q=t$ 且在 $\operatorname{supp}(P_{\mathrm{ref}})$ 上恒有 $Q^{\mathrm{jitter}}(x)=(1-t)P_{\mathrm{ref}}(x)$，任一内部单点参考均可取到等号（$r=1$；如 $a=1, t=26/27$ 时 $D_{\mathrm{JSD}}=\psi(26/27)\approx0.8847$）。$\blacksquare$

*命题 2 的证明。* 记跨组均距 $d=d_{UV}\ge 0$；对 V 统计量（$n,m\ge 1$，含对角项）令 $h=\tfrac12(d_{UU}+d_{VV})$，对 U 统计量（$n,m\ge 2$，排除对角项 [27]）令 $h=\tfrac12(\tilde d_{UU}+\tilde d_{VV})$，其中 $\tilde d_{UU}=\frac{n}{n-1}d_{UU}$、$\tilde d_{VV}=\frac{m}{m-1}d_{VV}$。将三角不等式 $\|u_i-u_{i'}\|_2\le\|u_i-v_j\|_2+\|u_{i'}-v_j\|_2$ 关于 $j\in\{1,\ldots,m\}$ 及全部 $(i,i')$ 或非对角 $i\ne i'$ 求平均，可得 $0\le d_{UU},\tilde d_{UU}\le 2d_{UV}$，对称地 $0\le d_{VV},\tilde d_{VV}\le 2d_{UV}$，故两种取法均有 $(d,h)\in\mathcal C=\{(d,h)\in\mathbb R^2:d\ge 0,\;0\le h\le 2d\}$。区域 $\mathcal C$ 是凸锥，当 $\delta_0>0$ 时，$F(d,h)=(d-h)/(d+\delta_0)$ 在 $\mathcal C$ 上光滑，且满足
$$\left|\frac{\partial F}{\partial d}\right|=\frac{h+\delta_0}{(d+\delta_0)^2}\le\frac{2d+\delta_0}{(d+\delta_0)^2}=\frac{(d+\delta_0)^2-d^2}{\delta_0(d+\delta_0)^2}\le\frac{1}{\delta_0},\qquad\left|\frac{\partial F}{\partial h}\right|=\frac{1}{d+\delta_0}\le\frac{1}{\delta_0}.$$
若只移动 $V$ 中各点且每点欧氏位移至多 $\epsilon$（$\|v'_j-v_j\|_2\le\epsilon$），每个跨组距离变化至多 $\epsilon$，每个 $V$ 内点对距离变化至多 $2\epsilon$（对角项为 $0$）而 $U$ 内距离不变，故 $|d'-d|\le\epsilon$、$|h'-h|\le\epsilon$。沿凸锥 $\mathcal C$ 中连接 $(d,h)$ 与 $(d',h')$ 的线段利用偏导上界积分（有限增量界），得 $|F(d',h')-F(d,h)|\le(|d'-d|+|h'-h|)/\delta_0\le 2\epsilon/\delta_0$，由此一次给出 $\tilde D_{\mathrm{E-reg}}$（因 $\widehat{\mathcal E}_V^2\ge 0$ [26]）和带符号 U 比值的单侧界 $2\epsilon/\delta_0$。因取正部 $z\mapsto[z]_+=\max(0,z)$ 是 $1$-Lipschitz 映射且 $d+\delta_0>0$，截断 U 比值 $[F(d,h)]_+=[\widehat{\mathcal E}_U^2]_+/(2d_{UV}+2\delta_0)$ 同样满足 $|[F(d',h')]_+-[F(d,h)]_+|\le|F(d',h')-F(d,h)|\le 2\epsilon/\delta_0$；又由 $h\ge 0$ 与 $\delta_0>0$ 知 $0\le[F(d,h)]_+\le d/(d+\delta_0)<1$，故严格小于 $1$ 的是截断后的比值。依次移动两侧 $(U,V)\to(U,V')\to(U',V')$ 即得双侧界 $4\epsilon/\delta_0$。$\blacksquare$

### 软体素平滑、多尺度复合与引理 1

作为连续 RGB 能量的平滑直方图对照，固定原始 8 比特通道单位下的网格步长 $w=48$ 与格点集 $\mathcal I=\{0,\ldots,6\}^3$，定义三线性帐篷核权重
$$W_i(\mathbf c)=\prod_{d\in\{R,G,B\}}\max(0,1-|c_d/w-i_d|),\qquad P_{\mathrm{soft}}(i\mid S)=|S|^{-1}\sum_{\mathbf c\in S}W_i(\mathbf c).$$
因 $255/w=5.3125<6$，在 $[0,255]^3$ 上恒有 $W_i(\mathbf c)\ge 0$ 且 $\sum_{i\in\mathcal I}W_i(\mathbf c)=1$，故 $P_{\mathrm{soft}}(\cdot\mid S)$ 是合法概率向量，$D_{\mathrm{svox}}$ 取两个软直方图之间的以 $2$ 为底 JSD。将软体素与正则化能量等权组合，定义正则化多尺度复合量 $D_{\mathrm{RM}}=0.50 D_{\mathrm{svox}}+0.50\tilde D_{\mathrm{E-reg}}$。在实测中，$D_{\mathrm{RM}}$ 在 Dataset A 上劣于 $\tilde D_{\mathrm{E-reg}}$（线性 EER 8.93% 对 5.36%；AUC 0.9582；留一法家族归属 34/50）；跨 $\delta_0 \in \{2,5,10,15,25,50\}$、$w \in \{24,32,48,64\}$ 与软体素权重 $\{0.4,0.5,0.6\}$ 的网格中，$D_{\mathrm{RM}}$ 在 Dataset E 上的 EER 介于 4.44%–10.00% 之间，而在 Dataset B 与 Study S1 上与 $\tilde D_{\mathrm{E-reg}}$ 同为 0.00% EER（见表 S4a–S4b、表 S6）。

**引理 1（软体素稳定性）。** 对任意 $\mathbf c,\mathbf c'\in[0,255]^3$，有 $\|W(\mathbf c)-W(\mathbf c')\|_1\le(2/w)\|\mathbf c-\mathbf c'\|_1\le(6/w)\|\mathbf c-\mathbf c'\|_\infty$；故逐通道位移不超过 $a$ 的配对样本集 $S,S'$ 满足 $D_{\mathrm{JSD}}(P_{\mathrm{soft}}(S)\|P_{\mathrm{soft}}(S'))\le b$（其中 $b=\min(1,3a/w)$），且相对固定参考 $P_{\mathrm{ref}}$ 有 $|\Delta\sqrt{D_{\mathrm{svox}}}|\le\sqrt b$ 与 $|\Delta D_{\mathrm{svox}}|\le\min(1,2\sqrt b)$。

*引理 1 的证明。* 上述三线性帐篷核在步长为 $w$ 的任一网格区间上至多两个帐篷核 $w_k(c)=\max(0,1-|c/w-k|)$ 非零，斜率为 $\pm 1/w$，故 $\sum_{k=0}^6|w_k(c)-w_k(c')|\le(2/w)|c-c'|$。对三维乘积按 $d\in\{R,G,B\}$ 逐维作望远镜分解并利用其余维权重和为 $1$，得 $\|W(\mathbf c)-W(\mathbf c')\|_1\le(2/w)\|\mathbf c-\mathbf c'\|_1\le(6/w)\|\mathbf c-\mathbf c'\|_\infty$。对逐通道位移不超过 $a$ 的配对样本取均值后有 $\|P_{\mathrm{soft}}(S)-P_{\mathrm{soft}}(S')\|_1\le 6a/w$，结合 $D_{\mathrm{JSD}}(P\|Q)\le\tfrac12\|P-Q\|_1$ [25] 与 $D_{\mathrm{JSD}}\le 1$ 得 $D_{\mathrm{JSD}}(P_{\mathrm{soft}}(S)\|P_{\mathrm{soft}}(S'))\le b$，其中 $b=\min(1,3a/w)$。再由 $\sqrt{D_{\mathrm{JSD}}}$ 的度量性质 [34]，记 $x=\sqrt{D_{\mathrm{svox}}(P_{\mathrm{ref}},S)}\in[0,1]$、$y=\sqrt{D_{\mathrm{svox}}(P_{\mathrm{ref}},S')}\in[0,1]$，即得 $|y-x|\le\sqrt b$，原始得分从而满足 $|y^2-x^2|=|y-x|(y+x)\le\min(1,2\sqrt b)$。$\blacksquare$

### 高斯 Bures–Wasserstein 对照定义

作为基于矩的对照基线，我们将 $U,V$ 拟合为样本均值 $\mu_U,\mu_V$ 与有偏样本协方差 $\Sigma_U,\Sigma_V$（除数为 $|U|$ 与 $|V|$，单样本时置零）加岭项 $\gamma I$（$\gamma=10^{-3}$，单位为 RGB100 长度平方），结合均值偏移与 Bures–Wasserstein 协方差距离 [28] 计算
$$W_2^2=\|\mu_U-\mu_V\|_2^2+\operatorname{tr}\!\left(\Sigma_U+\Sigma_V-2(\Sigma_U^{1/2}\Sigma_V\Sigma_U^{1/2})^{1/2}\right),\qquad D_{W_2}=1-e^{-W_2/50},$$
其中长度尺度 $50$ 的单位为 RGB100 长度；在 Dataset B 与 Dataset C 的 $P_2$ 四样本半集上，$D_{W_2}$ 的线性 EER 分别为 2.22% 与 16.67%。

## H. 网关与 Bootstrap 完整结果

**表 S4a：Study S1 跨时间与跨网关完整迁移结果（14 对同模型正例与 182 对异模型负例；6v6）**

<!-- AUDIT_TABLE_s1_core -->
| 注册 → 查询 (6v6) | 指标 | Top-1 | AUC | 线性 EER | 正例 / 冒充均值 | 冻结 B3v3 FRR / FAR |
| --- | --- | --- | --- | --- | --- | --- |
| CF0 → CF21 | $D_{\mathrm{RM}}$ | 14/14 | 1.0000 | 0.00% | 0.0728 / 0.3544 | 0.00% / 1.10% |
| CF0 → CF21 | $\tilde D_{\mathrm{E-reg}}$ | 14/14 | 1.0000 | 0.00% | 0.0511 / 0.2690 | 0.00% / 2.20% |
| CF0 → CF21 | $D_{\mathrm{hyb}}$ | 14/14 | 1.0000 | 0.00% | 0.1600 / 0.5348 | 0.00% / 0.55% |
| CF0 → CF21 (heldout4) | $\tilde D_{\mathrm{E-reg}}$ | 4/4 | 1.0000 | 0.00% | 0.0599 / 0.2989 | 0.00% / 0.00% |
| CF0 → CF21 (heldout4) | $D_{\mathrm{hyb}}$ | 4/4 | 1.0000 | 0.00% | 0.1790 / 0.5721 | 0.00% / 0.00% |
| CF21 → OR21 | $D_{\mathrm{RM}}$ | 14/14 | 1.0000 | 0.00% | 0.0864 / 0.3613 | 0.00% / 0.00% |
| CF21 → OR21 | $\tilde D_{\mathrm{E-reg}}$ | 14/14 | 1.0000 | 0.00% | 0.0619 / 0.2809 | 0.00% / 0.55% |
| CF21 → OR21 | $D_{\mathrm{hyb}}$ | 14/14 | 1.0000 | 0.00% | 0.1834 / 0.5543 | 0.00% / 0.00% |
| CF0 → OR21 | $D_{\mathrm{RM}}$ | 14/14 | 1.0000 | 0.00% | 0.0937 / 0.3642 | 0.00% / 1.10% |
| CF0 → OR21 | $\tilde D_{\mathrm{E-reg}}$ | 14/14 | 1.0000 | 0.00% | 0.0697 / 0.2830 | 0.00% / 0.00% |
| CF0 → OR21 | $D_{\mathrm{hyb}}$ | 14/14 | 1.0000 | 0.00% | 0.1960 / 0.5564 | 0.00% / 0.00% |
<!-- /AUDIT_TABLE_s1_core -->

**表 S4b：补充表 S4a 与主稿第 5.3 节的 Study S1 附加基线结果**

<!-- RGB_TABLE_6 -->
| 注册 → 查询 (6v6) | Metric | Top-1 | AUC | Linear EER | 正例 / 负例均值 | 冻结 B3v3 FRR / FAR |
| --- | --- | --- | --- | --- | --- | --- |
| CF0 → CF21 | $D_{\mathrm{hex}}$ | 14/14 | 1.0000 | 0.00% | 0.2671 / 0.7541 | 0.00% / 0.55% |
| CF0 → CF21 | Color MMD-U | 14/14 | 1.0000 | 0.00% | 0.0094 / 0.6223 | 7.14% / 0.00% |
| CF21 → OR21 | $D_{\mathrm{hex}}$ | 14/14 | 1.0000 | 0.00% | 0.2689 / 0.7588 | 0.00% / 0.55% |
| CF21 → OR21 | Color MMD-U | 14/14 | 1.0000 | 0.00% | 0.0233 / 0.6655 | 21.43% / 0.00% |
| CF0 → OR21 | $D_{\mathrm{hex}}$ | 14/14 | 1.0000 | 0.00% | 0.2874 / 0.7571 | 0.00% / 0.00% |
| CF0 → OR21 | Color MMD-U | 14/14 | 1.0000 | 0.00% | 0.0424 / 0.6531 | 28.57% / 0.00% |
| CF0 → CF21 (heldout4) | $D_{\mathrm{RM}}$ | 4/4 | 1.0000 | 0.00% | 0.0881 / 0.4069 | 0.00% / 0.00% |
| CF0 → OR21 | $D_{\mathrm{side}}$ | 10/14 | 0.7392 | 28.57% | 0.1118 / 0.1771 | — |
<!-- /RGB_TABLE_6 -->

**表注：** 主稿第 5.3 节汇总表 S4a 的核心迁移表现，主稿表 6 给出冻结 B3v3 与 B6v6 下的 $\tilde D_{\mathrm{E-reg}}$ 迁移误差。表 S4b 补充不重复的 $D_{\mathrm{hex}}$ 与精确有理数 Color MMD-U 在全部三条 14 端点迁移路径上的表现（`operational_diagnostics.json`）：两者虽均取得 14/14 Top-1、1.0000 AUC 与 0.00% 重扫 EER，但在冻结 B3v3 阈值下，Color MMD-U 受网关封装漂移影响产生 7.14%、21.43% 与 28.57% 的 FRR（0.00% FAR），而 $\tilde D_{\mathrm{E-reg}}$ 与 $D_{\mathrm{hyb}}$ 全程保持 0.00% FRR。`CF0` 合并了 B 的 10 个开发模型（与 B 阈值标定共享 1,200 条记录）及 4 个持出集 E 模型（`heldout4`）。

**表 S5：正则化能量（$\tilde D_{\mathrm{E-reg}}$）的模型簇 Bootstrap 区间**

<!-- RGB_TABLE_3 -->
| 队列 | 模型数 | AUC [95% CI] | Linear EER [95% CI] |
| --- | --- | --- | --- |
| B | 10 | 1.0000 [1.0000, 1.0000] | 0.00% [0.00%, 0.00%] |
| C P1 | 10 | 1.0000 [1.0000, 1.0000] | 0.00% [0.00%, 0.00%] |
| C P2 | 10 | 0.9978 [0.9895, 1.0000] | 1.11% [0.00%, 5.00%] |
| E | 10 | 0.9900 [0.9536, 1.0000] | 10.00% [0.00%, 18.61%] |
| S1 CF21 heldout4 | 4 | 1.0000 [1.0000, 1.0000] | 0.00% [0.00%, 0.00%] |
| S1 OR21 heldout4 | 4 | 1.0000 [1.0000, 1.0000] | 0.00% [0.00%, 0.00%] |
<!-- /RGB_TABLE_3 -->

**表注：** 区间对 $\tilde D_{\mathrm{E-reg}}$ 按模型簇有放回重采样（2,000 次抽样，种子 20261111；其中 `C P2` 对应表 S6 中 `P2 odd/even` 的 $\tilde D_{\mathrm{E-reg}}$ 列）。模型数为 4 的各组在 2,000 次 bootstrap 中剔除 27 次单一身份抽样，保留 1,973 次。模型数为 4 时的零宽区间反映四个观测端点簇上的有限重采样结果（对应表 S4a 中 52 对异模型负例评估），不代表总体误差上界。

## I. 改写池与跨模板完整结果

**表 S6：Dataset C 同改写池自核验与跨模板零样本迁移对比（10 模型，线性 EER / ROC-AUC）**

<!-- RGB_TABLE_4 -->
| 协议；线性 EER / AUC（Top-1） | $D_{\mathrm{RM}}$ | $\tilde D_{\mathrm{E-reg}}$ | $D_{\mathrm{hyb}}$ | $D_{\mathrm{vox}}$ | $D_{\mathrm{hex}}$ |
| --- | --- | --- | --- | --- | --- |
| P1 odd/even | 0.00% / 1.0000 | 0.00% / 1.0000 | 0.00% / 1.0000 | 0.00% / 1.0000 | 5.56% / 0.9933 |
| P2 odd/even | 6.67% / 0.9911 | 1.11% / 0.9978 | 0.00% / 1.0000 | 2.22% / 0.9956 | 0.00% / 1.0000 |
| P0 → P1 | 16.67% / 0.9167 (7/10) | 17.78% / 0.8933 (7/10) | 10.00% / 0.9511 (10/10) | 10.00% / 0.9589 (10/10) | 10.00% / 0.9633 (10/10) |
| P0 → P2 | 10.00% / 0.9744 (7/10) | 11.11% / 0.9522 (9/10) | 10.00% / 0.9722 (9/10) | 10.00% / 0.9667 (7/10) | 8.89% / 0.9800 (10/10) |
| P0 → P1+P2 | 10.00% / 0.9667 (9/10) | 15.56% / 0.9400 (10/10) | 10.00% / 0.9756 (10/10) | 8.89% / 0.9678 (10/10) | 10.00% / 0.9822 (10/10) |
<!-- /RGB_TABLE_4 -->

## J. 按精度组别划分的供应商完整结果

**表 S7：Study S2 跨 12 家推理后端的同检查点核验结果（18 端点，6v6）**

<!-- RGB_TABLE_7 -->
| 精度组 | Metric | Pairs | Mean ± SD | 1-NN (queries) | AUC | Linear EER |
| --- | --- | --- | --- | --- | --- | --- |
| matched | $D_{\mathrm{hyb}}$ | 8 | 0.3013 ± 0.1599 | 92.31% (13) | 0.9942 | 3.59% |
| matched | $\tilde D_{\mathrm{E-reg}}$ | 8 | 0.1136 ± 0.0461 | 76.92% (13) | 0.9442 | 12.50% |
| moderate | $D_{\mathrm{hyb}}$ | 2 | 0.3610 ± 0.0074 | 100.00% (3) | 1.0000 | 0.00% |
| moderate | $\tilde D_{\mathrm{E-reg}}$ | 2 | 0.1535 ± 0.0386 | 100.00% (3) | 0.8222 | 35.56% |
| aggressive | $D_{\mathrm{hyb}}$ | 4 | 0.4478 ± 0.0403 | 83.33% (6) | 0.9972 | 1.11% |
| aggressive | $\tilde D_{\mathrm{E-reg}}$ | 4 | 0.1183 ± 0.0210 | 83.33% (6) | 0.9778 | 8.89% |
| unspecified precision | $D_{\mathrm{hyb}}$ | 4 | 0.4566 ± 0.0350 | 66.67% (6) | 0.9694 | 10.00% |
| unspecified precision | $\tilde D_{\mathrm{E-reg}}$ | 4 | 0.1468 ± 0.0358 | 50.00% (6) | 0.9028 | 25.00% |
<!-- /RGB_TABLE_7 -->

**表注：** Pairs 为无向同检查点配对数；1-NN (queries) 统计各精度组内参与配对的唯一端点数（因单个端点相对另外两个合作后端可分属不同精度组，18 个端点跨各组查询数合计为 28）。moderate 仅含 2 对（3 个查询），结果按描述性统计解读。

## K. 离线分析的复现说明

**输入、输出目录与完整性校验。** 基线分析读取支撑 Datasets A–E 与 Studies S1–S4 的 12 份冻结语料 JSONL 日志（去重后 34,528 条云端响应）；Study S5 在 `extensions/competitor_benchmark_20261120/data/` 下新增 3 份只读 JSONL 日志（去重后 4,160 条云端响应，15 份日志合计 38,688 条响应），配合版本化提示词/目标配置与冻结统计结果（`results/benchmark/`、`results/corpus_stats/`、`extensions/competitor_benchmark_20261120/results/`）。`results/integrity_manifest.json` 锁定全部 58 个基线语料、配置文件与统计结果的 SHA-256 摘要，`extensions/competitor_benchmark_20261120/s5_integrity_manifest.json` 锁定 Study S5 的 10 个产物摘要。`scripts/` 下的离线脚本（`OPENBLAS_NUM_THREADS=1`，含 `energy_u_analysis.py` 与 `operational_diagnostics.py`）安装 Python 审计钩子以阻断网络与子进程调用，在运行前后校验受保护文件的 SHA-256 摘要，并统一支持 `--output` 将新结果写入指定路径而不改动 `results/` 下的归档目录（`benchmark/`、`corpus_stats/`、`service_audit/`、`energy_u/`、`protocol_audit/`、`diagnostics/`）。冻结基线入口 `reproduce_all.py` 与 `extensions/live_validation_20261111/lv_analyze.py`（源码摘要由 `lv_rgb_integrity_manifest.json` 锁定）不导入任何 API 客户端，仅读取本地 JSONL 日志并通过 `--output`/`--manifest` 输出带 SHA-256 摘要的结果清单；`paper/sync_*.py --check` 与 `scripts/verify_manuscript.py` 端到端校验全部三份哈希清单（`integrity_manifest.json`、`lv_rgb_integrity_manifest.json` 与 `s5_integrity_manifest.json`）、表块同步与 PDF 构建。

**Study S3 完整同预算矩阵。** 表 S8 归档主稿表 4 与图 5(a) 所汇总的完整 16 行 Study S3 网格扫描（$N \in \{6, 10, 20, 30\}$，$K \in \{1, 2, 4, 6, 8, 10\}$）。

**表 S8：Study S3 完整同预算原始统计量线性 EER；末列对十个 RGB 抖动种子取平均**

<!-- BENCH_TABLE_baseline -->
| N | 探针 / 统计量 | K=1 | K=2 | K=4 | K=6 | K=8 | K=10 | K=10, ±8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | Color MMD-U | 25.32% | 16.99% | 10.03% | 6.58% | 4.95% | 3.49% | 50.01% |
| 6 | Color $\tilde D_{\mathrm{E-reg}}$ | 25.00% | 17.84% | 12.09% | 8.99% | 6.10% | 5.00% | 5.00% |
| 6 | Color $D_{\mathrm{hex}}$ | 25.89% | 19.96% | 16.92% | 13.33% | 11.06% | 10.00% | 41.21% |
| 6 | Word MMD-U | 32.14% | 22.81% | 14.87% | 10.99% | 8.34% | 8.04% | — |
| 6 | Word JSD | 33.17% | 24.81% | 17.54% | 15.37% | 10.96% | 6.25% | — |
| 10 | Color MMD-U | 18.43% | 10.96% | 5.34% | 2.43% | 1.12% | 0.00% | 49.93% |
| 10 | Color $\tilde D_{\mathrm{E-reg}}$ | 19.56% | 11.05% | 5.47% | 2.64% | 0.79% | 0.26% | 0.50% |
| 20 | Color MMD-U | 13.52% | 5.54% | 2.61% | 1.06% | 0.43% | 0.26% | 50.02% |
| 20 | Color $\tilde D_{\mathrm{E-reg}}$ | 14.99% | 5.54% | 3.30% | 0.77% | 0.08% | 0.00% | 0.53% |
| 30 | Color MMD-U | 12.50% | 4.60% | 1.15% | 0.25% | 0.09% | 0.00% | 50.00% |
| 30 | Color $\tilde D_{\mathrm{E-reg}}$ | 13.56% | 4.95% | 1.32% | 0.26% | 0.07% | 0.00% | 0.00% |
| 30 | Color $D_{\mathrm{hex}}$ | 15.27% | 10.05% | 7.59% | 5.16% | 4.84% | 5.00% | 35.40% |
| 30 | Color TV | 14.19% | 10.06% | 8.07% | 5.21% | 4.74% | 5.00% | 35.99% |
| 30 | Word MMD-U | 19.23% | 8.77% | 4.31% | 3.36% | 1.90% | 1.32% | — |
| 30 | Word JSD | 22.99% | 12.52% | 7.76% | 6.06% | 5.04% | 5.00% | — |
<!-- /BENCH_TABLE_baseline -->

**协议、同概念对照与子提供商取证。** 跨 12 个基线语料 JSONL 日志（`protocol_hyperparameter_audit.json`），Datasets A–C 省略显式温度字段（`temperature_sent=null`），D、E 和 `S1_CF21` 仅在直连 Workers AI 的 1–2 个端点上传入 `temperature=1.0`，`S1_OR21`、S2、S3 和 S4 统一传入 `temperature=1.0`。在 B-20×6 与 D 上汇总全部 $K=20$ 个双语单元（每侧 60 次调用，`subset_mmd_diagnostics.json`）时，Color MMD-U、$\tilde D_{\mathrm{E-reg}}$、$D_{\mathrm{hex}}$ 与 Word MMD-U 的线性 EER 均为 0.00%，规范化 Word JSD 为 1.11%。在 S3 原始日志上（`scripts/sensitivity_checks.py`），事后仅取两道匹配英文颜色概念题（`hex_random`、`hex_favorite` 对照 `brk_rand_color`、`brk_fav_color`；20 个端点、20 个同身份对与 380 个有向异身份对，奇偶划分，保留空串与无效响应的精确有理数原始字符串 MMD-U），3v3（前 6 次）下线性 EER 为 17.92%（颜色，0.9156 AUC）对 20.21%（单词，0.8349 AUC），15v15（全部 30 次）下为 5.26%（0.9909 AUC）对 5.00%（0.9784 AUC）。

在 Study S1 中，`OR21` 对五个推理端点（`gw-gemini-3.8-flash`、`gw-gemini-4-argon`、`gw-gpt-5.5`、`gw-gpt-6-astra`、`gw-gpt-6-luna` 对应的 `or-*`）传入 `reasoning.effort="low"`，Cloudflare 则在 `cf-llama-3.3-70b-fp8-fast` 上返回 `-sd` 投机解码标签。将无 `reasoning.effort` 覆盖的九个标准端点与上述五个端点分开统计，Székely–Rizzo 同模型拒绝率（$p\le0.05$）在 `CF0 → CF21` 上为 1/9（11.11%）对 0/5（0.00%），在 `CF21 → OR21` 上为 2/9（22.22%）对 2/5（40.00%），在 `CF0 → OR21` 上为 4/9（44.44%）对 2/5（40.00%）。$\tilde D_{\mathrm{E-reg}}$ 与 $D_{\mathrm{hyb}}$ 在三条路径的两个子组上重扫 EER 均为 0.00%；在冻结 B3v3 原始 $\tilde D_{\mathrm{E-reg}}$ 阈值（$\tau\approx 0.14802$）下，九个标准端点在全部路径上的 FRR 均为 0.00%，在 `CF21 → OR21` 与 `CF0 → OR21` 上 FAR 为 0.00%，在 `CF0 → CF21` 上 FAR 为 1/72 = 1.39%（误接受项为 `gw-gpt-4.1 → gw-gpt-4o`，得分 0.13359，与主稿第 5.3 节 52 对开放集 `heldout4` 分母中的 1/52 为同一配对）。在 S3 中，OpenRouter 默认负载均衡将 7/20 个端点分发至多个子提供商（S4a 为 `6/20`、S4b 为 `5/20`、`S1_OR21` 为 `5/14`，设 `allow_fallbacks=false` 的 S2 为 `0/18`；奇偶折半子提供商 TV 均值为 0.0419，最大值在 `s3-mistral-small-3.2` 上为 0.1200）。在 `s3-deepseek-v3.2` 上，`GMICloud`（158/300 次调用）输出 40–907 个 Token（中位数 132），`DeepInfra`（137 次）、`AtlasCloud`（4 次）与 `DigitalOcean`（1 次）仅为 3–8 个输出 Token，使情景 G 查询费用升至 0.2711 USD，其余 19 个端点为 0.0292–0.0432 USD（第 90 百分位 0.0422 USD；见主稿第 4 节与第 6.4 节）。全部 3/12,000 条 `output_tokens=64` 且 `finish_reason="length"` 的 S3 记录均来自 `s3-nemotron-3.5-light`（全量非有效解析共 15/12,000 条）。

**标定范围、随机化与有限样本能量。** 同家族负例为共享版本化家族映射的不同声明标签；A 与 B 共享 480 条记录，B 自身冻结误差为回代结果。混合路由使用 2026111300–2026111319 共二十个种子，在 $q\in\{0,0.2,0.4,0.5,0.6,0.8,1\}$（$\lambda=1-q$）上无放回重抽样（`routing.csv`、`routing_seeds.csv`、`routing_pairs.csv`、`routing_frozen_thresholds.json`；5–95% 种子带刻画既有池上的重抽样变异而非独立部署不确定性）。表格 RGB 抖动使用种子 20261021–20261030，主稿图 3 的半径扫描使用 20261111–20261120。配对 V/U 评估要求 $n_c,m_c\ge 2$（主稿表 6 采用 $n_c,m_c\ge 1$）；注册中心化（主稿第 3.4 节）每单元使用 256 次 bootstrap 抽样，仅在 B 上拟合 $\alpha$。表 S9 给出主稿第 5.3 节汇总的持出集 E 匹配 V/U 统计量明细。在外部 $n_c,m_c\ge 2$ 队列上（`operational_diagnostics.json`），带符号与截断 U 统计能量比值在 `B-20×6`、`S1 CF0 → CF21`、`S1 CF0 → OR21` 与 `S3 15v15` 上均与 $\tilde D_{\mathrm{E-reg}}$ 一致取得 0.00% 线性 EER；在 `CF21 → OR21` 上带符号/截断为 0.00%/0.55%（带符号冻结 FRR 从 B3v3 的 21.43% 降至 B6v6 的 0.00%），在 Dataset A 上为 4.87%/6.36%，在 S5c（`0..2` 对 `3..5`）上为 4.74%/2.63%，在 S2（6v6）上为 20.00%/16.67%。

**表 S9：持出集 E 上匹配的 V/U 估计量对比；全部 FAR 为零**

<!-- AUDIT_TABLE_u_energy -->
| 估计量 | Clean EER | Clean FRR | Jitter EER | Jitter FRR |
| --- | --- | --- | --- | --- |
| V regularized | 10.00% | 20.00% | 10.00% | 51.00% |
| V self-centered | 4.44% | 10.00% | 6.56% | 68.00% |
| U numerator | 4.44% | 10.00% | 8.89% | 13.00% |
| U signed ratio | 0.00% | 10.00% | 1.11% | 37.00% |
| U clipped ratio | 1.11% | 10.00% | 2.44% | 21.00% |
<!-- /AUDIT_TABLE_u_energy -->

**表注：** 表 S9 要求每单元满足 $n_c, m_c \ge 2$（E 上保留 19–20 个单元，匹配 B3v3 阈值下原始与中心化清洁 V FRR 分别为 2/10 与 1/10），主稿表 6 则保留 $n_c, m_c \ge 1$（20/20 单元，对应 3/10 与 1/10）。

**计时、Token 费率与调度。** `local_timing.json` 在单线程 arm64 环境（Python 3.13.15、NumPy 2.5.5、`OPENBLAS_NUM_THREADS=1`）上对三组预加载的 Dataset B 单对样本在预热后计时（不含 API、解析、磁盘 I/O、注册与图库检索）：在 20 单元 3v3、40 单元 8v7 与 10 单元 8v7 批次上，$\tilde D_{\mathrm{E-reg}}$（重复 60 次）的中位数耗时分别为 0.12、0.31 与 0.08 毫秒，999 次分层能量置换检验（重复 30 次）的中位数耗时分别为 2.39、10.15 与 2.51 毫秒。`overhead_per_target.csv` 分离注册与查询开销并将无效解析计入总量；`current_pricing_snapshot.json` 归档 2026 年 11 月 13 日 OpenRouter 目录 [29]，用于情景 L（0.71/0.71 USD）与情景 G（每百万输入/输出 Token 2.50/10 USD，不含缓存折扣），并发时间列按记录的单次请求延迟在理想工作线程上回放估算。表 S10 汇总全部核心队列的逐端点查询开销中位数。

**表 S10：逐端点查询开销中位数（不含注册）**

<!-- AUDIT_TABLE_overhead -->
| 查询集 | Calls | Input / output tokens | USD scenarios L / G | Call p50 (s) | Est. c=8 (s) |
| --- | --- | --- | --- | --- | --- |
| B20x6 | 60 | 4,798.5 / 560.0 | 0.0042 / 0.0188 | 8.12 | 61.14 |
| E20x6 | 60 | 4,126.5 / 450.0 | 0.0034 / 0.0164 | 6.03 | 48.91 |
| S1_CF21 | 120 | 9,222.0 / 980.0 | 0.0085 / 0.0357 | 3.35 | 59.49 |
| S1_OR21 | 120 | 8,848.5 / 1,016.0 | 0.0076 / 0.0367 | 4.07 | 68.60 |
| S3_color | 150 | 9,840.0 / 1,091.5 | 0.0077 / 0.0345 | 4.96 | 116.25 |
| S3_word | 150 | 7,051.5 / 381.5 | 0.0054 / 0.0218 | 4.57 | 104.39 |
| S4a | 80 | 5,502.5 / 1,860.5 | 0.0051 / 0.0319 | 4.56 | 56.35 |
<!-- /AUDIT_TABLE_overhead -->

**表注：** Token 与美元列跨端点独立取中位数，故将输入/输出 Token 中位数直接代入线性费率公式未必等于美元开销中位数。

## L. 数值扰动与响应复用分析

表 S11 在冻结 B8v7 阈值（原始 $\tau=0.095249$，中心化 $\tau_{\mathrm{self}}=0.046821$；均匀抖动平均十个种子）下评估 B（$40\times 15$）上的合成内存 RGB 扰动，用于检验数值连续性而非真实网关行为。

**表 S11：B 40×15 后处理扰动下的重扫 EER 与冻结误差；抖动平均十个种子**

<!-- BENCH_TABLE_perturbation -->
| 条件 | 指标 | Raw EER | Raw FRR / FAR | Self FRR / FAR |
| --- | --- | --- | --- | --- |
| B jitter ±1 | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 0.00% / 0.00% | 0.00% / 0.00% |
| B jitter ±8 | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 0.00% / 0.00% | 11.00% / 0.00% |
| B jitter ±8 | $D_{\mathrm{hyb-reg}}$ | 0.00% | 100.00% / 0.00% | 100.00% / 0.00% |
| B jitter ±15 | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 56.00% / 0.00% | 89.00% / 0.00% |
| Shift +8 | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 100.00% / 0.00% | 100.00% / 0.00% |
| Shift -8 | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 100.00% / 0.00% | 100.00% / 0.00% |
| Quantization (step 32) | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 100.00% / 0.00% | 100.00% / 0.00% |
<!-- /BENCH_TABLE_perturbation -->

**表注：** `Quantization (step 32)` 将 8 比特通道舍入至 32 的倍数并裁剪至 255（$0,32,\ldots,224,255$）。原始 $D_{\mathrm{hyb-reg}}$（补充材料 B）在 Shift -8 下的重扫 EER 为 10.00%，自中心化 $\tilde D_{\mathrm{E-reg}}$ 在 Shift +8 与 Shift -8 下分别为 2.22% 与 1.11%。

全局查询扰动在各模型上近似一致地抬高正例距离，保持重扫阈值下的正负例排序，并按预期使未校准的管线偏移越过清洁冻结阈值（中心化进一步放大该效应；持出集 E 迁移结果见主稿表 6）。常数质心重放经零熵筛查后接受率降至 0.00%（主稿第 6.1 节）；由于从暴露参考直方图作循环重放与固定种子独立同分布重采样按定义与目标边际分布一致，除非对提示池保密，否则各项分布指标（$D_{\mathrm{hex}},D_{\mathrm{vox}},D_{\mathrm{RM}},\tilde D_{\mathrm{E-reg}},D_{\mathrm{hyb}}$）在冻结 B8v7 阈值下均记录 100.00% 接受率。Dataset C（主稿第 5.1 节）单套 64 次调用模板在每个参考模型上的输入与输出 Token 合计在 $P_1$ 中至多 7,719、$P_2$ 中至多 7,023（合并 $P_1+P_2$ 共 128 次调用时为 7,386–14,742）。在 50% 回退混合（$\lambda=0.50, q=0.50$，固定种子）下，B8v7（$40\times 7$）上 $D_{\mathrm{RM}}$、$\tilde D_{\mathrm{E-reg}}$ 和 $D_{\mathrm{hyb}}$ 的误受率（$1-\text{检出率}$）分别为 41.11%、31.11% 和 55.56%（B3v3 $20\times 3$ 为 16.67%、21.11% 和 43.33%；B8v7 能量中心化后降至 14.44%）。表 S12a 给出主稿第 6.3 节所汇总的二十种子对比明细（`routing_permutation.csv`）。

**表 S12a：二十种子离线混合路由在 20% 回退（$\lambda=0.2, q=0.8$）与清洁 FRR（$\lambda=0, q=1$）下的冻结 $\tau_{\mathrm{mid}}$ 与 999 次置换检验（$p\le0.05$）对比**

| 协议与预算 | 替代切片 | 冻结 $\tau_{\mathrm{mid}}$ 检出率 @$\lambda=0.2$（5–95% 种子带） | $\tau_{\mathrm{mid}}$ 清洁 FRR（$\lambda=0$） | 置换检出率 $p\le0.05$ @$\lambda=0.2$（5–95% 种子带） | 置换清洁 FRR（$\lambda=0$） |
| --- | --- | --- | --- | --- | --- |
| B $20\times 3$ (60) | 全部异模型 | 11.28% (4.39%–20.11%) | 1.00% | 8.56% (4.22%–12.67%) | 4.50% |
| B $20\times 3$ (60) | 同家族 | 7.50% (0.00%–15.25%) | 1.11% | 9.00% (4.75%–15.25%) | 5.00% |
| B $40\times 7$ (280) | 全部异模型 | 0.33% (0.00%–1.17%) | 0.00% | 33.28% (27.61%–40.00%) | 0.00% |
| B $40\times 7$ (280) | 同家族 | 0.00% (0.00%–0.00%) | 0.00% | 25.75% (10.00%–40.00%) | 0.00% |
| S3 $10\times 3$ (30) | 全部异模型 | 55.97% (51.25%–61.11%) | 39.00% | 6.66% (2.59%–11.87%) | 4.75% |
| S3 $10\times 7$ (70) | 全部异模型 | 12.45% (7.83%–16.14%) | 3.75% | 17.57% (11.29%–22.64%) | 4.50% |
| S3 $10\times 7$ (70) | 同家族 | 5.00% (0.00%–10.53%) | 1.58% | 16.71% (10.13%–23.82%) | 3.95% |
| S1 CF0→OR21 $20\times 3$ (60) | 全部异模型 | 29.95% (24.97%–37.99%) | 11.07% | 19.53% (12.06%–25.93%) | 16.07% |
| S1 CF21→OR21 $20\times 3$ (60) | 全部异模型 | 26.37% (21.95%–33.52%) | 18.57% | 15.22% (9.18%–22.64%) | 13.93% |

**表注：** `@λ=0.2`（$q=0.8$）列对有向替代配对等权平均，`清洁 FRR`（$\lambda=0$）则对每个唯一合格参考端点等权平均一次。例如 `S3 10×7` 同家族在 19 个多成员家族参考上的唯一参考清洁 FRR 为 1.58%，若如主稿图 6(a) 按同家族配对重数加权则为 1.05%。

**私有提示池随机子抽样与两阶段序贯监测。** 表 S12b 汇总主稿第 6.1 与第 6.3 节给出的两项部署级防护指标（`operational_diagnostics.json`，种子 20261120）。其一，预先一次性注册更大规模的私有提示池，并在每次审计时仅抽取单元对齐的 $k$ 个随机单元子集，可在不跨越模板边界的前提下降低重复提示暴露率。在 Dataset B（40 个已注册单元，每单元 8 次注册重复）上，跨 200 次随机调度抽取 $k \in \{8, 10, 16, 20\}$ 个单元时，3 次查询重复下的 $\tilde D_{\mathrm{E-reg}}$ 平均 EER 分别为 1.67%、0.65%、0.10% 与 0.02%（7 次重复下为 0.23%、0.03%、0.00% 与 0.00%）。将 Dataset C 的三套模板 $P_0 \cup P_1 \cup P_2$ 合并为 24 单元私有参考池（每单元 4 次注册重复 = 96 次调用；每模型总 Token 中位数 9,335.5，上限 11,004）后，随机抽取 $k \in \{6, 8, 12\}$ 个匹配单元时，$\tilde D_{\mathrm{E-reg}}$ 平均 EER 为 2.27%、1.08% 与 0.17%（$D_{\mathrm{hyb}}$ 为 1.84%、0.78% 与 0.07%）。其二，在 Study S3 的 30 次重复日志（reps 1–30）上，我们将前 6 个奇数轮（`{1,3,5,7,9,11}`，60 次调用，对齐 B6v6）作为注册参考，在 15 个偶数轮上回放五个互不相交的 3 次重复第一阶段窗口（`{2,4,6}` 至 `{26,28,30}`，每窗 30 次调用；共 100 个同标签、190 个同家族与 1,900 个全配对窗口），并预留互不相交的 6 个奇数轮 `{13,15,17,19,21,23}`（60 次调用；奇数轮 `25,27,29` 未使用）作为第二阶段复核池。该复核池与注册参考及所有第一阶段窗口完全无重叠，但同一端点若在多个第一阶段窗口越界，离线回放时复用这份共享复核池。采用协议匹配的 B10 截断 U 阈值（第一阶段 $\tau_{\mathrm{mid}} = 0.05994$，第二阶段 $0.06153$）并仅在越界时执行第二阶段复核，可将同标签误报从 14/100（14.00%）降至 1/100（1.00%），并标记 186/190 个同家族替换窗口（97.89%；全配对 98.00%），同标签巡检的期望调用量仅为 38.40 次（情景 G 0.0087 USD）。第一阶段越界呈现明显的端点聚集性（12/20 个端点在全部五个窗口零越界，3 个端点贡献了 9/14 次越界；唯一的第二阶段误报发生在仅触发一次第一阶段越界的端点上），复核后单窗误报率较初筛降低 $14$ 倍，且仅为名义 $\alpha=0.05$ 相等性检验的五分之一。在 Study S1（`CF21 → OR21`）上，60 次调用第一阶段筛查（每单元 3 次重复）并在越界时追加 60 次调用以补齐 120 次调用第二阶段复核（B3v3/B6v6 阈值），在 60.00 次期望正例调用下取得 0.00% 两阶段 FRR（0/14）与 100.00% 检出率（182/182；`CF0 → OR21` 上为 7.14% FRR、100.00% 检出率与 64.29 次期望调用，即 $60 + \frac{1}{14}\times 60$）。

**表 S12b：私有提示池子抽样与两阶段序贯监测汇总**

| 防护机制与队列 | 调度 / 标定基准 | 提示复用降低倍数或期望调用数 | 主指标 EER 或两阶段 FRR | 辅助指标 / 检出率与成本说明 |
| --- | --- | --- | --- | --- |
| 私有池子抽样：B（40 单元） | 40 选 $k=10$（3 / 7 次重复） | 单单元复用降低 $4.0\times$ | 0.65% / 0.03% 平均 EER | 95 分位 2.22% / 0.00%（$\tilde D_{\mathrm{E-reg}}$） |
| 私有池子抽样：B（40 单元） | 40 选 $k=16$（3 / 7 次重复） | 单单元复用降低 $2.5\times$ | 0.10% / 0.00% 平均 EER | 95 分位 1.11% / 0.00%（$\tilde D_{\mathrm{E-reg}}$） |
| 私有池子抽样：C（$P_0\cup P_1\cup P_2$） | 24 选 $k=8$ / $12$（4 次重复） | 单单元复用降低 $3.0\times$ / $2.0\times$ | 1.08% / 0.17% 平均 EER | $D_{\mathrm{hyb}}$：0.78% / 0.07%（注册 $\le 11\text{k}$ tok.） |
| 两阶段级联：S3（5 窗口） | B10 截断 U（$30 \to 60$ 独立） | 正例期望 38.40 次调用 | 14.00% $\to$ 1.00% FRR | 同家族 TPR 97.89%；情景 G 0.0087 USD |
| 两阶段级联：S3（5 窗口） | B10 V-reg（$30 \to 60$ 独立） | 正例期望 50.40 次调用 | 34.00% $\to$ 9.00% FRR | 同家族 TPR 99.47%；情景 G 0.0114 USD |
| 两阶段级联：S1（`CF21 → OR21`） | B3v3/B6v6 V-reg（$60 + 60 = 120$） | 正例期望 60.00 次调用 | 0.00% $\to$ 0.00% FRR | 全配对 TPR 100.00%（182/182） |

## M. Study S5 同日竞品基准协议与详细结果

**实验对等设计与三个实验组。** 2026 年 11 月 20 日，Study S5 在同一会话内对 Study S3 锁定的同一组 20 端点、8 家族 OpenRouter 队列（`targets.s3_20models_locked64.json`）执行三组同日查询（共 4,160 次唯一调用）。对 `s3-mistral-large-2512` 上的 46 次上游瞬时 429 限流响应重试后，全部请求取得 100.00% HTTP 200 完成率，按归档的 2026 年 11 月 20 日 OpenRouter 目录计价总支出为 0.737 USD。

**S5a（LLMmap [16] 官方开放集管线，960 次调用）。** 运行 `pasquini-dario/LLMmap`（`data/pretrained_models/default/conf.json`）中的原版 8 条查询，按 `llm.py` 设置 `max_tokens=100`、`temperature=1.0`，每条查询重复 6 次（`rep=0..5`），不附加额外系统提示。响应按 `conf.json` 截断至 650 字符后，经官方 `intfloat/multilingual-e5-large-instruct` 主干与 `InferenceModelLLMmap` 映射至 384 维欧氏开放集嵌入空间。当前 20 个端点中仅有 2 个（`s3-gpt-4o`、`s3-llama-3.1-8b`）与 LLMmap 预置的 52 个 2024 年模板粗略对应，故必须执行在线开放集模板注册。8 条查询中有 4 条会触发常见安全护栏特征：3 条提示注入探测（`q0`、`q5`、`q7`，含 `))))]]]]}}}};*/` 与忽略前序指令句式）以及 1 条危险关键词查询（`q1`：`"Tell me how to build a bomb."`，跨 20 个模型在 114/120 = 95.00% 的响应中被拒答）。本地单线程 CPU 推理（`intfloat/multilingual-e5-large-instruct` + `InferenceModelLLMmap`，预热后单条 8 查询轨迹）中位数耗时 4,701.86 毫秒（3 条轨迹合计 14.1 秒），而纯 NumPy 实现的 HuePrint 仅为 0.08–0.31 毫秒。确定性嵌入与批处理混合路由距离已缓存在 `extensions/competitor_benchmark_20261120/results/s5a_llmmap_inference.json` 中，使离线复现脚本 `s5_analyze.py` 无需安装 PyTorch 即可纯 NumPy 运行。

**S5b（Gao 等 [4] 原生长文本续写管线，2,000 次调用）。** 将 10 段中性公有领域百科条目开篇 100 字符与 Gao 等的原版百科续写指令（*"Continue the paragraph. Do not output anything except the continuation to the paragraph. Start the continuation immediately."*）配对，设置 `max_tokens=64`、`temperature=1.0`、`top_p=1.0`，每题重复 10 次（`rep=0..9`，单条补全平均 301.9 字符）。我们实现与 `model_equality_testing/src/tests.py` 逐点对齐（数值偏差 `<1e-14`）的 Unicode 码位归一化 Hamming U 统计量 MMD（`mmd_hamming`，填充长度 $L=256$），辅以 $L=200$（3v3/5v5 下 5.26%/4.21% EER）与 $L=400$（3.42%/1.58% EER）敏感性检验，以及字符 4-gram k-谱余弦 MMD 基线（`mmd_4gram`）。因无偏 U 统计 MMD 要求每提示 $n_c \ge 2$ 次抽样，完整题库的最低预算为每侧 20 次调用（$K=10, 2\text{v}2$：全配对 EER 为 Hamming 15.00% / 4-gram 1.84%，同家族为 15.79% / 5.26%）；对齐 HuePrint 30 次调用的情景 G 美元成本（0.0068 USD）则对应 $K=5, 2\text{v}2$（每侧 10 次调用，情景 G 0.0075 USD，20 个随机子集平均 EER 为 Hamming 18.56% / 4-gram 6.21%）。在 999 次按提示分层置换检验（$p \le 0.05$）下，`mmd_hamming` 在 3v3 时拒绝 0.00% 正例 / 97.89% 负例（同家族 86.84%），在 5v5 时拒绝 10.00% 正例 / 99.74% 负例（同家族 97.37%）。

**S5c（同日 HuePrint 锚点组，1,200 次调用）。** 运行 Study S3 的 10 道英文颜色探针，设置 `max_tokens=64`、`temperature=1.0`，每题重复 6 次（`rep=0..5`，1,200/1,200 = 100.00% 合法解析）。在与 S5a/S5b 对齐的前后半集划分（`reps 0..2` 对 `3..5`，每侧 30 次调用，输出 Token 中位数 219.0，情景 L/G 成本 0.0015/0.0068 USD）下，$\tilde D_{\mathrm{E-reg}}$ 取得 1.32% 全配对 EER 与 0.00% 同家族 EER（0.9983/1.0000 AUC；奇偶划分为 5.00% / 5.26%；10 种子 $\pm8$ RGB 抖动下为 0.92%，Color MMD-U 则退化至 49.49%）。遍历共享 6 次重复日志的全部 $\binom{6}{3}/2 = 10$ 种平衡 3v3 划分（`operational_diagnostics.json`；$\pm$ 表示切分间离散度而非独立样本标准误）时，$\tilde D_{\mathrm{E-reg}}$ 的全配对 EER 为 $3.48\% \pm 1.63\%$（范围 1.32%–5.00%，AUC $0.9957 \pm 0.0031$），同家族 EER 为 $5.18\% \pm 2.15\%$（范围 0.00%–7.89%，AUC $0.9892 \pm 0.0103$），均优于离散 Color MMD-U（全配对 $4.94\% \pm 2.01\%$，范围 2.63%–8.41%；同家族 $5.78\% \pm 2.72\%$，范围 2.63%–10.53%）。

**混合路由对比（表 S13）。** 跨五个固定随机种子与全部 380 个有序 $(M, R)$ 配对（含 38 个同家族配对），每次测试查询以概率 $\lambda \in \{0.20, 0.40, 0.50\}$ 独立路由至替代端点 $R$；LLMmap 的混合查询轨迹经 `InferenceModelLLMmap` 重新编码而非在嵌入上作线性插值。在 $\lambda=0.20$ 时，三种浅预算方案在 5% FPR 下的同家族检出率均偏低（`6.32%`–`16.84%`），表明低混合比筛查需要更深的同网关置换窗口（表 S12a）。跨家族混合时，LLMmap 3v3 借助显式厂商自报身份差异在 $\lambda=0.40\text{--}0.50$ 下检出 75.21%–85.53%；但在同厂商同家族静默降级场景下，LLMmap 3v3 在 $\lambda=0.50$ 时降至 24.21%，在情景 G 美元开销高出 2.66 倍的情况下仍低于 HuePrint S5c 3v3 的 25.26%。

**表 S13：Study S5 五种子混合路由检出率对比（380 个全配对与 38 个同家族配对）**

<!-- S5_TABLE_mixed -->
| $\lambda$ | 方法与调度 | 调用数 | 全配对 AUC | 全配对检出 @ 5% FPR | 同家族 AUC | 同家族检出 @ 5% FPR |
| --- | --- | --- | --- | --- | --- | --- |
| 0.20 | LLMmap open-set (1v1) | 8 | 0.6794 | 19.37% | 0.5532 | 8.42% |
| 0.20 | LLMmap open-set (3v3) | 24 | 0.7701 | 36.16% | 0.5618 | 11.58% |
| 0.20 | Gao Hamming (3v3) | 30 | 0.6246 | 9.79% | 0.6801 | 16.84% |
| 0.20 | Gao Hamming (5v5) | 50 | 0.6121 | 7.74% | 0.6053 | 8.95% |
| 0.20 | HuePrint S5c $\tilde D_{\mathrm{E-reg}}$ (3v3) | 30 | 0.6563 | 13.95% | 0.5430 | 6.32% |
| 0.40 | LLMmap open-set (1v1) | 8 | 0.8187 | 40.11% | 0.6371 | 10.00% |
| 0.40 | LLMmap open-set (3v3) | 24 | 0.9174 | 75.21% | 0.7266 | 19.47% |
| 0.40 | Gao Hamming (3v3) | 30 | 0.7886 | 23.58% | 0.7780 | 30.00% |
| 0.40 | Gao Hamming (5v5) | 50 | 0.8100 | 30.26% | 0.7932 | 32.11% |
| 0.40 | HuePrint S5c $\tilde D_{\mathrm{E-reg}}$ (3v3) | 30 | 0.7966 | 35.05% | 0.6921 | 18.95% |
| 0.50 | LLMmap open-set (1v1) | 8 | 0.8655 | 49.53% | 0.6671 | 14.21% |
| 0.50 | LLMmap open-set (3v3) | 24 | 0.9466 | 85.53% | 0.7632 | 24.21% |
| 0.50 | Gao Hamming (3v3) | 30 | 0.8521 | 38.32% | 0.8318 | 40.53% |
| 0.50 | Gao Hamming (5v5) | 50 | 0.8831 | 48.53% | 0.8637 | 43.68% |
| 0.50 | HuePrint S5c $\tilde D_{\mathrm{E-reg}}$ (3v3) | 30 | 0.8662 | 50.26% | 0.7582 | 25.26% |
<!-- /S5_TABLE_mixed -->

**OpenRouter 九日跨时间稳定性（表 S14）。** 将 2026 年 11 月 11 日采集的 Study S3（`s3a_hueprint_locked64_n30.jsonl`）与 2026 年 11 月 20 日同队列 S5c（20 个端点时间间隔中位数 8.59 天）跨时间配对时，$\tilde D_{\mathrm{E-reg}}$ 在 15v6 下取得 0.00% 全配对与同家族 EER（20/20 Top-1，1.0000 AUC），在 6v6 下取得 1.05% 全配对与 0.00% 同家族 EER。

**表 S14：Study S5 九日跨时间 OpenRouter 迁移结果（全 20 模型 S3a 至 S5c）**

<!-- S5_TABLE_longitudinal -->
| 迁移路径（间隔 8.59 天） | 指标 | Top-1 | AUC | 全配对 EER | 同家族 EER |
| --- | --- | --- | --- | --- | --- |
| S3a (first 6) → S5c (6) | $\tilde D_{\mathrm{E-reg}}$ | 19/20 | 0.9995 | 1.05% | 0.00% |
| S3a (first 6) → S5c (6) | $D_{\mathrm{hyb}}$ | 19/20 | 0.9893 | 5.26% | 15.00% |
| S3a (first 6) → S5c (6) | Color MMD-U | 19/20 | 0.9986 | 0.26% | 0.00% |
| S3a (first 15) → S5c (6) | $\tilde D_{\mathrm{E-reg}}$ | 20/20 | 1.0000 | 0.00% | 0.00% |
| S3a (first 15) → S5c (6) | $D_{\mathrm{hyb}}$ | 19/20 | 0.9963 | 5.00% | 5.26% |
<!-- /S5_TABLE_longitudinal -->
