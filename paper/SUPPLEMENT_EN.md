# Supplementary Material for "Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services"

This supplement provides the color-chart sensitivity analysis, fixed-weight regularization ablation, exact endpoint labels, verbatim probe batteries, stability proofs, and extended validation tables using the same 12 frozen corpus logs as the main manuscript. Citations [24]–[29] retain their main-manuscript numbers, and [30]–[34] are supplement-only references.

## A. Color Charts and Sensitivity

**Injective and Lipschitz color charts.** For any map $\Phi:\Omega_{\mathrm{RGB}}\to\Omega_*\subset\mathbb R^3$ that is injective on the finite $256^3$ sRGB grid without coordinate rounding or bin merging, category relabeling preserves exact-code JSD ($D_{\mathrm{JSD}}(\Phi_\#P\|\Phi_\#Q)=D_{\mathrm{JSD}}(P\|Q)$) and Proposition 1's support-escape events, while strong negative type on bounded $\Omega_*$ [26], [30] ensures $\tilde D_{\mathrm{E},\delta_*}(\Phi_\#P,\Phi_\#Q)=0\iff P=Q$ ($\delta_*>0$). If $\|\Phi(x)-\Phi(x')\|_2\le L_{\max}\|x-x'\|_2$ ($L_{\max}<\infty$), an RGB100 shift of at most $\epsilon$ moves $\Phi$-coordinates by at most $L_{\max}\epsilon$, so Proposition 2 gives one- and two-sided bounds $2L_{\max}\epsilon/\delta_*$ and $4L_{\max}\epsilon/\delta_*$ (capped at $1$ for clipped ratios) for $D_*(U,V)=\tilde D_{\mathrm{E},\delta_*}(\Phi(U),\Phi(V))$.

**Uniformly scaled D65 CIELAB control.** Standard D65-relative sRGB-to-CIELAB conversion [24], [31], [32] (piecewise linear/power transfer without D50 adaptation) is injective on the 8-bit grid, whereas its nonlinear perceptual warping shifts finite-sample energy rankings relative to undistorted RGB100 ($L_{\max}=1$). Table S1 applies a single frozen isotropic scale ($0.7658$, fitted from within-cell pairwise distances in B-20×6 enrollment data alone), mapping $\delta_0=15$ to native CIELAB $\delta_*=19.59$ without channelwise scaling or clipping.

**TABLE S1: Regularized-Energy EER / AUC in RGB100 and Uniformly Scaled CIELAB**

<!-- BENCH_TABLE_charts -->
| Dataset | Condition | RGB100 EER / AUC | CIELAB EER / AUC |
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



## B. Regularization at Fixed Weights

Here $D_{\mathrm{hyb-reg}}$ replaces the unregularized energy component $\bar D_{\mathrm E}$ in $D_{\mathrm{hyb}}$ with $\tilde D_{\mathrm{E-reg}}$ while holding the four mixture weights $(0.35, 0.25, 0.25, 0.15)$ fixed (main manuscript Section 3.4, Eq. (4)).

**TABLE S2: Linear EER for Regularization at Fixed Hybrid Weights**

<!-- BENCH_TABLE_hybrid -->
| Protocol | $\bar D_{\mathrm E}$ | $\tilde D_{\mathrm{E-reg}}$ | $D_{\mathrm{hyb}}$ | $D_{\mathrm{hyb-reg}}$ |
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

D contains word responses, so color energy and color hybrids are undefined there. Leave-one-out family attribution over multi-member-family endpoints (50 of 56 in A and 9 of 10 in E, excluding singleton-family models) also differs from binary verification: regularizing energy ($\bar D_{\mathrm E} \to \tilde D_{\mathrm{E-reg}}$) improves accuracy from 31/50 to 35/50 on A (both hybrids score 36/50) and from 2/9 to 6/9 on E (both hybrids score 7/9).

**Syntax and reasoning-envelope decontamination.** In $D_{\mathrm{side}}$, hex letter-case tags assign `numeric_only` when a valid `#RRGGBB` literal contains only digits `0`–`9` ($10^6/16^6 \approx 5.96\%$ of the RGB cube), and reasoning-length bins read `usage.reasoning_tokens` from the API billing envelope when present before falling back to visible reasoning character counts (`perturbation_diagnostics.json`). First, stripping API reasoning metadata alone (`explicit_reasoning` and `usage.reasoning_tokens`, `content_only_no_envelope`) lowers genuine mean $D_{\mathrm{side}}$ on cross-gateway S1 (`CF0 → OR21`, where OpenRouter returns `reasoning_tokens` while Cloudflare omits them) from 0.1118 to 0.0161, and moves S4a (5v5) $D_{\mathrm{hyb}}$ EER from 1.58% to 2.89% while $\tilde D_{\mathrm{E-reg}}$ remains 0.00%. Second, additionally merging `numeric_only` into `upper` (`pure_content_syntax`) yields 2.63% $D_{\mathrm{hyb}}$ EER on S4a (with $\tilde D_{\mathrm{E-reg}}$ still 0.00%), lowers S1 (`CF0 → OR21`) genuine mean $D_{\mathrm{side}}$ to 0.0064, and lowers $D_{\mathrm{side}}$ AUC/linear EER from 0.7804/30.32% to 0.6557/36.76% on Dataset A and from 0.9722/10.00% to 0.6933/36.00% on Dataset B ($40\times 15$).

<!-- SUPPLEMENT_INVENTORY -->

## C. Complete Endpoint Inventory and Label Provenance

This table lists all 56 Dataset A endpoints, with 48 responses each. Identifiers, declared models, and returned model labels are copied from the frozen response log; family and vendor labels come from the versioned mapping. They are experimental labels, not independently authenticated weight identities or a verified product catalog.

Sources: `data/census_40models.jsonl` (56 endpoints, 2,688 records) and `config/family_map.json`. CF-W denotes Cloudflare Workers AI; CF-G denotes Cloudflare AI Gateway. The provider field for CF-G rows is a target alias and does not independently identify the backend.

**TABLE S3: Dataset A Endpoint Labels**

| Endpoint ID / declared model | Returned model label | Source | Vendor / family |
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

## D. Exact Forty-Cell Multilingual Probe Battery

Source: `config/prompts.json`. 10 tasks, 4 languages, and 40 cells. The quoted prompts preserve the original Unicode text. Each user prompt is paired with the system prompt for its format and language.

### System prompts

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

### User prompts

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


## E. Exact S4a CSS and JSON Canary Probes

Source: `config/prompts.implicit_css.json`. 8 tasks, 2 languages, and 16 cells. The quoted prompts preserve the original Unicode text. Each user prompt is paired with the system prompt for its format and language.

### System prompts

**hex**

**en:** You are a frontend UI engineer configuring web stylesheets and JSON design tokens. Keep code snippets minimal and practical.

**zh:** 你是一名负责配置网页样式表与 JSON 设计变量的前端 UI 工程师。请保持代码片段简洁实用。

### User prompts

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


## F. Exact S4b Comparison Probes

Source: `config/prompts.implicit_v5_exact.json`. 8 tasks, 2 languages, and 16 cells. The quoted prompts preserve the original Unicode text. Each user prompt is paired with the system prompt for its format and language.

### System prompts

**hex**

**en:** You are a concise web styling assistant. Reply with only the requested CSS/HTML hexadecimal color literal.

**zh:** 你是一个简洁的网页样式助手。请仅回复所要求的网页十六进制色值。

**rgb_triplet**

**en:** You are a concise graphics assistant. Reply with only the three comma-separated 0-255 channel integers.

**zh:** 你是一个简洁的图形助手。请仅回复三个用逗号分隔的0到255通道整数。

### User prompts

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

## G. Stability Proofs and Gaussian Baseline

*Proof of Proposition 1.* Let $q=Q^{\mathrm{jitter}}(\Omega\setminus\operatorname{supp}(P_{\mathrm{ref}}))\ge t$; when $\operatorname{supp}(P_{\mathrm{src}})\subseteq\{a,\ldots,255-a\}^3$, each source color produces $(2a+1)^3$ equiprobable outcomes of which at most $r$ lie in $\operatorname{supp}(P_{\mathrm{ref}})$, giving $q\ge\max(0,1-r/(2a+1)^3)$. Convexity of $Q\mapsto D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q)$ and $\mathbb E[\hat Q_n^{\mathrm{jitter}}]=Q^{\mathrm{jitter}}$ yield $\mathbb E[D_{\mathrm{hex}}(P_{\mathrm{ref}},\hat Q_n^{\mathrm{jitter}})]\ge D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})$ by Jensen's inequality (in main-manuscript Fig. 3(a), conditioning on the observed clean query sample fixes $P_{\mathrm{src}}$ at the empirical query histogram and takes expectation over one independent jitter draw per observation). Coarsening $\Omega$ via $T(x)=\mathbf 1[x\notin\operatorname{supp}(P_{\mathrm{ref}})]$ maps $P_{\mathrm{ref}}$ to $(1,0)$ and $Q^{\mathrm{jitter}}$ to $(1-q,q)$; because $D_{\mathrm{JSD}}$ is a Csiszár $f$-divergence with strictly convex generator [33], data processing gives $D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})\ge D_{\mathrm{JSD}}((1,0)\|(1-q,q))=\psi(q)$ with $\psi$ in main-manuscript Eq. (1). Since $\psi'(q)=\tfrac12\big(1-\log_2\tfrac{2(1-q)}{2-q}\big)>\tfrac12>0$ on $(0,1)$, $\psi(q)\ge\psi(t)\ge t/2$. Equality $D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})=\psi(t)$ holds iff $q=t$ and $Q^{\mathrm{jitter}}(x)=(1-t)P_{\mathrm{ref}}(x)$ across $\operatorname{supp}(P_{\mathrm{ref}})$, attained by any interior point-mass reference ($r=1$; e.g., $a=1, t=26/27$ gives $D_{\mathrm{JSD}}=\psi(26/27)\approx 0.8847$). $\blacksquare$

