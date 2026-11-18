# 《空谈无益，亮出颜色：面向聚合式大语言模型服务的低预算一致性审计》补充材料

本补充材料基于与主稿相同的 12 份冻结语料日志，给出色彩坐标敏感性分析、固定权重正则化消融、完整端点标签、多语种探针原文、稳定性证明与扩展验证表。文献 [24]–[29] 沿用主稿编号，[30]–[34] 为补充材料专用文献。

## A. 色彩坐标变换与敏感性对照

**单射与 Lipschitz 色彩坐标变换。** 对有限 $256^3$ sRGB 网格上不作坐标舍入或分箱合并的任一单射映射 $\Phi:\Omega_{\mathrm{RGB}}\to\Omega_*\subset\mathbb R^3$，类别单射重命名保持精确色号 JSD（$D_{\mathrm{JSD}}(\Phi_\#P\|\Phi_\#Q)=D_{\mathrm{JSD}}(P\|Q)$）与命题 1 的支撑逃逸事件不变，且有界 $\Omega_*$ 上的欧氏距离强负型性质 [26], [30] 保证 $\tilde D_{\mathrm{E},\delta_*}(\Phi_\#P,\Phi_\#Q)=0\iff P=Q$（$\delta_*>0$）。若 $\|\Phi(x)-\Phi(x')\|_2\le L_{\max}\|x-x'\|_2$（$L_{\max}<\infty$），RGB100 中至多 $\epsilon$ 的位移在 $\Omega_*$ 中至多为 $L_{\max}\epsilon$，代入命题 2 即得 $D_*(U,V)=\tilde D_{\mathrm{E},\delta_*}(\Phi(U),\Phi(V))$ 的单侧界 $2L_{\max}\epsilon/\delta_*$ 与双侧界 $4L_{\max}\epsilon/\delta_*$（对截断比值再以 $1$ 封顶）。

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

其中 $D_{\mathrm{hyb-reg}}$ 将 $D_{\mathrm{hyb}}$ 中的未正则化能量项 $\bar D_{\mathrm E}$ 替换为 $\tilde D_{\mathrm{E-reg}}$，并保持四项混合权重 $(0.35, 0.25, 0.25, 0.15)$ 不变（主稿第 3.4 节式 (4)）。

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

D 为单词响应，颜色能量与颜色混合量在其上无定义。在多成员家族端点（A 中 50/56、E 中 9/10，剔除单成员家族模型）上的留一法家族归属表现亦不同于二元核验：将能量正则化（$\bar D_{\mathrm E}\to\tilde D_{\mathrm{E-reg}}$）使准确率在 A 上从 31/50 提升至 35/50（两种混合量均为 36/50），在 E 上从 2/9 提升至 6/9（两种混合量均为 7/9）。

**语法与推理计费信封去混杂消融。** 在 $D_{\mathrm{side}}$ 中，当有效 `#RRGGBB` 色号仅由数字 `0`–`9` 构成时（占 RGB 立方体的 $10^6/16^6 \approx 5.96\%$），十六进制大小写标签记为 `numeric_only`；推理长度分箱则在 API 计费信封返回 `usage.reasoning_tokens` 时优先读取该字段，否则回退到可见推理字符数（`perturbation_diagnostics.json`）。第一，仅移除 API 推理元数据（剥离 `explicit_reasoning` 与 `usage.reasoning_tokens`，即 `content_only_no_envelope`）使跨网关 S1（`CF0 → OR21`，其中 OpenRouter 返回 `reasoning_tokens` 而 Cloudflare 省略该字段）的同模型正例均值 $D_{\mathrm{side}}$ 从 0.1118 降至 0.0161，并使 S4a（5v5）上的 $D_{\mathrm{hyb}}$ EER 从原始 1.58% 升至 2.89%，而 $\tilde D_{\mathrm{E-reg}}$ 保持 0.00%（对应主稿第 6.2 节）。第二，在此基础上再把 `numeric_only` 合并到 `upper`（`pure_content_syntax`）时，S4a 上的 $D_{\mathrm{hyb}}$ EER 为 2.63%（$\tilde D_{\mathrm{E-reg}}$ 仍为 0.00%），S1（`CF0 → OR21`）同模型正例均值 $D_{\mathrm{side}}$ 进一步降至 0.0064，且 $D_{\mathrm{side}}$ 的 AUC/线性 EER 在 Dataset A 上从 0.7804/30.32% 降至 0.6557/36.76%，在 Dataset B（$40\times 15$）上从 0.9722/10.00% 降至 0.6933/36.00%。

<!-- SUPPLEMENT_INVENTORY -->

## C. 完整端点清单与标签来源

本表完整列出数据集 A 的 56 个端点，每端点 48 条响应。标识符、声明模型名和返回模型名逐字取自冻结响应日志；家族与厂商标签取自版本化标签映射。这些是实验标签，不是独立认证的权重身份或产品目录。

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

## G. 稳定性证明与高斯对照

*命题 1 的证明。* 记 $q=Q^{\mathrm{jitter}}(\Omega\setminus\operatorname{supp}(P_{\mathrm{ref}}))\ge t$；当 $\operatorname{supp}(P_{\mathrm{src}})\subseteq\{a,\ldots,255-a\}^3$ 时，每个源色号产生 $(2a+1)^3$ 个等概率结果，其中至多 $r$ 个落入 $\operatorname{supp}(P_{\mathrm{ref}})$，故 $q\ge\max(0,1-r/(2a+1)^3)$。由 $Q\mapsto D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q)$ 的凸性及 $\mathbb E[\hat Q_n^{\mathrm{jitter}}]=Q^{\mathrm{jitter}}$，Jensen 不等式给出 $\mathbb E[D_{\mathrm{hex}}(P_{\mathrm{ref}},\hat Q_n^{\mathrm{jitter}})]\ge D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})$（主稿图 3(a) 在固定已观察到的清洁查询颜色后对每次观测各加一次独立随机扰动，条件下即将 $P_{\mathrm{src}}$ 取为查询经验直方图并求期望）。以指示映射 $T(x)=\mathbf 1[x\notin\operatorname{supp}(P_{\mathrm{ref}})]$ 作二元粗化，将 $P_{\mathrm{ref}}$ 映射为 $(1,0)$、$Q^{\mathrm{jitter}}$ 映射为 $(1-q,q)$；因 $D_{\mathrm{JSD}}$ 是带严格凸生成元的 Csiszár $f$-散度 [33]，数据处理不等式给出 $D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})\ge D_{\mathrm{JSD}}((1,0)\|(1-q,q))=\psi(q)$（$\psi$ 见主稿式 (1)）。在 $(0,1)$ 上 $\psi'(q)=\tfrac12\big(1-\log_2\tfrac{2(1-q)}{2-q}\big)>\tfrac12>0$，故 $\psi(q)\ge\psi(t)\ge t/2$。等式 $D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})=\psi(t)$ 成立当且仅当 $q=t$ 且在 $\operatorname{supp}(P_{\mathrm{ref}})$ 上恒有 $Q^{\mathrm{jitter}}(x)=(1-t)P_{\mathrm{ref}}(x)$，任一内部单点参考均可取到等号（$r=1$；如 $a=1, t=26/27$ 时 $D_{\mathrm{JSD}}=\psi(26/27)\approx0.8847$）。$\blacksquare$

