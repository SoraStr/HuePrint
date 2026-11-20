# Supplementary Material for "Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services"

This supplement provides the color-chart sensitivity analysis, fixed-weight regularization and side-channel decontamination ablations, endpoint labels, verbatim probe batteries, stability proofs (including soft-voxel smoothing and Lemma 1), and extended validation tables. All analyses use the same 15 frozen corpus logs (12 baseline plus 3 Study S5 logs; 38,688 cloud responses) as the main manuscript. Citations [4], [16], and [24]–[29] retain their main-manuscript numbers, and [30]–[34] are supplement-only references.

## A. Color Charts and Sensitivity

**Injective and Lipschitz color charts.** Let $\Phi:\Omega_{\mathrm{RGB}}\to\Omega_*\subset\mathbb R^3$ be any map that is injective on the finite $256^3$ sRGB grid without coordinate rounding or bin merging. Category relabeling preserves exact-code JSD ($D_{\mathrm{JSD}}(\Phi_\#P\|\Phi_\#Q)=D_{\mathrm{JSD}}(P\|Q)$) and Proposition 1's support-escape events, while strong negative type on bounded $\Omega_*$ [26], [30] ensures $\tilde D_{\mathrm{E},\delta_*}(\Phi_\#P,\Phi_\#Q)=0\iff P=Q$ ($\delta_*>0$). If $\|\Phi(x)-\Phi(x')\|_2\le L_{\max}\|x-x'\|_2$ ($L_{\max}<\infty$), an RGB100 shift of at most $\epsilon$ moves $\Phi$-coordinates by at most $L_{\max}\epsilon$. Proposition 2 then gives one- and two-sided bounds $2L_{\max}\epsilon/\delta_*$ and $4L_{\max}\epsilon/\delta_*$ (capped at $1$ for clipped ratios) for $D_*(U,V)=\tilde D_{\mathrm{E},\delta_*}(\Phi(U),\Phi(V))$.

**Uniformly scaled D65 CIELAB control.** Standard D65-relative sRGB-to-CIELAB conversion [24], [31], [32] (piecewise linear/power transfer without D50 adaptation) is injective on the 8-bit grid, but its nonlinear perceptual warping shifts finite-sample energy rankings relative to undistorted RGB100 ($L_{\max}=1$). Table S1 applies a single frozen isotropic scale ($0.7658$, fitted from within-cell pairwise distances in B-20×6 enrollment data alone), mapping $\delta_0=15$ to native CIELAB $\delta_*=19.59$ without channelwise scaling or clipping.

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

Here $D_{\mathrm{hyb-reg}} = 0.35 D_{\mathrm{vox}} + 0.25 D_{\mathrm{hex}} + 0.25 \tilde D_{\mathrm{E-reg}} + 0.15 D_{\mathrm{side}}$ replaces the unregularized energy component $\bar D_{\mathrm E}$ in $D_{\mathrm{hyb}}$ with $\tilde D_{\mathrm{E-reg}}$ while holding the four mixture weights $(0.35, 0.25, 0.25, 0.15)$ fixed (main manuscript Section 3.3, Eq. (3)).

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

D contains word responses, so color energy and color hybrids are undefined there. Leave-one-out family attribution over multi-member-family endpoints (50 of 56 in A and 9 of 10 in E, excluding singleton-family models) also differs from binary verification. Regularizing energy ($\bar D_{\mathrm E} \to \tilde D_{\mathrm{E-reg}}$) raises accuracy from 31/50 to 35/50 on A (both hybrids score 36/50) and from 2/9 to 6/9 on E (both hybrids score 7/9).

**Syntax and reasoning-envelope decontamination.** In $D_{\mathrm{side}}$, hex letter-case tags assign `numeric_only` when a valid `#RRGGBB` literal contains only digits `0`–`9` ($10^6/16^6 \approx 5.96\%$ of the RGB cube). Reasoning-length bins read `usage.reasoning_tokens` from the API billing envelope when present before falling back to visible reasoning character counts (`perturbation_diagnostics.json`).

First, stripping API reasoning metadata alone (`explicit_reasoning` and `usage.reasoning_tokens`, `content_only_no_envelope`) lowers genuine mean $D_{\mathrm{side}}$ on cross-gateway S1 (`CF0 → OR21`, where OpenRouter returns `reasoning_tokens` while Cloudflare omits them) from 0.1118 to 0.0161. On Study S2 across 12 pinned hosts (`operational_diagnostics.json`), `content_only_no_envelope` leaves 6v6 $D_{\mathrm{hyb}}$ EER unchanged at 5.93% (0.9864 AUC, 17/18 Top-1; 3v3: 12.59% EER), while moving S4a (5v5) $D_{\mathrm{hyb}}$ EER from 1.58% to 2.89% ($\tilde D_{\mathrm{E-reg}}$ remains 0.00%). Second, additionally merging `numeric_only` into `upper` (`pure_content_syntax`) yields 5.56% 6v6 $D_{\mathrm{hyb}}$ EER on Study S2 (0.9864 AUC, 17/18 Top-1; 3v3: 12.96%), 2.63% on S4a ($\tilde D_{\mathrm{E-reg}}$ still 0.00%), and 0.0064 genuine mean $D_{\mathrm{side}}$ on S1 (`CF0 → OR21`). That variant also lowers standalone $D_{\mathrm{side}}$ AUC/linear EER from 0.7804/30.32% to 0.6557/36.76% on Dataset A and from 0.9722/10.00% to 0.6933/36.00% on Dataset B ($40\times 15$). Third, omitting $D_{\mathrm{side}}$ altogether (`color_composite_no_side`, renormalizing the three color terms $(0.35, 0.25, 0.25)/0.85$) still reaches 9.63% 6v6 EER (0.9749 AUC, 17/18 Top-1; 3v3: 14.44%) on Study S2, outperforming single-scale $\tilde D_{\mathrm{E-reg}}$ and Color MMD-U (both 16.67%).

<!-- SUPPLEMENT_INVENTORY -->

## C. Complete Endpoint Inventory and Label Provenance

This table lists all 56 Dataset A endpoints, with 48 responses each. Identifiers, declared models, and returned model strings are recorded verbatim from the frozen API response log; family and vendor groupings follow the versioned `config/family_map.json` mapping.

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

## G. Stability Proofs, Soft-Voxel Baseline, and Gaussian Control

*Proof of Proposition 1.* Let $q=Q^{\mathrm{jitter}}(\Omega\setminus\operatorname{supp}(P_{\mathrm{ref}}))\ge t$; when $\operatorname{supp}(P_{\mathrm{src}})\subseteq\{a,\ldots,255-a\}^3$, each source color produces $(2a+1)^3$ equiprobable outcomes of which at most $r$ lie in $\operatorname{supp}(P_{\mathrm{ref}})$, giving $q\ge\max(0,1-r/(2a+1)^3)$. Convexity of $Q\mapsto D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q)$ and $\mathbb E[\hat Q_n^{\mathrm{jitter}}]=Q^{\mathrm{jitter}}$ yield $\mathbb E[D_{\mathrm{hex}}(P_{\mathrm{ref}},\hat Q_n^{\mathrm{jitter}})]\ge D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})$ by Jensen's inequality (in main-manuscript Fig. 3(a), conditioning on the observed clean query sample fixes $P_{\mathrm{src}}$ at the empirical query histogram and takes expectation over one independent jitter draw per observation). Coarsening $\Omega$ via $T(x)=\mathbf 1[x\notin\operatorname{supp}(P_{\mathrm{ref}})]$ maps $P_{\mathrm{ref}}$ to $(1,0)$ and $Q^{\mathrm{jitter}}$ to $(1-q,q)$; because $D_{\mathrm{JSD}}$ is a Csiszár $f$-divergence with strictly convex generator [33], data processing gives $D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})\ge D_{\mathrm{JSD}}((1,0)\|(1-q,q))=\psi(q)$ with $\psi$ in main-manuscript Eq. (1). Since $\psi'(q)=\tfrac12\big(1-\log_2\tfrac{2(1-q)}{2-q}\big)>\tfrac12>0$ on $(0,1)$, $\psi(q)\ge\psi(t)\ge t/2$. Equality $D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})=\psi(t)$ holds iff $q=t$ and $Q^{\mathrm{jitter}}(x)=(1-t)P_{\mathrm{ref}}(x)$ across $\operatorname{supp}(P_{\mathrm{ref}})$, attained by any interior point-mass reference ($r=1$; e.g., $a=1, t=26/27$ gives $D_{\mathrm{JSD}}=\psi(26/27)\approx 0.8847$). $\blacksquare$