*Proof of Lemma 1.* On each interval of width $w$ in main-manuscript Eq. (2), at most two tent functions $w_k(c)=\max(0,1-|c/w-k|)$ are nonzero with slopes $\pm 1/w$, giving $\sum_{k=0}^6|w_k(c)-w_k(c')|\le(2/w)|c-c'|$. Telescoping across $d\in\{R,G,B\}$ using unit-sum weights on the remaining coordinates yields $\|W(\mathbf c)-W(\mathbf c')\|_1\le(2/w)\|\mathbf c-\mathbf c'\|_1\le(6/w)\|\mathbf c-\mathbf c'\|_\infty$. Averaging over paired samples displaced by at most $a$ per channel gives $\|P_{\mathrm{soft}}(S)-P_{\mathrm{soft}}(S')\|_1\le 6a/w$, so $D_{\mathrm{JSD}}(P\|Q)\le\tfrac12\|P-Q\|_1$ [25] and $D_{\mathrm{JSD}}\le 1$ give $D_{\mathrm{JSD}}(P_{\mathrm{soft}}(S)\|P_{\mathrm{soft}}(S'))\le b$ with $b=\min(1,3a/w)$. Since $\sqrt{D_{\mathrm{JSD}}}$ is a metric [34], setting $x=\sqrt{D_{\mathrm{svox}}(P_{\mathrm{ref}},S)}\in[0,1]$ and $y=\sqrt{D_{\mathrm{svox}}(P_{\mathrm{ref}},S')}\in[0,1]$ yields $|y-x|\le\sqrt b$, and hence $|y^2-x^2|=|y-x|(y+x)\le\min(1,2\sqrt b)$ for raw $D_{\mathrm{svox}}$. $\blacksquare$

*Proof of Proposition 2.* Let $d=d_{UV}\ge 0$, and let $h=\tfrac12(d_{UU}+d_{VV})$ for V-statistics ($n,m\ge 1$, diagonals included) or $h=\tfrac12(\tilde d_{UU}+\tilde d_{VV})$ with $\tilde d_{UU}=\frac{n}{n-1}d_{UU}$, $\tilde d_{VV}=\frac{m}{m-1}d_{VV}$ for U-statistics ($n,m\ge 2$, diagonals excluded [27]). Averaging $\|u_i-u_{i'}\|_2\le\|u_i-v_j\|_2+\|u_{i'}-v_j\|_2$ over $j\in\{1,\ldots,m\}$ and either all $(i,i')$ or off-diagonal $i\ne i'$ gives $0\le d_{UU},\tilde d_{UU}\le 2d_{UV}$, and symmetrically $0\le d_{VV},\tilde d_{VV}\le 2d_{UV}$; hence $(d,h)$ lies in the convex cone $\mathcal C=\{(d,h)\in\mathbb R^2:d\ge 0,\;0\le h\le 2d\}$. For $\delta_0>0$, $F(d,h)=(d-h)/(d+\delta_0)$ is smooth on $\mathcal C$ with
$$\left|\frac{\partial F}{\partial d}\right|=\frac{h+\delta_0}{(d+\delta_0)^2}\le\frac{2d+\delta_0}{(d+\delta_0)^2}=\frac{(d+\delta_0)^2-d^2}{\delta_0(d+\delta_0)^2}\le\frac{1}{\delta_0},\qquad\left|\frac{\partial F}{\partial h}\right|=\frac{1}{d+\delta_0}\le\frac{1}{\delta_0}.$$
When each point of $V$ moves by at most $\epsilon$ in Euclidean norm ($\|v'_j-v_j\|_2\le\epsilon$), every cross-pair distance changes by at most $\epsilon$ and every within-$V$ pair distance changes by at most $2\epsilon$ ($0$ on diagonals) while within-$U$ distances stay fixed, so $|d'-d|\le\epsilon$ and $|h'-h|\le\epsilon$. By the mean value theorem along the segment in $\mathcal C$ between $(d,h)$ and $(d',h')$, $|F(d',h')-F(d,h)|\le(|d'-d|+|h'-h|)/\delta_0\le 2\epsilon/\delta_0$, which simultaneously covers $\tilde D_{\mathrm{E-reg}}$ (since $\widehat{\mathcal E}_V^2\ge 0$ [26]) and the signed U ratio. Because $z\mapsto[z]_+=\max(0,z)$ is $1$-Lipschitz and $d+\delta_0>0$, the clipped U ratio $[F(d,h)]_+=[\widehat{\mathcal E}_U^2]_+/(2d_{UV}+2\delta_0)$ satisfies $|[F(d',h')]_+-[F(d,h)]_+|\le|F(d',h')-F(d,h)|\le 2\epsilon/\delta_0$; moreover $h\ge 0$ and $\delta_0>0$ imply $0\le[F(d,h)]_+\le d/(d+\delta_0)<1$, so the clipped ratio is strictly less than $1$. Chaining $(U,V)\to(U,V')\to(U',V')$ yields $4\epsilon/\delta_0$. $\blacksquare$

### Gaussian Bures–Wasserstein Baseline

As a moment-based control, we fit sample means $\mu_U,\mu_V$ and biased sample covariances $\Sigma_U,\Sigma_V$ (divisor $|U|$ and $|V|$, zero for singletons) plus ridge $\gamma I$ ($\gamma=10^{-3}$ in squared RGB100 units), combining mean shift and Bures–Wasserstein covariance distance [28] via
$$W_2^2=\|\mu_U-\mu_V\|_2^2+\operatorname{tr}\!\left(\Sigma_U+\Sigma_V-2(\Sigma_U^{1/2}\Sigma_V\Sigma_U^{1/2})^{1/2}\right),\qquad D_{W_2}=1-e^{-W_2/50},$$
where $50$ has RGB100 length units; on Dataset B and Dataset C's four-sample $P_2$ halves, $D_{W_2}$ yields 2.22% and 16.67% linear EER, respectively.

## H. Detailed Gateway and Bootstrap Results

**TABLE S4: Additional Study S1 Baselines Complementing Main-Manuscript Table 4**

<!-- RGB_TABLE_6 -->
| Enrollment → query (6v6) | Metric | Top-1 | AUC | Linear EER | Genuine / impostor mean | Frozen B3v3 FRR / FAR |
| --- | --- | --- | --- | --- | --- | --- |
| CF0 → CF21 | $D_{\mathrm{hex}}$ | 14/14 | 1.0000 | 0.00% | 0.2671 / 0.7541 | 0.00% / 0.55% |
| CF0 → CF21 (heldout4) | $D_{\mathrm{RM}}$ | 4/4 | 1.0000 | 0.00% | 0.0881 / 0.4069 | 0.00% / 0.00% |
| CF0 → OR21 | $D_{\mathrm{side}}$ | 10/14 | 0.7392 | 28.57% | 0.1118 / 0.1771 | — |
<!-- /RGB_TABLE_6 -->

**Table note:** Main-manuscript Table 4 reports the remaining 11 Study S1 transfer rows ($D_{\mathrm{RM}}$, $\tilde D_{\mathrm{E-reg}}$, and $D_{\mathrm{hyb}}$ across `CF0 → CF21`, `CF0 → CF21 (heldout4)`, `CF21 → OR21`, and `CF0 → OR21`), and main-manuscript Section 5.5 and Table 5 detail the B6v6 and 52-pair open-set `heldout4` denominators. `CF0` pools B's 10 development models (1,200 rows shared with B calibration) and four held-out E models (`heldout4`).

**TABLE S5: Regularized-Energy ($\tilde D_{\mathrm{E-reg}}$) Model-Cluster Bootstrap Intervals**

<!-- RGB_TABLE_3 -->
| Cohort | Models | AUC [95% CI] | Linear EER [95% CI] |
| --- | --- | --- | --- |
| B | 10 | 1.0000 [1.0000, 1.0000] | 0.00% [0.00%, 0.00%] |
| C P1 | 10 | 1.0000 [1.0000, 1.0000] | 0.00% [0.00%, 0.00%] |
| C P2 | 10 | 0.9978 [0.9895, 1.0000] | 1.11% [0.00%, 5.00%] |
| E | 10 | 0.9900 [0.9536, 1.0000] | 10.00% [0.00%, 18.61%] |
| S1 CF21 heldout4 | 4 | 1.0000 [1.0000, 1.0000] | 0.00% [0.00%, 0.00%] |
| S1 OR21 heldout4 | 4 | 1.0000 [1.0000, 1.0000] | 0.00% [0.00%, 0.00%] |
<!-- /RGB_TABLE_3 -->

**Table note:** Intervals resample model clusters with replacement (2,000 draws, seed 20261111) for $\tilde D_{\mathrm{E-reg}}$ (`C P2` corresponds to the `P2 odd/even` $\tilde D_{\mathrm{E-reg}}$ entry in Table S6). For each Models = 4 cohort, 27 single-identity draws were excluded from 2,000 bootstrap draws, leaving 1,973. Zero-width intervals describe the observed pool (for reference, four independent Bernoulli trials with zero failures carry a one-sided exact 95% binomial upper bound of 52.71%).




## I. Paraphrase and Cross-Template Results

**TABLE S6: Dataset C Within-Paraphrase Self-Verification vs. Zero-Shot Cross-Template Transfer (10 Models, Linear EER / AUC)**

<!-- RGB_TABLE_4 -->
| Protocol; linear EER / AUC (Top-1) | $D_{\mathrm{RM}}$ | $\tilde D_{\mathrm{E-reg}}$ | $D_{\mathrm{hyb}}$ | $D_{\mathrm{vox}}$ | $D_{\mathrm{hex}}$ |
| --- | --- | --- | --- | --- | --- |
| P1 odd/even | 0.00% / 1.0000 | 0.00% / 1.0000 | 0.00% / 1.0000 | 0.00% / 1.0000 | 5.56% / 0.9933 |
| P2 odd/even | 6.67% / 0.9911 | 1.11% / 0.9978 | 0.00% / 1.0000 | 2.22% / 0.9956 | 0.00% / 1.0000 |
| P0 → P1 | 16.67% / 0.9167 (7/10) | 17.78% / 0.8933 (7/10) | 10.00% / 0.9511 (10/10) | 10.00% / 0.9589 (10/10) | 10.00% / 0.9633 (10/10) |
| P0 → P2 | 10.00% / 0.9744 (7/10) | 11.11% / 0.9522 (9/10) | 10.00% / 0.9722 (9/10) | 10.00% / 0.9667 (7/10) | 8.89% / 0.9800 (10/10) |
| P0 → P1+P2 | 10.00% / 0.9667 (9/10) | 15.56% / 0.9400 (10/10) | 10.00% / 0.9756 (10/10) | 8.89% / 0.9678 (10/10) | 10.00% / 0.9822 (10/10) |
<!-- /RGB_TABLE_4 -->


## J. Precision-Regime Provider Results

**TABLE S7: Study S2 Cross-Provider Weight Verification Across 12 Independent Backends (18 Endpoints, 6v6)**

<!-- RGB_TABLE_7 -->
| Precision regime | Metric | Pairs | Mean ± SD | 1-NN (queries) | AUC | Linear EER |
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

**Table note:** Pairs counts unordered same-checkpoint pairs; 1-NN (queries) evaluates unique endpoints participating in each regime (summing to 28 across the 18 endpoints because an endpoint can belong to two regimes across its two partner backends). The moderate regime contains only 2 pairs (3 queries), so its estimates are descriptive.

## K. Reproducing the Offline Analyses

**Inputs, outputs, and integrity.** All operational analyses read the 12 frozen corpus JSONL logs supporting Datasets A–E and Studies S1–S4 (34,528 deduplicated cloud responses) plus versioned prompt/target configurations and frozen baseline tables (`results/benchmark/`, `results/corpus_stats/`). `results/integrity_manifest.json` records SHA-256 digests for all 58 protected files. Offline scripts under `scripts/` (`OPENBLAS_NUM_THREADS=1`) install Python audit hooks blocking network and subprocess calls, verify protected SHA-256 digests before and after execution (`energy_u_analysis.py` checks its 11 input/source digests and refuses to overwrite an existing `results.json`), and accept `--output` to write fresh outputs without touching archived `results/` directories (`benchmark/`, `corpus_stats/`, `service_audit/`, `energy_u/`, `protocol_audit/`, `diagnostics/`). The frozen baseline scripts `reproduce_all.py` and `extensions/live_validation_20261111/lv_analyze.py` (whose own SHA-256 digests are locked in `lv_rgb_integrity_manifest.json`) import no API clients, read local JSONLs only, and emit SHA-256 manifests via `--output`/`--manifest`; `paper/sync_*.py --check` and `scripts/verify_manuscript.py` verify both manifests, table sync, and PDF builds.

**Protocol, matched-concept, and sub-provider forensics.** Across the 12 active corpus JSONL logs (`protocol_hyperparameter_audit.json`), Datasets A–C omit explicit temperature (`temperature_sent=null`), D/E/`S1_CF21` pass `temperature=1.0` only on direct Workers AI calls (1–2 targets), and `S1_OR21`/S2/S3/S4 pass `temperature=1.0` uniformly. Pooling all $K=20$ bilingual cells (60 calls/side) on B-20×6 and D (`subset_mmd_diagnostics.json`) yields 0.00% linear EER for Color MMD-U, $\tilde D_{\mathrm{E-reg}}$, $D_{\mathrm{hex}}$, and Word MMD-U versus 1.11% for canonical Word JSD. On S3's raw logs (`scripts/sensitivity_checks.py`), a post-hoc raw-string exact-rational MMD-U check restricted to the two matched English color-concept tasks (`hex_random`, `hex_favorite` vs. `brk_rand_color`, `brk_fav_color` across 20 endpoints; 20 genuine vs. 380 directed impostor pairs, odd/even split, empty/invalid outputs retained) yields linear EER of 17.92% (color, 0.9156 AUC) vs. 20.21% (word, 0.8349 AUC) at 3v3 (first 6 draws) and 5.26% (0.9909 AUC) vs. 5.00% (0.9784 AUC) at 15v15 (all 30 draws). In S1, `OR21` passes `reasoning.effort="low"` on five reasoning endpoints (`gw-gemini-3.8-flash`, `gw-gemini-4-argon`, `gw-gpt-5.5`, `gw-gpt-6-astra`, `gw-gpt-6-luna` paired with `or-*`), while Cloudflare returns `-sd` on `cf-llama-3.3-70b-fp8-fast`. Splitting the nine standard endpoints (no `reasoning.effort` override) from those five yields Székely–Rizzo genuine rejection rates ($p \le 0.05$) of 1/9 (11.11%) vs. 0/5 (0.00%) on `CF0 → CF21`, 2/9 (22.22%) vs. 2/5 (40.00%) on `CF21 → OR21`, and 4/9 (44.44%) vs. 2/5 (40.00%) on `CF0 → OR21`; $\tilde D_{\mathrm{E-reg}}$ and $D_{\mathrm{hyb}}$ retain 0.00% re-swept EER on both subgroups across all paths, while under frozen B3v3 raw $\tilde D_{\mathrm{E-reg}}$ ($\tau \approx 0.14802$) the nine standard endpoints record 0.00% FRR throughout, 0.00% FAR on `CF21 → OR21` and `CF0 → OR21`, and 1/72 = 1.39% FAR on `CF0 → CF21` (`gw-gpt-4.1 → gw-gpt-4o`, score 0.13359—the same pair counted against the 52-pair `heldout4` open-set denominator in main-manuscript Section 5.5). In S3, OpenRouter load-balances 7/20 endpoints across sub-providers (`6/20` in S4a, `5/20` in S4b, `5/14` in `S1_OR21`, vs. `0/18` in S2; odd/even TV mean 0.0419, max 0.1200 on `s3-mistral-small-3.2`). On `s3-deepseek-v3.2`, `GMICloud` (158/300 calls) emitted 40–907 output tokens (median 132) vs. 3–8 on `DeepInfra` (137), `AtlasCloud` (4), and `DigitalOcean` (1) (raising Scenario G query cost to 0.2711 USD vs. 0.0292–0.0432 USD across the other 19 endpoints, 90th percentile 0.0422 USD; main-manuscript Sections 4.2 and 6.4), while `s3-nemotron-3.5-light` accounted for all 3/12,000 `finish_reason="length"` calls at `output_tokens=64` (15/12,000 non-valid parses overall).

**Calibration scope, randomization, and finite-sample energy.** Same-family negatives share the versioned family mapping across distinct declared labels; A shares 480 rows with B, and B's own frozen errors are resubstitution. Mixed routing uses twenty seeds (2026111300–2026111319) over $q \in \{0, 0.2, 0.4, 0.5, 0.6, 0.8, 1\}$ ($\lambda = 1 - q$) without replacement (`routing.csv`, `routing_seeds.csv`, `routing_pairs.csv`, `routing_frozen_thresholds.json`; 5th–95th seed bands reflect pool resampling rather than independent deployment uncertainty). Tabular RGB jitter uses seeds 20261021–20261030; Fig. 3's radius sweep uses 20261111 through 20261120. Paired V/U evaluation requires $n_c, m_c \ge 2$ ($n_c, m_c \ge 1$ for Table 5); enrollment centering (main-manuscript Section 3.5) uses 256 bootstrap draws per cell and fits $\alpha$ only on B.

**Timing, token prices, and scheduling.** `local_timing.json` records single-threaded arm64 execution (Python 3.13.15, NumPy 2.5.5, `OPENBLAS_NUM_THREADS=1`) over three preloaded Dataset B single-pair fixtures after warm-up (API, parsing, disk I/O, enrollment, and gallery search excluded): on 20-cell 3v3, 40-cell 8v7, and 10-cell 8v7 batches, warm medians are 0.12, 0.31, and 0.08 ms (60 reps) for $\tilde D_{\mathrm{E-reg}}$ and 2.39, 10.15, and 2.51 ms (30 reps) for 999-permutation stratified energy testing. `overhead_per_target.csv` separates enrollment from queries (retaining invalid parses in totals); `current_pricing_snapshot.json` archives the November 13, 2026 OpenRouter catalog [29] for scenarios L (0.71/0.71 USD) and G (2.50/10 USD per million input/output tokens, without cached-input discounts), and concurrent times replay recorded single-call latencies on ideal workers.

## L. Numerical Perturbations and Response-Reuse Analysis

Table S8 evaluates synthetic in-memory RGB perturbations on B ($40\times 15$) under frozen B8v7 cutoffs ($\tau = 0.095249$ raw, $\tau_{\mathrm{self}} = 0.046821$ centered, 10 jitter seeds), testing numerical continuity rather than live gateway behavior.

**TABLE S8: B 40×15 Post-Processing EER and Frozen Errors; Jitter Averages Ten Seeds**

<!-- BENCH_TABLE_perturbation -->
| Condition | Metric | Raw EER | Raw FRR / FAR | Self FRR / FAR |
| --- | --- | --- | --- | --- |
| B jitter ±1 | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 0.00% / 0.00% | 0.00% / 0.00% |
| B jitter ±8 | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 0.00% / 0.00% | 11.00% / 0.00% |
| B jitter ±8 | $D_{\mathrm{hyb-reg}}$ | 0.00% | 100.00% / 0.00% | 100.00% / 0.00% |
| B jitter ±15 | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 56.00% / 0.00% | 89.00% / 0.00% |
| Shift +8 | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 100.00% / 0.00% | 100.00% / 0.00% |
| Shift -8 | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 100.00% / 0.00% | 100.00% / 0.00% |
| Quantization (step 32) | $\tilde D_{\mathrm{E-reg}}$ | 0.00% | 100.00% / 0.00% | 100.00% / 0.00% |
<!-- /BENCH_TABLE_perturbation -->

**Table note:** `Quantization (step 32)` rounds 8-bit channels to multiples of 32 clipped to 255 ($0,32,\ldots,224,255$). Raw $D_{\mathrm{hyb-reg}}$ (main-manuscript Eq. (4)) gives 10.00% re-swept EER at Shift -8; self-centered $\tilde D_{\mathrm{E-reg}}$ gives 2.22% and 1.11% at Shift +8/-8.

Uniform query perturbations shift genuine distances upward across models alike, preserving re-swept pair ordering while crossing clean-frozen cutoffs (amplified by centering; see main-manuscript Table 5 for held-out E). On B ($40\times 15$), cyclic replay and fixed-seed i.i.d. resampling from an exposed reference histogram both recorded 100.00% empirical acceptance under frozen B8v7 cutoffs across $D_{\mathrm{hex}}, D_{\mathrm{vox}}, D_{\mathrm{RM}}, \tilde D_{\mathrm{E-reg}}, D_{\mathrm{hyb}}$ (0.00% for constant-centroid replay after zero-entropy screening; main-manuscript Section 6.1). Single-template 64-call re-enrollment in Dataset C (main-manuscript Section 5.3) used up to 7,719 in $P_1$ and 7,023 in $P_2$ input-plus-output tokens per model (7,386–14,742 across 128 calls for $P_1+P_2$). At 50% fallback mixing ($q=0.50$, fixed seed), B8v7 ($40\times 7$) false-accept rates ($1 - \text{detection}$) are 41.11%, 31.11%, and 55.56% for $D_{\mathrm{RM}}$, $\tilde D_{\mathrm{E-reg}}$, and $D_{\mathrm{hyb}}$ (16.67%, 21.11%, and 43.33% on B3v3 $20\times 3$; 14.44% centered on B8v7). Table S9 details the 20-seed comparison summarized in main-manuscript Section 6.3 (`routing_permutation.csv`).

**TABLE S9: Twenty-Seed Mixed-Routing Detection at 20% Fallback ($q = 0.8$) and Clean FRR ($q = 1$): Frozen $\tau_{\mathrm{mid}}$ vs. 999-Permutation Test ($p \le 0.05$)**

| Protocol (Query Calls) | Subgroup | $\tau_{\mathrm{mid}}$ @ $q=0.8$ (5th–95th) | $\tau_{\mathrm{mid}}$ Clean FRR | Perm. @ $q=0.8$ (5th–95th) | Perm. Clean FRR |
| --- | --- | --- | --- | --- | --- |
| B $20\times 3$ (60) | All distinct | 11.28% (4.39%–20.11%) | 1.00% | 8.56% (4.22%–12.67%) | 4.50% |
| B $20\times 3$ (60) | Same family | 7.50% (0.00%–15.25%) | 1.11% | 9.00% (4.75%–15.25%) | 5.00% |
| B $40\times 7$ (280) | All distinct | 0.33% (0.00%–1.17%) | 0.00% | 33.28% (27.61%–40.00%) | 0.00% |
| B $40\times 7$ (280) | Same family | 0.00% (0.00%–0.00%) | 0.00% | 25.75% (10.00%–40.00%) | 0.00% |
| S3 $10\times 3$ (30) | All distinct | 55.97% (51.25%–61.11%) | 39.00% | 6.66% (2.59%–11.87%) | 4.75% |
| S3 $10\times 7$ (70) | All distinct | 12.45% (7.83%–16.14%) | 3.75% | 17.57% (11.29%–22.64%) | 4.50% |
| S3 $10\times 7$ (70) | Same family | 5.00% (0.00%–10.53%) | 1.58% | 16.71% (10.13%–23.82%) | 3.95% |
| S1 CF0→OR21 $20\times 3$ (60) | All distinct | 29.95% (24.97%–37.99%) | 11.07% | 19.53% (12.06%–25.93%) | 16.07% |
| S1 CF21→OR21 $20\times 3$ (60) | All distinct | 26.37% (21.95%–33.52%) | 18.57% | 15.22% (9.18%–22.64%) | 13.93% |

**Table note:** `@ q=0.8` columns average equally across directed substitute pairs, whereas `Clean FRR` averages once per unique eligible reference endpoint (for `S3 10×7` same-family, unique-reference clean FRR is 1.58% across 19 multi-member-family references versus 1.05% when weighted by same-family pair multiplicity as in main-manuscript Fig. 6(a)).