*引理 1 的证明。* 主稿式 (2) 步长为 $w$ 的任一网格区间上至多两个帐篷核 $w_k(c)=\max(0,1-|c/w-k|)$ 非零，斜率为 $\pm 1/w$，故 $\sum_{k=0}^6|w_k(c)-w_k(c')|\le(2/w)|c-c'|$。对三维乘积按 $d\in\{R,G,B\}$ 逐维作望远镜分解并利用其余维权重和为 $1$，得 $\|W(\mathbf c)-W(\mathbf c')\|_1\le(2/w)\|\mathbf c-\mathbf c'\|_1\le(6/w)\|\mathbf c-\mathbf c'\|_\infty$。对逐通道位移不超过 $a$ 的配对样本取均值后有 $\|P_{\mathrm{soft}}(S)-P_{\mathrm{soft}}(S')\|_1\le 6a/w$，结合 $D_{\mathrm{JSD}}(P\|Q)\le\tfrac12\|P-Q\|_1$ [25] 与 $D_{\mathrm{JSD}}\le 1$ 得 $D_{\mathrm{JSD}}(P_{\mathrm{soft}}(S)\|P_{\mathrm{soft}}(S'))\le b$，其中 $b=\min(1,3a/w)$。再由 $\sqrt{D_{\mathrm{JSD}}}$ 的度量性质 [34]，记 $x=\sqrt{D_{\mathrm{svox}}(P_{\mathrm{ref}},S)}\in[0,1]$、$y=\sqrt{D_{\mathrm{svox}}(P_{\mathrm{ref}},S')}\in[0,1]$，即得 $|y-x|\le\sqrt b$，进而原始得分满足 $|y^2-x^2|=|y-x|(y+x)\le\min(1,2\sqrt b)$。$\blacksquare$

*命题 2 的证明。* 记跨组均距 $d=d_{UV}\ge 0$；对 V 统计量（$n,m\ge 1$，含对角项）令 $h=\tfrac12(d_{UU}+d_{VV})$，对 U 统计量（$n,m\ge 2$，排除对角项 [27]）令 $h=\tfrac12(\tilde d_{UU}+\tilde d_{VV})$，其中 $\tilde d_{UU}=\frac{n}{n-1}d_{UU}$、$\tilde d_{VV}=\frac{m}{m-1}d_{VV}$。将三角不等式 $\|u_i-u_{i'}\|_2\le\|u_i-v_j\|_2+\|u_{i'}-v_j\|_2$ 关于 $j\in\{1,\ldots,m\}$ 及全部 $(i,i')$ 或非对角 $i\ne i'$ 求平均，可得 $0\le d_{UU},\tilde d_{UU}\le 2d_{UV}$，对称地 $0\le d_{VV},\tilde d_{VV}\le 2d_{UV}$，故两种取法均有 $(d,h)\in\mathcal C=\{(d,h)\in\mathbb R^2:d\ge 0,\;0\le h\le 2d\}$。区域 $\mathcal C$ 是凸锥，当 $\delta_0>0$ 时，$F(d,h)=(d-h)/(d+\delta_0)$ 在 $\mathcal C$ 上光滑，且满足
$$\left|\frac{\partial F}{\partial d}\right|=\frac{h+\delta_0}{(d+\delta_0)^2}\le\frac{2d+\delta_0}{(d+\delta_0)^2}=\frac{(d+\delta_0)^2-d^2}{\delta_0(d+\delta_0)^2}\le\frac{1}{\delta_0},\qquad\left|\frac{\partial F}{\partial h}\right|=\frac{1}{d+\delta_0}\le\frac{1}{\delta_0}.$$
若只移动 $V$ 中各点且每点欧氏位移至多 $\epsilon$（$\|v'_j-v_j\|_2\le\epsilon$），每个跨组距离变化至多 $\epsilon$，每个 $V$ 内点对距离变化至多 $2\epsilon$（对角项为 $0$）而 $U$ 内距离不变，故 $|d'-d|\le\epsilon$、$|h'-h|\le\epsilon$。沿凸锥 $\mathcal C$ 中连接 $(d,h)$ 与 $(d',h')$ 的线段利用偏导上界积分（有限增量界），得 $|F(d',h')-F(d,h)|\le(|d'-d|+|h'-h|)/\delta_0\le 2\epsilon/\delta_0$，由此一次给出 $\tilde D_{\mathrm{E-reg}}$（因 $\widehat{\mathcal E}_V^2\ge 0$ [26]）和带符号 U 比值的单侧界 $2\epsilon/\delta_0$。因取正部 $z\mapsto[z]_+=\max(0,z)$ 是 $1$-Lipschitz 映射且 $d+\delta_0>0$，截断 U 比值 $[F(d,h)]_+=[\widehat{\mathcal E}_U^2]_+/(2d_{UV}+2\delta_0)$ 同样满足 $|[F(d',h')]_+-[F(d,h)]_+|\le|F(d',h')-F(d,h)|\le 2\epsilon/\delta_0$；又由 $h\ge 0$ 与 $\delta_0>0$ 知 $0\le[F(d,h)]_+\le d/(d+\delta_0)<1$，故严格小于 $1$ 的是截断后的比值。依次移动两侧 $(U,V)\to(U,V')\to(U',V')$ 即得双侧界 $4\epsilon/\delta_0$。$\blacksquare$

### 高斯 Bures–Wasserstein 对照定义

作为基于矩的对照基线，我们将 $U,V$ 拟合为样本均值 $\mu_U,\mu_V$ 与有偏样本协方差 $\Sigma_U,\Sigma_V$（除数为 $|U|$ 与 $|V|$，单样本时置零）加岭项 $\gamma I$（$\gamma=10^{-3}$，单位为 RGB100 长度平方），结合均值偏移与 Bures–Wasserstein 协方差距离 [28] 计算
$$W_2^2=\|\mu_U-\mu_V\|_2^2+\operatorname{tr}\!\left(\Sigma_U+\Sigma_V-2(\Sigma_U^{1/2}\Sigma_V\Sigma_U^{1/2})^{1/2}\right),\qquad D_{W_2}=1-e^{-W_2/50},$$
其中长度尺度 $50$ 的单位为 RGB100 长度；在 Dataset B 与 Dataset C 的 $P_2$ 四样本半集上，$D_{W_2}$ 的线性 EER 分别为 2.22% 与 16.67%。

## H. 网关与 Bootstrap 完整结果

**表 S4：补充主稿表 4 的 Study S1 附加基线结果**

<!-- RGB_TABLE_6 -->
| 注册 → 查询 (6v6) | Metric | Top-1 | AUC | Linear EER | 正例 / 负例均值 | 冻结 B3v3 FRR / FAR |
| --- | --- | --- | --- | --- | --- | --- |
| CF0 → CF21 | $D_{\mathrm{hex}}$ | 14/14 | 1.0000 | 0.00% | 0.2671 / 0.7541 | 0.00% / 0.55% |
| CF0 → CF21 (heldout4) | $D_{\mathrm{RM}}$ | 4/4 | 1.0000 | 0.00% | 0.0881 / 0.4069 | 0.00% / 0.00% |
| CF0 → OR21 | $D_{\mathrm{side}}$ | 10/14 | 0.7392 | 28.57% | 0.1118 / 0.1771 | — |
<!-- /RGB_TABLE_6 -->

**表注：** 其余 11 行 Study S1 迁移结果（$D_{\mathrm{RM}}$、$\tilde D_{\mathrm{E-reg}}$ 与 $D_{\mathrm{hyb}}$ 在 `CF0 → CF21`、`CF0 → CF21 (heldout4)`、`CF21 → OR21` 与 `CF0 → OR21` 上的表现）见主稿表 4，B6v6 与 52 对开放集 `heldout4` 分母的详细说明见主稿第 5.5 节与表 5。`CF0` 合并了 B 的 10 个开发模型（与 B 阈值标定共享 1,200 条记录）及 4 个持出集 E 模型（`heldout4`）。

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

**表注：** 区间对 $\tilde D_{\mathrm{E-reg}}$ 按模型簇有放回重采样（2,000 次抽样，种子 20261111；其中 `C P2` 对应表 S6 中 `P2 odd/even` 的 $\tilde D_{\mathrm{E-reg}}$ 列）。模型数为 4 的各组在 2,000 次 bootstrap 中剔除 27 次单一身份抽样，保留 1,973 次。零宽区间仅描述所观测样本池（作为对照，四次独立 Bernoulli 试验均无失败时的单侧精确 95% 二项上界为 52.71%）。




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

**输入、输出目录与完整性校验。** 全部运行分析均读取支撑 Datasets A–E 与 Studies S1–S4 的 12 份冻结语料 JSONL 日志（去重后共 34,528 条云端响应），以及版本化提示词/目标配置与冻结统计基线（`results/benchmark/`、`results/corpus_stats/`）。`results/integrity_manifest.json` 记录全部 58 个受保护语料、配置文件与冻结基线的 SHA-256 摘要。`scripts/` 下的离线脚本（`OPENBLAS_NUM_THREADS=1`）安装 Python 审计钩子以阻断网络与子进程调用，在运行前后核验受保护文件的 SHA-256 摘要（其中 `energy_u_analysis.py` 校验其 11 个输入与源码文件的摘要，并拒绝覆盖已存在的 `results.json`），且统一支持 `--output` 将新结果写入用户指定路径而不改动 `results/` 下的归档目录（`benchmark/`、`corpus_stats/`、`service_audit/`、`energy_u/`、`protocol_audit/`、`diagnostics/`）。历史冻结基线入口 `reproduce_all.py` 与 `extensions/live_validation_20261111/lv_analyze.py`（自身源码摘要由 `lv_rgb_integrity_manifest.json` 锁定）不导入任何 API 客户端，仅读取本地 JSONL 日志并通过 `--output`/`--manifest` 输出带 SHA-256 摘要的结果清单；`paper/sync_*.py --check` 与 `scripts/verify_manuscript.py` 端到端校验两份哈希清单、表块同步与 PDF 构建。

**协议、同概念对照与子提供商取证。** 跨 12 个正式语料 JSONL 日志（`protocol_hyperparameter_audit.json`），Datasets A–C 省略显式温度字段（`temperature_sent=null`），D、E 和 `S1_CF21` 仅在直连 Workers AI 的 1–2 个端点上传入 `temperature=1.0`，`S1_OR21`、S2、S3 和 S4 则统一传入 `temperature=1.0`。在 B-20×6 与 D 上汇总全部 $K=20$ 个双语单元（每侧 60 次调用，`subset_mmd_diagnostics.json`）时，Color MMD-U、$\tilde D_{\mathrm{E-reg}}$、$D_{\mathrm{hex}}$ 与 Word MMD-U 的线性 EER 均为 0.00%，规范化 Word JSD 为 1.11%。在 S3 原始日志上（`scripts/sensitivity_checks.py`），事后仅取两道匹配英文颜色概念题（`hex_random`、`hex_favorite` 对照 `brk_rand_color`、`brk_fav_color`；20 个端点、20 个同身份对与 380 个有向异身份对，奇偶划分，保留空串与无效响应的精确有理数原始字符串 MMD-U），3v3（前 6 次）下线性 EER 为 17.92%（颜色，0.9156 AUC）对 20.21%（单词，0.8349 AUC），15v15（全部 30 次）下为 5.26%（0.9909 AUC）对 5.00%（0.9784 AUC）。在 Study S1 中，`OR21` 对五个推理端点（`gw-gemini-3.8-flash`、`gw-gemini-4-argon`、`gw-gpt-5.5`、`gw-gpt-6-astra`、`gw-gpt-6-luna` 对应的 `or-*`）传入 `reasoning.effort="low"`，而 Cloudflare 在 `cf-llama-3.3-70b-fp8-fast` 上返回 `-sd` 投机解码标签。将无 `reasoning.effort` 覆盖的九个标准端点与上述五个端点分开统计，Székely–Rizzo 同模型拒绝率（$p\le0.05$）在 `CF0 → CF21` 上为 1/9（11.11%）对 0/5（0.00%），在 `CF21 → OR21` 上为 2/9（22.22%）对 2/5（40.00%），在 `CF0 → OR21` 上为 4/9（44.44%）对 2/5（40.00%）；$\tilde D_{\mathrm{E-reg}}$ 与 $D_{\mathrm{hyb}}$ 在三条路径的两个子组上重扫 EER 均为 0.00%，而在冻结 B3v3 原始 $\tilde D_{\mathrm{E-reg}}$ 阈值（$\tau\approx 0.14802$）下，九个标准端点在全部路径上的 FRR 均为 0.00%，在 `CF21 → OR21` 与 `CF0 → OR21` 上 FAR 为 0.00%，在 `CF0 → CF21` 上 FAR 为 1/72 = 1.39%（误接受项为 `gw-gpt-4.1 → gw-gpt-4o`，得分 0.13359，与主稿第 5.5 节 52 对开放集 `heldout4` 分母中的 1/52 为同一配对）。在 S3 中，OpenRouter 默认负载均衡将 7/20 个端点分发至多个子提供商（S4a 为 `6/20`、S4b 为 `5/20`、`S1_OR21` 为 `5/14`，设 `allow_fallbacks=false` 的 S2 为 `0/18`；奇偶折半子提供商 TV 均值为 0.0419，最大值在 `s3-mistral-small-3.2` 上为 0.1200）。在 `s3-deepseek-v3.2` 上，`GMICloud`（158/300 次调用）输出 40–907 个 Token（中位数 132），而 `DeepInfra`（137 次）、`AtlasCloud`（4 次）与 `DigitalOcean`（1 次）仅为 3–8 个输出 Token（使情景 G 查询费用升至 0.2711 USD，其余 19 个端点为 0.0292–0.0432 USD，第 90 百分位 0.0422 USD；见主稿第 4.2 与 6.4 节）；全部 3/12,000 条 `output_tokens=64` 且 `finish_reason="length"` 的 S3 记录均来自 `s3-nemotron-3.5-light`（全量非有效解析共 15/12,000 条）。

**标定范围、随机化与有限样本能量。** 同家族负例为共享版本化家族映射的不同声明标签；A 与 B 共享 480 条记录，B 自身冻结误差为回代结果。混合路由使用 2026111300–2026111319 共二十个种子，在 $q\in\{0,0.2,0.4,0.5,0.6,0.8,1\}$（$\lambda=1-q$）上无放回重抽样（`routing.csv`、`routing_seeds.csv`、`routing_pairs.csv`、`routing_frozen_thresholds.json`；5–95% 种子带刻画既有池上的重抽样变异而非独立部署不确定性）。表格 RGB 抖动使用种子 20261021–20261030，主稿图 3 的半径扫描使用 20261111–20261120。配对 V/U 评估要求 $n_c,m_c\ge 2$（主稿表 5 采用 $n_c,m_c\ge 1$）；注册中心化（主稿第 3.5 节）每单元使用 256 次 bootstrap 抽样，仅在 B 上拟合 $\alpha$。

**计时、Token 费率与调度。** `local_timing.json` 在单线程 arm64 环境（Python 3.13.15、NumPy 2.5.5、`OPENBLAS_NUM_THREADS=1`）上对三组预加载的 Dataset B 单对样本在预热后计时（不含 API、解析、磁盘 I/O、注册与图库检索）：在 20 单元 3v3、40 单元 8v7 与 10 单元 8v7 批次上，$\tilde D_{\mathrm{E-reg}}$（重复 60 次）的中位数耗时分别为 0.12、0.31 与 0.08 毫秒，999 次分层能量置换检验（重复 30 次）的中位数耗时分别为 2.39、10.15 与 2.51 毫秒。`overhead_per_target.csv` 分离注册与查询开销并将无效解析计入总量；`current_pricing_snapshot.json` 归档 2026 年 11 月 13 日 OpenRouter 目录 [29]，用于情景 L（0.71/0.71 USD）与情景 G（每百万输入/输出 Token 2.50/10 USD，不含缓存折扣），并发时间列按记录的单次请求延迟在理想工作线程上回放估算。

## L. 数值扰动与响应复用分析

表 S8 在冻结 B8v7 阈值（原始 $\tau=0.095249$，中心化 $\tau_{\mathrm{self}}=0.046821$；均匀抖动平均十个种子）下评估 B（$40\times 15$）上的合成内存 RGB 扰动，用于检验数值连续性而非真实网关行为。

**表 S8：B 40×15 后处理扰动下的重扫 EER 与冻结误差；抖动平均十个种子**

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

**表注：** `Quantization (step 32)` 将 8 比特通道舍入至 32 的倍数并裁剪至 255（$0,32,\ldots,224,255$）。原始 $D_{\mathrm{hyb-reg}}$（主稿式 (4)）在 Shift -8 下的重扫 EER 为 10.00%，自中心化 $\tilde D_{\mathrm{E-reg}}$ 在 Shift +8 与 Shift -8 下分别为 2.22% 与 1.11%。

全局查询扰动在各模型上近似一致地抬高正例距离，保持重扫阈值下的正负例排序，同时将正例推过清洁冻结阈值（中心化进一步放大该效应；持出集 E 迁移结果见主稿表 5）。在 B（$40\times 15$）上，对暴露参考直方图作循环重放与固定种子独立同分布重采样在冻结 B8v7 阈值下对 $D_{\mathrm{hex}},D_{\mathrm{vox}},D_{\mathrm{RM}},\tilde D_{\mathrm{E-reg}},D_{\mathrm{hyb}}$ 实测均记录到 100.00% 接受率（常数质心重放经零熵筛查后为 0.00%；主稿第 6.1 节）。Dataset C（主稿第 5.3 节）单套 64 次调用模板在每个参考模型上的输入与输出 Token 合计在 $P_1$ 中至多 7,719、$P_2$ 中至多 7,023（合并 $P_1+P_2$ 共 128 次调用时为 7,386–14,742）。在 50% 回退混合（$q=0.50$，固定种子）下，B8v7（$40\times 7$）上 $D_{\mathrm{RM}}$、$\tilde D_{\mathrm{E-reg}}$ 和 $D_{\mathrm{hyb}}$ 的误受率（$1-\text{检出率}$）分别为 41.11%、31.11% 和 55.56%（B3v3 $20\times 3$ 为 16.67%、21.11% 和 43.33%；B8v7 能量中心化后降至 14.44%）。表 S9 给出主稿第 6.3 节所汇总的二十种子对比明细（`routing_permutation.csv`）。

**表 S9：二十种子离线混合路由在 20% 回退（$q=0.8,\lambda=0.2$）下的冻结中点与分层 999 次置换检验对比**

| 协议与预算 | 替代切片 | 冻结 $\tau_{\mathrm{mid}}$ 检出率 @$q=0.8$（5–95% 种子带） | 冻结清洁 FRR（$q=1$） | 置换检出率 $p\le0.05$ @$q=0.8$（5–95% 种子带） | 置换清洁 FRR（$q=1$） |
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

**表注：** `@q=0.8` 列对有向替代配对等权平均，而 `清洁 FRR` 对每个唯一合格参考端点等权平均一次（例如 `S3 10×7` 同家族在 19 个多成员家族参考上的唯一参考清洁 FRR 为 1.58%，若如主稿图 6(a) 按同家族配对重数加权则为 1.05%）。