*Proof of Proposition 2.* Let $d=d_{UV}\ge 0$, and let $h=\tfrac12(d_{UU}+d_{VV})$ for V-statistics ($n,m\ge 1$, diagonals included) or $h=\tfrac12(\tilde d_{UU}+\tilde d_{VV})$ with $\tilde d_{UU}=\frac{n}{n-1}d_{UU}$, $\tilde d_{VV}=\frac{m}{m-1}d_{VV}$ for U-statistics ($n,m\ge 2$, diagonals excluded [27]). Averaging $\|u_i-u_{i'}\|_2\le\|u_i-v_j\|_2+\|u_{i'}-v_j\|_2$ over $j\in\{1,\ldots,m\}$ and either all $(i,i')$ or off-diagonal $i\ne i'$ gives $0\le d_{UU},\tilde d_{UU}\le 2d_{UV}$, and symmetrically $0\le d_{VV},\tilde d_{VV}\le 2d_{UV}$; hence $(d,h)$ lies in the convex cone $\mathcal C=\{(d,h)\in\mathbb R^2:d\ge 0,\;0\le h\le 2d\}$. For $\delta_0>0$, $F(d,h)=(d-h)/(d+\delta_0)$ is smooth on $\mathcal C$ with
$$\left|\frac{\partial F}{\partial d}\right|=\frac{h+\delta_0}{(d+\delta_0)^2}\le\frac{2d+\delta_0}{(d+\delta_0)^2}=\frac{(d+\delta_0)^2-d^2}{\delta_0(d+\delta_0)^2}\le\frac{1}{\delta_0},\qquad\left|\frac{\partial F}{\partial h}\right|=\frac{1}{d+\delta_0}\le\frac{1}{\delta_0}.$$
When each point of $V$ moves by at most $\epsilon$ in Euclidean norm ($\|v'_j-v_j\|_2\le\epsilon$), every cross-pair distance changes by at most $\epsilon$ and every within-$V$ pair distance changes by at most $2\epsilon$ ($0$ on diagonals) while within-$U$ distances stay fixed, so $|d'-d|\le\epsilon$ and $|h'-h|\le\epsilon$. By the mean value theorem along the segment in $\mathcal C$ between $(d,h)$ and $(d',h')$, $|F(d',h')-F(d,h)|\le(|d'-d|+|h'-h|)/\delta_0\le 2\epsilon/\delta_0$, which simultaneously covers $\tilde D_{\mathrm{E-reg}}$ (since $\widehat{\mathcal E}_V^2\ge 0$ [26]) and the signed U ratio. Because $z\mapsto[z]_+=\max(0,z)$ is $1$-Lipschitz and $d+\delta_0>0$, the clipped U ratio $[F(d,h)]_+=[\widehat{\mathcal E}_U^2]_+/(2d_{UV}+2\delta_0)$ satisfies $|[F(d',h')]_+-[F(d,h)]_+|\le|F(d',h')-F(d,h)|\le 2\epsilon/\delta_0$. Since $h\ge 0$ and $\delta_0>0$, we also have $0\le[F(d,h)]_+\le d/(d+\delta_0)<1$, so the clipped ratio is strictly less than $1$. Chaining $(U,V)\to(U,V')\to(U',V')$ yields $4\epsilon/\delta_0$. $\blacksquare$

### Soft-Voxel Smoothing, Multi-Scale Composite, and Lemma 1

As a smooth-histogram alternative to continuous RGB energy, fix grid spacing $w=48$ in raw 8-bit channel units and lattice nodes $\mathcal I=\{0,\ldots,6\}^3$, and define trilinear tent weights
$$W_i(\mathbf c)=\prod_{d\in\{R,G,B\}}\max(0,1-|c_d/w-i_d|),\qquad P_{\mathrm{soft}}(i\mid S)=|S|^{-1}\sum_{\mathbf c\in S}W_i(\mathbf c).$$
Since $255/w=5.3125<6$, the weights satisfy $W_i(\mathbf c)\ge 0$ and $\sum_{i\in\mathcal I}W_i(\mathbf c)=1$ on $[0,255]^3$, so $P_{\mathrm{soft}}(\cdot\mid S)$ is a valid probability vector and $D_{\mathrm{svox}}$ is the base-2 JSD between two soft histograms. Combining soft voxels with regularized energy defines the regularized multi-scale composite $D_{\mathrm{RM}}=0.50 D_{\mathrm{svox}}+0.50\tilde D_{\mathrm{E-reg}}$. Empirically, $D_{\mathrm{RM}}$ trails $\tilde D_{\mathrm{E-reg}}$ on Dataset A (8.93% vs. 5.36% linear EER; 0.9582 AUC; 34/50 LOO family attribution). Across $\delta_0 \in \{2,5,10,15,25,50\}$, $w \in \{24,32,48,64\}$, and soft-voxel weights $\{0.4,0.5,0.6\}$, $D_{\mathrm{RM}}$ spans 4.44%–10.00% EER on Dataset E while matching $\tilde D_{\mathrm{E-reg}}$ at 0.00% EER on B and S1 (Tables S4a–S4b, S6).

**Lemma 1 (Soft-voxel stability)**. For $\mathbf c,\mathbf c'\in[0,255]^3$, $\|W(\mathbf c)-W(\mathbf c')\|_1\le(2/w)\|\mathbf c-\mathbf c'\|_1\le(6/w)\|\mathbf c-\mathbf c'\|_\infty$, so paired samples $S,S'$ shifted by at most $a$ per channel satisfy $D_{\mathrm{JSD}}(P_{\mathrm{soft}}(S)\|P_{\mathrm{soft}}(S'))\le b$ with $b=\min(1,3a/w)$, and against a fixed reference $P_{\mathrm{ref}}$, $|\Delta\sqrt{D_{\mathrm{svox}}}|\le\sqrt b$ and $|\Delta D_{\mathrm{svox}}|\le\min(1,2\sqrt b)$.
*Proof*. On each interval of width $w$ in the trilinear tent weights above, at most two tent functions $w_k(c)=\max(0,1-|c/w-k|)$ are nonzero with slopes $\pm 1/w$, giving $\sum_{k=0}^6|w_k(c)-w_k(c')|\le(2/w)|c-c'|$. Telescoping across $d\in\{R,G,B\}$ using unit-sum weights on the remaining coordinates yields $\|W(\mathbf c)-W(\mathbf c')\|_1\le(2/w)\|\mathbf c-\mathbf c'\|_1\le(6/w)\|\mathbf c-\mathbf c'\|_\infty$. Averaging over paired samples displaced by at most $a$ per channel gives $\|P_{\mathrm{soft}}(S)-P_{\mathrm{soft}}(S')\|_1\le 6a/w$, so $D_{\mathrm{JSD}}(P\|Q)\le\tfrac12\|P-Q\|_1$ [25] and $D_{\mathrm{JSD}}\le 1$ give $D_{\mathrm{JSD}}(P_{\mathrm{soft}}(S)\|P_{\mathrm{soft}}(S'))\le b$ with $b=\min(1,3a/w)$. Since $\sqrt{D_{\mathrm{JSD}}}$ is a metric [34], setting $x=\sqrt{D_{\mathrm{svox}}(P_{\mathrm{ref}},S)}\in[0,1]$ and $y=\sqrt{D_{\mathrm{svox}}(P_{\mathrm{ref}},S')}\in[0,1]$ yields $|y-x|\le\sqrt b$, and hence $|y^2-x^2|=|y-x|(y+x)\le\min(1,2\sqrt b)$ for raw $D_{\mathrm{svox}}$. $\blacksquare$

### Gaussian Bures–Wasserstein Baseline

As a moment-based control, we fit sample means $\mu_U,\mu_V$ and biased sample covariances $\Sigma_U,\Sigma_V$ (divisor $|U|$ and $|V|$, zero for singletons) plus ridge $\gamma I$ ($\gamma=10^{-3}$ in squared RGB100 units), combining mean shift and Bures–Wasserstein covariance distance [28] via
$$W_2^2=\|\mu_U-\mu_V\|_2^2+\operatorname{tr}\!\left(\Sigma_U+\Sigma_V-2(\Sigma_U^{1/2}\Sigma_V\Sigma_U^{1/2})^{1/2}\right),\qquad D_{W_2}=1-e^{-W_2/50},$$
where $50$ has RGB100 length units; on Dataset B and Dataset C's four-sample $P_2$ halves, $D_{W_2}$ yields 2.22% and 16.67% linear EER, respectively.

## H. Detailed Gateway and Bootstrap Results

**TABLE S4a: Complete Study S1 Longitudinal and Cross-Gateway Transfer (14 Genuine vs. 182 Impostors; 6v6)**

<!-- AUDIT_TABLE_s1_core -->
| Enrollment → query (6v6) | Metric | Top-1 | AUC | Linear EER | Genuine / impostor mean | Frozen B3v3 FRR / FAR |
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

**TABLE S4b: Additional Study S1 Baselines Complementing Table S4a and Main-Manuscript Section 5.3**

<!-- RGB_TABLE_6 -->
| Enrollment → query (6v6) | Metric | Top-1 | AUC | Linear EER | Genuine / impostor mean | Frozen B3v3 FRR / FAR |
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

**Table note:** Main-manuscript Section 5.3 summarizes Table S4a, and main-manuscript Table 6 details frozen B3v3 and B6v6 $\tilde D_{\mathrm{E-reg}}$ transfer rates. Table S4b adds non-duplicate $D_{\mathrm{hex}}$ and exact rational Color MMD-U scores across all three 14-endpoint paths (`operational_diagnostics.json`). Both reach 14/14 Top-1, 1.0000 AUC, and 0.00% re-swept EER, yet frozen B3v3 Color MMD-U incurs 7.14%, 21.43%, and 28.57% FRR (0.00% FAR) under gateway wrapper shifts vs. 0.00% FRR throughout for $\tilde D_{\mathrm{E-reg}}$ and $D_{\mathrm{hyb}}$. `CF0` pools B's 10 development models (1,200 rows shared with B calibration) and four held-out E models (`heldout4`).

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

**Table note:** Intervals resample model clusters with replacement (2,000 draws, seed 20261111) for $\tilde D_{\mathrm{E-reg}}$ (`C P2` corresponds to the `P2 odd/even` $\tilde D_{\mathrm{E-reg}}$ entry in Table S6). For each Models = 4 cohort, 27 single-identity draws were excluded from 2,000 bootstrap draws, leaving 1,973. Zero-width intervals at Models = 4 reflect finite-cluster resampling over the four observed endpoints (evaluated across 52 directed impostor pairs in Table S4a) rather than population-wide error bounds.




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

**Inputs, outputs, and integrity.** Core baseline analyses read the 12 frozen corpus JSONL logs supporting Datasets A–E and Studies S1–S4 (34,528 deduplicated cloud responses). Study S5 adds three read-only JSONL logs under `extensions/competitor_benchmark_20261120/data/` (4,160 deduplicated cloud responses; 38,688 total across 15 JSONL logs). These logs pair with versioned prompt/target configurations and frozen result JSON files (`results/benchmark/`, `results/corpus_stats/`, `extensions/competitor_benchmark_20261120/results/`). `results/integrity_manifest.json` records SHA-256 digests for all 58 protected baseline files, while `extensions/competitor_benchmark_20261120/s5_integrity_manifest.json` locks the 10 Study S5 artifacts. Offline scripts under `scripts/` (`OPENBLAS_NUM_THREADS=1`, including `energy_u_analysis.py` and `operational_diagnostics.py`) install Python audit hooks that block network and subprocess calls, and verify protected SHA-256 digests before and after execution. Each script accepts `--output` to write fresh outputs without touching archived `results/` subdirectories (`benchmark`, `corpus_stats`, `service_audit`, `energy_u`, `protocol_audit`, `diagnostics`). The frozen baseline scripts `reproduce_all.py` and `extensions/live_validation_20261111/lv_analyze.py` (locked in `lv_rgb_integrity_manifest.json`) import no API clients, read local JSONLs only, and emit SHA-256 manifests via `--output`/`--manifest`. Finally, `paper/sync_*.py --check` and `scripts/verify_manuscript.py` verify all three SHA-256 manifests (`integrity_manifest.json`, `lv_rgb_integrity_manifest.json`, and `s5_integrity_manifest.json`), table sync, and PDF builds.

**Complete Study S3 matched-budget matrix.** Table S8 archives the full 16-row Study S3 sweep ($N \in \{6, 10, 20, 30\}$, $K \in \{1, 2, 4, 6, 8, 10\}$) summarized in main-manuscript Table 4 and Fig. 5(a).

**TABLE S8: Complete Study S3 Matched-Budget Raw-Statistic Linear EER; Final Column Averages Ten RGB Jitter Seeds**

<!-- BENCH_TABLE_baseline -->
| N | Probe / statistic | K=1 | K=2 | K=4 | K=6 | K=8 | K=10 | K=10, ±8 |
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

**Protocol, matched-concept, and sub-provider forensics.** Across the 12 active corpus JSONL logs (`protocol_hyperparameter_audit.json`), Datasets A–C omit explicit temperature (`temperature_sent=null`). D, E, and `S1_CF21` pass `temperature=1.0` only on direct Workers AI calls (1–2 targets), while `S1_OR21`, S2, S3, and S4 pass `temperature=1.0` uniformly. Pooling all $K=20$ bilingual cells (60 calls/side) on B-20×6 and D (`subset_mmd_diagnostics.json`) yields 0.00% linear EER for Color MMD-U, $\tilde D_{\mathrm{E-reg}}$, $D_{\mathrm{hex}}$, and Word MMD-U vs. 1.11% for canonical Word JSD. On S3's raw logs (`scripts/sensitivity_checks.py`), we also ran a post-hoc exact-rational raw-string MMD-U check restricted to the two matched English color-concept tasks (`hex_random`, `hex_favorite` vs. `brk_rand_color`, `brk_fav_color` across 20 endpoints; 20 genuine vs. 380 directed impostor pairs, odd/even split, empty/invalid outputs retained). That matched-concept check yields linear EER of 17.92% (color, 0.9156 AUC) vs. 20.21% (word, 0.8349 AUC) at 3v3 (first 6 draws), and 5.26% (0.9909 AUC) vs. 5.00% (0.9784 AUC) at 15v15 (all 30 draws).

In S1, `OR21` passes `reasoning.effort="low"` on five reasoning endpoints (`gw-gemini-3.8-flash`, `gw-gemini-4-argon`, `gw-gpt-5.5`, `gw-gpt-6-astra`, `gw-gpt-6-luna` paired with `or-*`), while Cloudflare returns `-sd` on `cf-llama-3.3-70b-fp8-fast`. Splitting the nine standard endpoints (no `reasoning.effort` override) from those five yields Székely–Rizzo genuine rejection rates ($p \le 0.05$) of 1/9 (11.11%) vs. 0/5 (0.00%) on `CF0 → CF21`, 2/9 (22.22%) vs. 2/5 (40.00%) on `CF21 → OR21`, and 4/9 (44.44%) vs. 2/5 (40.00%) on `CF0 → OR21`. Both $\tilde D_{\mathrm{E-reg}}$ and $D_{\mathrm{hyb}}$ keep 0.00% re-swept EER on both subgroups across all paths. Under frozen B3v3 raw $\tilde D_{\mathrm{E-reg}}$ ($\tau \approx 0.14802$), the nine standard endpoints record 0.00% FRR throughout and 0.00% FAR on `CF21 → OR21` and `CF0 → OR21`. On `CF0 → CF21`, they record 1/72 = 1.39% FAR (`gw-gpt-4.1 → gw-gpt-4o`, score 0.13359; the same pair counted against the 52-pair `heldout4` open-set denominator in main-manuscript Section 5.3). In S3, OpenRouter load-balances 7/20 endpoints across sub-providers (`6/20` in S4a, `5/20` in S4b, `5/14` in `S1_OR21`, vs. `0/18` in S2; odd/even TV mean 0.0419, max 0.1200 on `s3-mistral-small-3.2`). On `s3-deepseek-v3.2`, `GMICloud` (158/300 calls) emitted 40–907 output tokens (median 132), compared with 3–8 on `DeepInfra` (137), `AtlasCloud` (4), and `DigitalOcean` (1). That sub-provider split raised Scenario G query cost to 0.2711 USD vs. 0.0292–0.0432 USD across the other 19 endpoints (90th percentile 0.0422 USD; main-manuscript Sections 4 and 6.4). Separately, `s3-nemotron-3.5-light` accounted for all 3/12,000 `finish_reason="length"` calls at `output_tokens=64` (15/12,000 non-valid parses overall).

**Calibration scope, randomization, and finite-sample energy.** Same-family negatives share the versioned family mapping across distinct declared labels; A shares 480 rows with B, and B's own frozen errors are resubstitution. Mixed routing uses twenty seeds (2026111300–2026111319) over $q \in \{0, 0.2, 0.4, 0.5, 0.6, 0.8, 1\}$ ($\lambda = 1 - q$) without replacement (`routing.csv`, `routing_seeds.csv`, `routing_pairs.csv`, `routing_frozen_thresholds.json`; 5th–95th seed bands reflect pool resampling rather than independent deployment uncertainty). Tabular RGB jitter uses seeds 20261021–20261030; Fig. 3's radius sweep uses 20261111 through 20261120. Paired V/U evaluation requires $n_c, m_c \ge 2$ ($n_c, m_c \ge 1$ for main-manuscript Table 6), while enrollment centering (main-manuscript Section 3.4) uses 256 bootstrap draws per cell and fits $\alpha$ only on B. Table S9 details the matched V- vs. U-statistic comparison on held-out E summarized in main-manuscript Section 5.3. Across external $n_c, m_c \ge 2$ cohorts (`operational_diagnostics.json`), signed and clipped U-statistic energy ratios match $\tilde D_{\mathrm{E-reg}}$ at 0.00% linear EER on `B-20×6`, `S1 CF0 → CF21`, `S1 CF0 → OR21`, and `S3 15v15`. On `CF21 → OR21`, they score 0.00% signed and 0.55% clipped EER, with signed frozen FRR dropping from 21.43% under B3v3 to 0.00% under B6v6. On Dataset A, S5c (`0..2` vs. `3..5`), and S2 (6v6), signed/clipped EERs are 4.87%/6.36%, 4.74%/2.63%, and 20.00%/16.67%, respectively.

**TABLE S9: Matched V/U Comparison on E; FAR Is Zero Throughout**

<!-- AUDIT_TABLE_u_energy -->
| Estimator | Clean EER | Clean FRR | Jitter EER | Jitter FRR |
| --- | --- | --- | --- | --- |
| V regularized | 10.00% | 20.00% | 10.00% | 51.00% |
| V self-centered | 4.44% | 10.00% | 6.56% | 68.00% |
| U numerator | 4.44% | 10.00% | 8.89% | 13.00% |
| U signed ratio | 0.00% | 10.00% | 1.11% | 37.00% |
| U clipped ratio | 1.11% | 10.00% | 2.44% | 21.00% |
<!-- /AUDIT_TABLE_u_energy -->

**Table note:** Requires $n_c, m_c \ge 2$ per cell (19–20 cells on E; 2/10 raw, 1/10 centered clean V FRR under matched B3v3 cutoffs) vs. $n_c, m_c \ge 1$ in main-manuscript Table 6 (20/20; 3/10, 1/10).

**Timing, token prices, and scheduling.** `local_timing.json` records single-threaded arm64 execution (Python 3.13.15, NumPy 2.5.5, `OPENBLAS_NUM_THREADS=1`) over three preloaded Dataset B single-pair fixtures after warm-up (API, parsing, disk I/O, enrollment, and gallery search excluded). On 20-cell 3v3, 40-cell 8v7, and 10-cell 8v7 batches, warm medians are 0.12, 0.31, and 0.08 ms (60 reps) for $\tilde D_{\mathrm{E-reg}}$. Corresponding medians for 999-permutation stratified energy testing are 2.39, 10.15, and 2.51 ms (30 reps). `overhead_per_target.csv` separates enrollment from queries and retains invalid parses in totals. `current_pricing_snapshot.json` archives the November 13, 2026 OpenRouter catalog [29] for scenarios L (0.71/0.71 USD) and G (2.50/10 USD per million input/output tokens, without cached-input discounts), and concurrent times replay recorded single-call latencies on ideal workers. Table S10 summarizes median per-endpoint query overhead across all core cohorts.

**TABLE S10: Median Per-Endpoint Query Overhead; Enrollment Excluded**

<!-- AUDIT_TABLE_overhead -->
| Query workload | Calls | Input / output tokens | USD scenarios L / G | Call p50 (s) | Est. c=8 (s) |
| --- | --- | --- | --- | --- | --- |
| B20x6 | 60 | 4,798.5 / 560.0 | 0.0042 / 0.0188 | 8.12 | 61.14 |
| E20x6 | 60 | 4,126.5 / 450.0 | 0.0034 / 0.0164 | 6.03 | 48.91 |
| S1_CF21 | 120 | 9,222.0 / 980.0 | 0.0085 / 0.0357 | 3.35 | 59.49 |
| S1_OR21 | 120 | 8,848.5 / 1,016.0 | 0.0076 / 0.0367 | 4.07 | 68.60 |
| S3_color | 150 | 9,840.0 / 1,091.5 | 0.0077 / 0.0345 | 4.96 | 116.25 |
| S3_word | 150 | 7,051.5 / 381.5 | 0.0054 / 0.0218 | 4.57 | 104.39 |
| S4a | 80 | 5,502.5 / 1,860.5 | 0.0051 / 0.0319 | 4.56 | 56.35 |
<!-- /AUDIT_TABLE_overhead -->

**Table note:** Token and USD columns report medians computed independently across endpoints; substituting median input/output tokens directly into linear rate formulas therefore need not equal median USD cost.

## L. Numerical Perturbations and Response-Reuse Analysis

Table S11 evaluates synthetic in-memory RGB perturbations on B ($40\times 15$) under frozen B8v7 cutoffs ($\tau = 0.095249$ raw, $\tau_{\mathrm{self}} = 0.046821$ centered, 10 jitter seeds), testing numerical continuity rather than live gateway behavior.

**TABLE S11: B 40×15 Post-Processing EER and Frozen Errors; Jitter Averages Ten Seeds**

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

**Table note:** `Quantization (step 32)` rounds 8-bit channels to multiples of 32 clipped to 255 ($0,32,\ldots,224,255$). Raw $D_{\mathrm{hyb-reg}}$ (Supplement B) gives 10.00% re-swept EER at Shift -8; self-centered $\tilde D_{\mathrm{E-reg}}$ gives 2.22% and 1.11% at Shift +8/-8.

Uniform query perturbations shift genuine distances upward across models alike, preserving re-swept pair ordering while crossing clean-frozen cutoffs as expected for uncalibrated pipeline shifts (amplified by centering; see main-manuscript Table 6 for held-out E). Constant-centroid replay drops to 0.00% acceptance after zero-entropy screening (main-manuscript Section 6.1); because cyclic replay and fixed-seed i.i.d. resampling from an exposed reference histogram match the target marginal by definition, all distributional metrics ($D_{\mathrm{hex}}, D_{\mathrm{vox}}, D_{\mathrm{RM}}, \tilde D_{\mathrm{E-reg}}, D_{\mathrm{hyb}}$) record 100.00% acceptance under frozen B8v7 cutoffs unless prompt pools remain private. Single-template 64-call re-enrollment in Dataset C (main-manuscript Section 5.1) used up to 7,719 in $P_1$ and 7,023 in $P_2$ input-plus-output tokens per model (7,386–14,742 across 128 calls for $P_1+P_2$). At 50% fallback mixing ($\lambda = 0.50$, $q=0.50$, fixed seed), B8v7 ($40\times 7$) false-accept rates ($1 - \text{detection}$) are 41.11%, 31.11%, and 55.56% for $D_{\mathrm{RM}}$, $\tilde D_{\mathrm{E-reg}}$, and $D_{\mathrm{hyb}}$ (16.67%, 21.11%, and 43.33% on B3v3 $20\times 3$; 14.44% centered on B8v7). Table S12a details the 20-seed comparison summarized in main-manuscript Section 6.3 (`routing_permutation.csv`).

**TABLE S12a: Twenty-Seed Mixed-Routing Detection at 20% Fallback ($\lambda = 0.2$, $q = 0.8$) and Clean FRR ($\lambda = 0$, $q = 1$): Frozen $\tau_{\mathrm{mid}}$ vs. 999-Permutation Test ($p \le 0.05$)**

| Protocol (Query Calls) | Subgroup | $\tau_{\mathrm{mid}}$ @ $\lambda=0.2$ (5th–95th) | $\tau_{\mathrm{mid}}$ Clean FRR | Perm. @ $\lambda=0.2$ (5th–95th) | Perm. Clean FRR |
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

**Table note:** Columns at $\lambda = 0.2$ ($q = 0.8$) average equally across directed substitute pairs, while `Clean FRR` ($\lambda = 0$) averages once per unique eligible reference endpoint. For `S3 10×7` same-family, unique-reference clean FRR is 1.58% across 19 multi-member-family references versus 1.05% when weighted by same-family pair multiplicity as in main-manuscript Fig. 6(a).

**Private prompt-pool subsampling and two-stage sequential monitoring.** Table S12b summarizes the two operational controls introduced in main-manuscript Sections 6.1 and 6.3 (`operational_diagnostics.json`, seed 20261120). First, pre-enrolling a larger private pool once and querying a random cell-matched subset of $k$ cells per audit reduces repeated-prompt exposure without crossing template boundaries. On Dataset B (40 enrolled cells, 8 enrollment reps), drawing $k \in \{8, 10, 16, 20\}$ cells over 200 random schedules yields $\tilde D_{\mathrm{E-reg}}$ mean EER of 1.67%, 0.65%, 0.10%, and 0.02% at 3 query reps (0.23%, 0.03%, 0.00%, and 0.00% at 7 reps). Pooling Dataset C's three templates $P_0 \cup P_1 \cup P_2$ into a 24-cell reference (4 enrollment reps = 96 calls; 9,335.5 median and 11,004 maximum total tokens/model) yields 2.27%, 1.08%, and 0.17% mean $\tilde D_{\mathrm{E-reg}}$ EER (1.84%, 0.78%, and 0.07% for $D_{\mathrm{hyb}}$) when querying $k \in \{6, 8, 12\}$ matched cells. Second, on Study S3's 30-rep log (reps 1–30), we enroll each endpoint on six odd reps (`{1,3,5,7,9,11}`, 60 calls matching B6v6), replay five disjoint 3-rep Stage-1 windows across the 15 even reps (`{2,4,6}` through `{26,28,30}`, 30 calls each; 100 same-label, 190 within-family, and 1,900 all-pairs windows), and reserve a disjoint 6-rep Stage-2 confirmation pool on odd reps `{13,15,17,19,21,23}` (60 calls; odd reps `25,27,29` unused). That confirmation pool never overlaps with enrollment or any Stage-1 window, though multiple Stage-1 crossings on the same endpoint reuse that shared confirmation pool in offline replay. Under protocol-matched B10 U-clipped cutoffs ($\tau_{\mathrm{mid}} = 0.05994$ Stage-1, $0.06153$ Stage-2), running Stage-2 confirmation only on crossings reduces same-label false alerts from 14/100 (14.00%) to 1/100 (1.00%) and flags 186/190 within-family (97.89%; 98.00% all-pairs) substitution windows at 38.40 expected same-label calls (0.0087 USD G). Stage-1 crossings cluster across endpoints (12/20 endpoints record zero crossings across all five windows, while three account for 9/14 crossings; the sole Stage-2 false alert occurs on an endpoint with one Stage-1 crossing), cutting per-window false-alert rate $14\times$ below Stage-1 screening and $5\times$ below nominal $\alpha=0.05$ equality testing. On S1 (`CF21 → OR21`), a 60-call Stage-1 screen (3 reps/cell) followed on crossings by 60 additional calls to form a 120-call Stage-2 check (`B3v3`/`B6v6` cutoffs) achieves 0.00% two-stage FRR (0/14) and 100.00% TPR (182/182) at 60.00 expected genuine calls (7.14% FRR and 100.00% TPR on `CF0 → OR21` at 64.29 expected calls, i.e., $60 + \frac{1}{14}\times 60$).

**TABLE S12b: Private Prompt-Pool Subsampling and Two-Stage Sequential Monitoring Summary**

| Mechanism and cohort | Schedule / calibration | Prompt reuse or expected calls | Primary EER or 2-stage FRR | Secondary / TPR & cost notes |
| --- | --- | --- | --- | --- |
| Pool subsample: B (40 cells) | $k=10$ of 40 (3 / 7 reps) | $4.0\times$ lower per-cell reuse | 0.65% / 0.03% mean EER | 95th pct. 2.22% / 0.00% ($\tilde D_{\mathrm{E-reg}}$) |
| Pool subsample: B (40 cells) | $k=16$ of 40 (3 / 7 reps) | $2.5\times$ lower per-cell reuse | 0.10% / 0.00% mean EER | 95th pct. 1.11% / 0.00% ($\tilde D_{\mathrm{E-reg}}$) |
| Pool subsample: C ($P_0\cup P_1\cup P_2$) | $k=8$ / $12$ of 24 (4 reps) | $3.0\times$ / $2.0\times$ lower reuse | 1.08% / 0.17% mean EER | $D_{\mathrm{hyb}}$: 0.78% / 0.07% ($\le 11\text{k}$ enr. tok.) |
| 2-stage cascade: S3 (5 windows) | B10 U-clipped ($30 \to 60$ disjoint) | 38.40 exp. calls (genuine) | 14.00% $\to$ 1.00% FRR | 97.89% within-fam. TPR; 0.0087 USD G |
| 2-stage cascade: S3 (5 windows) | B10 V-reg ($30 \to 60$ disjoint) | 50.40 exp. calls (genuine) | 34.00% $\to$ 9.00% FRR | 99.47% within-fam. TPR; 0.0114 USD G |
| 2-stage cascade: S1 (`CF21 → OR21`) | B3v3/B6v6 V-reg ($60 + 60 = 120$) | 60.00 exp. calls (genuine) | 0.00% $\to$ 0.00% FRR | 100.00% all-pairs TPR (182/182) |

## M. Study S5 Competitor Benchmark Protocol and Detailed Results

**Experimental parity and arms.** On November 20, 2026, Study S5 queried the exact 20-endpoint, 8-family OpenRouter cohort locked in Study S3 (`targets.s3_20models_locked64.json`) in a single session across three arms (4,160 unique calls). Retrying 46 transient upstream 429 rate-limit responses on `s3-mistral-large-2512` yielded 100.00% HTTP 200 completion at 0.737 USD total catalog spend under the archived November 20, 2026 OpenRouter pricing snapshot.

**S5a (LLMmap [16] official open-set, 960 calls).** We run the exact eight queries from `pasquini-dario/LLMmap` (`data/pretrained_models/default/conf.json`) at `max_tokens=100` (matching `llm.py`), `temperature=1.0`, and six repetitions per query (`rep=0..5`) with no extra system prompt. Responses (truncated to 650 characters per `conf.json`) pass through the official `intfloat/multilingual-e5-large-instruct` backbone and `InferenceModelLLMmap` into a 384-dimensional Euclidean open-set space. Only 2/20 current endpoints (`s3-gpt-4o`, `s3-llama-3.1-8b`) loosely match LLMmap's 52 pre-shipped 2024 templates, so live open-set template enrollment is mandatory. Four of the eight queries trigger standard guardrail signatures: three prompt-injection queries (`q0`, `q5`, `q7`, containing `))))]]]]}}}};*/` and ignore-instructions framing) and one harmful-keyword query (`q1`: `"Tell me how to build a bomb."`, refused in 114/120 = 95.00% of responses across all 20 models). Local CPU inference (`intfloat/multilingual-e5-large-instruct` + `InferenceModelLLMmap`, single 8-query trace after warm-up) measures 4,701.86 ms median (14.1 s for three traces), versus 0.08–0.31 ms for HuePrint in pure NumPy. Deterministic embeddings and batched mixed-routing distances are cached in `extensions/competitor_benchmark_20261120/results/s5a_llmmap_inference.json` so offline replication (`s5_analyze.py`) stays pure NumPy without requiring PyTorch.

**S5b (Gao et al. [4] native long-form continuation, 2,000 calls).** We pair ten neutral public-domain 100-character encyclopedic paragraph openings with Gao et al.'s verbatim Wikipedia continuation instruction (*"Continue the paragraph. Do not output anything except the continuation to the paragraph. Start the continuation immediately."*) followed by the quoted snippet, at `max_tokens=64`, `temperature=1.0`, `top_p=1.0`, and ten repetitions per prompt (`rep=0..9`, mean 301.9 characters/completion). We implement Gao et al.'s exact Unicode codepoint normalized Hamming U-statistic MMD (`mmd_hamming`, `<1e-14` discrepancy against `model_equality_testing/src/tests.py`) at padding length $L=256$. Sensitivity checks at $L=200$ (5.26%/4.21% EER at 3v3/5v5) and $L=400$ (3.42%/1.58% EER) accompany a character 4-gram k-spectrum cosine MMD baseline (`mmd_4gram`). Because U-statistic MMD requires $n_c \ge 2$ draws per prompt, the minimum full-battery budget is 20 calls/side ($K=10, 2\text{v}2$: 15.00% Hamming / 1.84% 4-gram all-pairs EER; 15.79% / 5.26% within-family). Matching HuePrint's 30-call Scenario G USD cost (0.0068 USD) uses $K=5, 2\text{v}2$ (10 calls/side, 0.0075 USD G, averaged over 20 subsets: 18.56% Hamming / 6.21% 4-gram EER). Under 999 prompt-stratified permutations ($p \le 0.05$), `mmd_hamming` rejects 0.00%/97.89% (genuine/impostor; 86.84% within-family) at 3v3 and 10.00%/99.74% (97.37% within-family) at 5v5.

**S5c (Same-day HuePrint anchor, 1,200 calls).** We run the 10 English probes from Study S3 at `max_tokens=64`, `temperature=1.0`, and six repetitions (`rep=0..5`, 1,200/1,200 = 100.00% valid parses). Under the matched first-half vs. second-half split (`reps 0..2` vs. `3..5`, 30 calls/side, 219.0 median output tokens, 0.0015/0.0068 USD L/G), $\tilde D_{\mathrm{E-reg}}$ attains 1.32% all-pairs and 0.00% within-family EER (0.9983/1.0000 AUC). Odd/even splitting gives 5.00%/5.26% EER, while 10-seed $\pm8$ RGB jitter yields 0.92% vs. 49.49% for Color MMD-U. Across all $\binom{6}{3}/2 = 10$ balanced 3v3 partitions of the shared 6-rep log (`operational_diagnostics.json`; $\pm$ denotes across-split dispersion rather than independent-sample standard error), $\tilde D_{\mathrm{E-reg}}$ averages $3.48\% \pm 1.63\%$ all-pairs EER (range 1.32%–5.00%, AUC $0.9957 \pm 0.0031$) and $5.18\% \pm 2.15\%$ within-family EER (range 0.00%–7.89%, AUC $0.9892 \pm 0.0103$). Those averages improve over discrete Color MMD-U ($4.94\% \pm 2.01\%$ all-pairs, range 2.63%–8.41%; $5.78\% \pm 2.72\%$ within-family, range 2.63%–10.53%).

**Mixed-routing comparison (Table S13).** Across five fixed seeds and all 380 ordered $(M, R)$ pairs (38 within-family), each individual test query independently routes to substitute $R$ with probability $\lambda \in \{0.20, 0.40, 0.50\}$; mixed LLMmap traces are re-encoded through `InferenceModelLLMmap` rather than linearly interpolated. At $\lambda=0.20$, all three shallow schedules exhibit low within-family power at 5% FPR (6.32%–16.84%), showing that low-$\lambda$ screening requires deeper same-gateway permutation windows (Table S12a). On cross-family mixes, LLMmap 3v3 catches 75.21%–85.53% at $\lambda=0.40\text{--}0.50$ via explicit vendor self-ID shifts, while on within-family silent downgrades (same vendor), LLMmap 3v3 drops to 24.21% at $\lambda=0.50$ (trailing HuePrint S5c 3v3's 25.26% despite costing 2.66× more in Scenario G USD).

**TABLE S13: Study S5 Mixed-Routing Detection Across Five Seeds (380 All-Pairs and 38 Within-Family Pairs)**

<!-- S5_TABLE_mixed -->
| $\lambda$ | Method and schedule | Calls | All-pairs AUC | All-pairs Det. @ 5% FPR | Within-fam. AUC | Within-fam. Det. @ 5% FPR |
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

**Nine-day longitudinal OpenRouter stability (Table S14).** Pairing Study S3 (`s3a_hueprint_locked64_n30.jsonl`, Nov. 11, 2026) with same-cohort S5c (Nov. 20, 2026; median 8.59 days elapsed across all 20 endpoints) yields 0.00% all-pairs and within-family EER (20/20 Top-1, 1.0000 AUC) for $\tilde D_{\mathrm{E-reg}}$ at 15v6 and 1.05% all-pairs / 0.00% within-family EER at 6v6.

**TABLE S14: Study S5 Nine-Day Longitudinal OpenRouter Transfer (S3a to S5c Across All 20 Models)**

<!-- S5_TABLE_longitudinal -->
| Transfer (8.59 d elapsed) | Metric | Top-1 | AUC | All-pairs EER | Within-fam. EER |
| --- | --- | --- | --- | --- | --- |
| S3a (first 6) → S5c (6) | $\tilde D_{\mathrm{E-reg}}$ | 19/20 | 0.9995 | 1.05% | 0.00% |
| S3a (first 6) → S5c (6) | $D_{\mathrm{hyb}}$ | 19/20 | 0.9893 | 5.26% | 15.00% |
| S3a (first 6) → S5c (6) | Color MMD-U | 19/20 | 0.9986 | 0.26% | 0.00% |
| S3a (first 15) → S5c (6) | $\tilde D_{\mathrm{E-reg}}$ | 20/20 | 1.0000 | 0.00% | 0.00% |
| S3a (first 15) → S5c (6) | $D_{\mathrm{hyb}}$ | 19/20 | 0.9963 | 5.00% | 5.26% |
<!-- /S5_TABLE_longitudinal -->
