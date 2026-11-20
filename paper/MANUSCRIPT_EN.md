# Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services

**Abstract**—Aggregated large language model (LLM) services expose declared identifiers while hiding backend configurations. We present HuePrint, a black-box framework that audits brokered endpoint consistency via structured color elicitation and geometric comparison without weights or token probabilities. Across 38,688 cloud responses (56 endpoints, 12 backends), HuePrint cuts 30-call/side equal error rates (EERs) over word baselines from 4.52–5.23 to 0.94–1.00 percent on development models and from 6.25–8.04 to 3.49–5.00 percent across 20 locked endpoints, reaching 0.00 percent at 60–150 calls/side. On those 20 endpoints, HuePrint averages 5.18 percent within-family EER across all ten balanced 30-call splits (0.00–7.89 percent), outperforming open-set LLMmap (10.53–34.39 percent, 1–3 traces) and cost-matched long-form kernels (11.09–19.47 percent); relative to LLMmap, it also avoids safety-triggering probes and runs over 15,000 times faster locally. Regularized RGB energy lowers shallow EER (5.36 vs. 10.71 percent exact-hex and 6.42 percent string MMD), while hybrid scoring cuts cross-provider EER from 16.67 to 5.93 percent. In offline replay, two-stage confirmation cuts false alerts from 14 to 1 across 100 same-label windows and flags 186/190 within-family substitutions under one cent expected cost.

**Index Terms**—Services computing, model-as-a-service, service-level monitoring, API brokerage, behavioral consistency, energy statistics.

---

<!-- USER_LITERAL:introduction -->
```latex
\section{Introduction}
\IEEEPARstart{A}{pplications} consuming aggregated large language model (LLM) services specify a target model identifier, while the cloud broker selects which backend instance fulfills each request~\cite{ref1,ref2}. Dynamic cascades, learned routers, and multi-provider brokers trade inference cost against latency and quality~\cite{ref1,ref2,ref3}. When a service-level agreement (SLA) commits to a pinned checkpoint or serving tier, consumers need black-box evidence that the fulfilled endpoint remains behaviorally consistent with its declared configuration. Latency, uptime, and billing logs cannot verify that property.

In this paper, we introduce HuePrint, a lightweight black-box consistency signal for brokered LLM endpoints. HuePrint elicits short hexadecimal (\texttt{\#RRGGBB}) or decimal RGB responses across multilingual prompts and compares their empirical distributions against an enrolled reference. No weights, activations, or log-probabilities are needed. Prior audits expose statistical discrepancies across commercial endpoints~\cite{ref4} and separate substitutions from benign serving nondeterminism~\cite{ref5,ref6}. Rather than replacing functional benchmarks or hardware attestation~\cite{ref5}, HuePrint acts as a low-cost canary whose threshold crossings trigger targeted SLA investigation.

HuePrint combines two complementary layers. First, \emph{structured multilingual color elicitation} pairs compact three-channel coordinates with semantic priors, expanding per-cell output support over single-word batteries~\cite{ref7} and cutting matched 30-call/side EER across 20 locked endpoints from 6.25\%--8.04\% to 3.49\%--5.00\% (0.00\% by 60--150 calls/side). Second, \emph{continuous regularized RGB energy and multi-scale hybrid comparison} improve sparse-sample efficiency, cross-host matching, and threshold stability beyond discrete color strings. On clean responses, regularized energy $\Dereg{}$ lowers shallow 56-endpoint EER over exact-hex divergence and string MMD (5.36\% vs.\ 10.71\% and 6.42\%), lowers 20-endpoint 30-call within-family EER across ten balanced splits (5.18\% vs.\ 5.78\% string MMD), and lifts family attribution from 42.00\% to 70.00\%. Multi-scale $\Dhyb{}$ cuts cross-provider EER across 12 backends from 16.67\% to 5.93\%. Across 21-day gateway transfers, score separation stays exact; budget-matched B6v6 rules flag 1/14 raw (0/14 centered) same-label pairs vs.\ 6/14 equality-test rejections, while all catch 182/182 swaps.

This paper makes three contributions to cloud LLM service assurance:
\begin{itemize}
    \item \textbf{End-to-end MaaS consistency protocol:} We formulate versioned audit contracts linking enrollment, private pool subsampling, frozen calibration, two-stage sequential verification, and reference refresh across 38,688 live cloud responses (Datasets A--E and Studies S1--S5).
    \item \textbf{Perturbation and finite-sample estimator analysis:} We prove discrete JSD support-escape lower bounds and Lipschitz stability for regularized energy ratios, and contrast finite-sample V-statistic bias against enrollment self-centering and zero-bootstrap U-statistic energy ratios.
    \item \textbf{Operational and competitor benchmark:} Across 56 endpoints and 12 pinned serving stacks, we benchmark HuePrint against open-set LLMmap and native long-form equality testing. We also evaluate within-family substitutions, fractional fallback routing, CSS/JSON canaries, and per-audit cost and latency.
\end{itemize}
```
<!-- /USER_LITERAL:introduction -->

## 2. Related Work and Service Model

<!-- USER_LITERAL:related_work_first_two -->
```latex
\subsection{Cloud Service Assurance and LLM Brokerage}
\textbf{SLA governance and brokered routing.} FrugalGPT~\cite{ref1} and RouteLLM~\cite{ref2} optimize provider-side cost--quality tradeoffs via model cascades and learned routers, while QoS-aware LLM brokering~\cite{ref3} pairs SLA-constrained routing with CUSUM drift tracking. In multi-tenant brokerage, however, consumers cannot observe provider dispatch tables and need low-budget active probing (canary testing) to verify pinned-checkpoint SLAs against silent tier substitutions.

\textbf{Service testing and sequential drift monitoring.} Services computing research addresses cloud API reliability from complementary layers, including LLM-guided REST API fuzzing (RESTLess~\cite{ref8}), multi-modal microservice anomaly detection (UAC-AD~\cite{ref9}), and concept-drift-triggered edge rejuvenation~\cite{ref10}. White-box telemetry and fuzzers inspect host metrics or schema faults; HuePrint instead audits black-box completion distributions to separate benign drift from backend changes.
```
<!-- /USER_LITERAL:related_work_first_two -->

**Model and API auditing.** Provider-side watermarks, instructional backdoors, and IP ownership fingerprints [11]–[13] require owner intervention or target model-theft disputes rather than live endpoint monitoring. Passive attribution [14], [15] needs long outputs. Active neural fingerprinters (LLMmap [16], TRAP [17]) probe endpoints in roughly eight multi-token queries. LLMmap supports closed-set classification and open-set contrastive template matching via a 560M-parameter embedding backbone, yet requires enrolling new checkpoints and relies on prompt-injection and safety-boundary queries. Gao et al. [4] test long-form distribution equality via Hamming and k-spectrum string kernels; Cai et al. [5] analyze black-box and logprob substitution tests alongside adaptive routing and hardware enclaves; Zhu et al. [6] require white-box reference token probabilities. Biased random priors [18]–[21] motivate short probes despite shared-component correlations [22], [23]. Bruckner [7] applies discrete JSD across 40 single-word prompts (7.3% EER over 165 models). Table 1 positions HuePrint against these black-box auditing lines.

**TABLE 1: Comparison of Black-Box LLM Auditing Methods**

| Method | Access / ref. | Probe type | Query budget | Drift / perturb. | Guardrail / CPU |
| --- | --- | --- | --- | --- | --- |
| Gao et al. [4] | Text only; paired | Long continuations | 30–50 calls (64 tok.) | Strict ($p\le0.05$) | Benign; ~0.2 ms |
| Cai et al. [5] | Text / logprobs | Task prompts | Multi-query batch | Hypothesis test | Benign; light CPU |
| Zhu et al. [6] | White-box ref. probs | General prompts | Rank-uniform batch | Strict equality | Benign; ref. logits |
| Bruckner [7] | Text only; enrolled | 40 word prompts | 30–150 calls (1–2 tok.) | Discrete JSD | Directive; <1 ms |
| LLMmap [16] | Text; open-set templ. | 8 inj./safety/ID | 8–24 calls (100 tok.) | Contr. Euclidean | 4/8 flagged; 4.7 s E5 |
| TRAP [17] | Text; opt. suffix | Adversarial suffix | Targeted queries | Suffix match | Adv. str.; high opt. |
| **HuePrint** | **Text only; enrolled** | **RGB/hex & CSS/JSON** | **30–150 calls (~7 tok.)** | **Lipschitz + perm.** | **0% flag (S4a); 0.12 ms** |

<!-- USER_LITERAL:service_model -->
```latex
\subsection{Service Aggregation Architecture and Audit Contract}
\textbf{Roles and observables.} A consumer-side monitor enrolls a declared checkpoint $M^*$ via a trusted reference endpoint $E_{\mathrm{ref}}(M^*)$ and audits a brokered endpoint $E$ over $k$ task--language cells with $n_B$ completions per cell ($n=|U|, m=|V|$ valid parses; Fig.~1). Gateways such as Cloudflare AI Gateway and OpenRouter provide observable routing paths under standard chat-completion access, without model weights, hidden states, log-probabilities, or server-side seed control.

\textbf{Audit contract and deployment confounders.} An audit contract binds the reference profile, private prompt pool, sampling budget, parser, and frozen threshold version to a pinned-checkpoint SLA commitment. It does not target a declared complexity-cascaded router~\cite{ref1,ref2} whose lightweight branch legally serves short prompts. Checkpoint identity and numerical precision represent distinct behavioral properties alongside QoS telemetry rather than cryptographic weight proofs~\cite{ref5}. Two gateway mechanisms require explicit handling: response or semantic caching collapses stochastic draws at $T=1.0$ (screened via zero entropy and sub-median latency), and broker-injected system prompts shift color priors unless enrollment shares the gateway wrapper.

\textbf{Service-change scenarios and lifecycle.} We evaluate four operational regimes: (1) full checkpoint substitution behind a fixed model identifier; (2) cross-host serving and low-bit precision execution under an unchanged label, where cross-host checkpoint matching favors invariance across serving precisions; (3) probabilistic request-level fallback mixing declared and substitute backends; and (4) response reuse via lookup or histogram resampling. Scores below a frozen threshold $\tau$ yield \emph{accept}. Crossings trigger two-stage verification before \emph{investigate}, and authorized updates initiate reference refresh.
```
<!-- /USER_LITERAL:service_model -->

![Consumer-side audit lifecycle for a brokered LLM service. Enrollment and protocol-matched probes feed a frozen consistency decision; configuration changes require investigation and reference refresh.](../figs/fig1_service_audit.pdf)

## 3. Methodology and Perturbation Analysis

### 3.1 Probes, Parsing, and RGB Coordinates

The battery crosses 10 tasks with four languages (en, zh, ru, ar) for 40 task-language cells requesting random, favorite, warm, nature, ocean, calm, and night colors in hex (`#RRGGBB`) and RGB syntax (Fig. 2; e.g., *"Pick a random color. Reply with only its #RRGGBB hex code."*). Study S4 embeds color choices inside 1-line CSS custom properties (e.g., `--brand-primary`) and 1-field JSON design tokens; Supplements C–F give complete inventories and verbatim prompts. After stripping reasoning fields and inline tags, the parser extracts the first valid `#RRGGBB` code or validated $0\text{--}255$ RGB triplet and marks failures invalid. Valid parses retain canonical uppercase `#RRGGBB`, coordinates, syntax, and a strict-only-color flag.

For an sRGB code $\mathbf c\in\Omega=\{0,\ldots,255\}^3$ [24], let $\mathbf x=T(\mathbf c)=100\mathbf c/255\in\Omega_{\mathrm{RGB}}=[0,100]^3$; clipped perturbations $\mathbf c'=\operatorname{clip}_{[0,255]^3}(\mathbf c+\boldsymbol\eta)$ with $\|\boldsymbol\eta\|_\infty\le a$ satisfy $\|T(\mathbf c')-T(\mathbf c)\|_2\le 100\sqrt3 a/255$. RGB100 linearly rescales channels without gamma inversion or Lab conversion and is used for all continuous scores, while hard voxels use raw channel units. Supplement A analyzes injective and Lipschitz color charts, and Supplement B ablates fixed-weight regularization.

![Five deterministically selected family representatives on the random-color probe. Marker area denotes output frequency and fill denotes actual RGB; the two projections show (R, G) and (B, G). Word probabilities use the matched endpoints and random-color word probe, sorted by decreasing total probability.](../figs/fig2_rgb_geometry_vs_words.pdf)

### 3.2 Discrete JSD and Support Escape

With $M=(P+Q)/2$, base-2 JSD [25] is
$$D_{\mathrm{JSD}}(P\|Q)=\tfrac12\sum_xP(x)\log_2\frac{P(x)}{M(x)}+\tfrac12\sum_xQ(x)\log_2\frac{Q(x)}{M(x)},$$
omitting zero-mass terms; it satisfies $0\le D_{\mathrm{JSD}}(P\|Q)\le 1$, equaling $1$ iff $\operatorname{supp}(P)\cap\operatorname{supp}(Q)=\emptyset$. $D_{\mathrm{hex}}$ uses exact RGB codes ($256^3$ categories), while $D_{\mathrm{vox}}$ bins channels by $(\lfloor R/32\rfloor,\lfloor G/32\rfloor,\lfloor B/32\rfloor)$ ($8^3$ categories).

**Proposition 1 (Support-escape lower bound).** *Fix a reference empirical distribution $P_{\mathrm{ref}}$ with support size $r$, and let $Q^{\mathrm{jitter}}$ draw source colors $\mathbf c\sim P_{\mathrm{src}}$ perturbed by independent uniform integer noise on $\{-a,\ldots,a\}^3$ ($a\ge1$) under the clipped transformation above. For $n$ i.i.d. draws $\hat Q_n^{\mathrm{jitter}}\sim Q^{\mathrm{jitter}}$ with support-escape probability $Q^{\mathrm{jitter}}(\Omega\setminus\operatorname{supp}(P_{\mathrm{ref}}))\ge t\in[0,1]$,*
$$\mathbb E[D_{\mathrm{hex}}(P_{\mathrm{ref}},\hat Q_n^{\mathrm{jitter}})]\ge D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})\ge\psi(t),$$
$$\psi(t)=\tfrac12\log_2\frac2{2-t}+\tfrac{1-t}{2}\log_2\frac{2(1-t)}{2-t}+\tfrac t2\ge\tfrac t2,$$
*where $\psi$ is strictly increasing with $\psi(1)=1$ by continuity, and the population bound is tight. When $\operatorname{supp}(P_{\mathrm{src}})\subseteq\{a,\ldots,255-a\}^3$, one may take $t=\max(0,1-r/(2a+1)^3)$.*

<!-- USER_LITERAL:support_escape -->
```latex
Conditioning on observed query colors per cell and adding one random clipped shift per draw, Fig.~3(a) evaluates Eq.~(1) via the empirical query histogram's escape probability. Proposition~1 models coordinate post-processing or sparse-cell non-overlap: genuine $D_{\mathrm{hex}}$ scores saturate toward $1$ when nearby RGB codes miss the enrolled support, while empirical EER depends jointly on impostors (Fig.~3(c); proofs in Supplement~G).
```
<!-- /USER_LITERAL:support_escape -->

### 3.3 Regularized RGB Energy and Hybrid Composite

For nonempty RGB100 clouds $U,V$, let $n=|U|$, $m=|V|$, and
$$d_{UV}=\frac{\sum_{i,j}\|u_i-v_j\|_2}{nm},\qquad d_{UU}=\frac{\sum_{i,i'}\|u_i-u_{i'}\|_2}{n^2},$$
with $d_{VV}$ defined analogously, including diagonals. The V-statistic squared energy is $\widehat{\mathcal E}_V^2=2d_{UV}-d_{UU}-d_{VV}$. For distributions on $\mathbb R^3$ with finite first moments, population squared energy satisfies $\mathcal E^2(\mu,\nu)\ge 0$ with equality iff $\mu=\nu$ [26], [27]; applied to empirical measures, $0\le\widehat{\mathcal E}_V^2\le 2d_{UV}$. We therefore define
$$\bar D_{\mathrm E}=\frac{\widehat{\mathcal E}_V^2}{2d_{UV}},\qquad\tilde D_{\mathrm{E-reg}}=\frac{\widehat{\mathcal E}_V^2}{2d_{UV}+2\delta_0},$$
where $\delta_0=15$ RGB100 length units in Eq. (2) and $\bar D_{\mathrm E}=0$ at $d_{UV}=0$. Floating-point evaluation clips $[\widehat{\mathcal E}_V^2]_+=\max(0,\widehat{\mathcal E}_V^2)$ to $[0,2d_{UV}]$ and sets scores to zero when $d_{UV}<10^{-12}$. For constant clouds separated by $\epsilon>0$ ($d_{UU}=d_{VV}=0, d_{UV}=\epsilon$), $\bar D_{\mathrm E}$ jumps from $0$ at $\epsilon=0$ to $1$; by contrast, $\tilde D_{\mathrm{E-reg}}=\epsilon/(\epsilon+\delta_0)\le\epsilon/\delta_0$ varies smoothly.

**Proposition 2 (Lipschitz stability of regularized energy ratios).** *For nonempty $U,V\subset\mathbb R^3$, $\delta_0>0$, $d=d_{UV}$, and within-cloud mean distance average $h$ computed with diagonals ($\tilde D_{\mathrm{E-reg}}$) or without diagonals ($|U|,|V|\ge 2$, Section 3.4), let $F(d,h)=(d-h)/(d+\delta_0)$. Moving each point of $V$ by at most $\epsilon$ in Euclidean norm (in arbitrary directions) changes $F(d,h)$ and $[F(d,h)]_+$ by at most $2\epsilon/\delta_0$. Moving every point of $U$ and $V$ by at most $\epsilon$ changes them by at most $4\epsilon/\delta_0$.*

<!-- USER_LITERAL:energy_corollary -->
```latex
For clipped ratios in $[0,1)$, channel shift $a$ bounds one-sided change by $\min\{1, 200\sqrt{3}a/(255\delta_0)\}$ ($0.0906$ at $a=1$, $0.7245$ at $a=8$ for $\delta_0=15$) and remains continuous as $d_{UV}\to 0$. Proposition~2 permits arbitrary worst-case per-point directions, whereas uncoordinated uniform jitter in Fig.~3(b) stays far below this envelope.
```
<!-- /USER_LITERAL:energy_corollary -->

Alternative smooth-histogram ($D_{\mathrm{svox}}, D_{\mathrm{RM}}$, Supplement G Lemma 1), regularized-hybrid ($D_{\mathrm{hyb-reg}}$), and Gaussian Bures–Wasserstein [28] controls underperform $\tilde D_{\mathrm{E-reg}}$ on shallow or multimodal clouds (Supplements B and G).

![Ten fixed jitter seeds per radius on cohorts B and E. (a) Exact hex JSD and its clipping-aware conditional expected lower bound (Proposition 1). (b) Empirical regularized-energy score change vs. Proposition 2's Lipschitz upper bound. (c) Re-swept linear EER for exact hex vs. regularized energy; inset shows $\delta_0$ sensitivity.](../figs/fig3_stability_bounds.pdf)

**Hybrid composite and decision rules.** Across heterogeneous serving hosts (Study S2), discrete formatting habits complement continuous RGB coordinates. The auxiliary term $D_{\mathrm{side}}$ averages JSD over visible syntax (hex letter case, `#` prefix, or RGB comma spacing, including all-digit `numeric_only` hex codes covering $5.96\%$ of RGB), available first reasoning words, and log-binned reasoning lengths (`usage.reasoning_tokens` before visible character counts). Because $D_{\mathrm{side}}$ inspects syntax and envelope metadata rather than colors alone, Supplement B ablates content-only and color-only variants across cohorts. The fixed hybrid composite is
$$D_{\mathrm{hyb}}=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}+0.25\bar D_{\mathrm E}+0.15D_{\mathrm{side}}.$$
In Eq. (3), scores average shared eligible cells and accept at $S\le\tau$. Development genuine and impostor scores $G,I$ define $\tau_{\mathrm{mid}}=(\max G+\min I)/2$ and $\tau_{\mathrm{u0}}=\operatorname{nextafter}(\min I,-\infty)$ (zero FAR holds on development negatives). AUC gives ties half weight, linear EER interpolates adjacent ROC points under re-swept thresholds, and frozen FAR/FRR evaluate deployment cutoffs.

### 3.4 Enrollment Calibration and Finite-Sample Energy Estimators

**Self-dispersion centering and equality testing.** For each reference and cell, we bootstrap two enrollment-only clouds matching reference and planned query sizes across 256 fixed-seed draws. Averaging across eligible cells yields $\mu_{\mathrm{self}}$ without query data or test labels, defining $\Delta_D=D-\alpha\mu_{\mathrm{self}}$. Under IID enrollment sampling of size $n$, resampling $\hat P_n$ collides with probability $1/n$, scaling expected empirical within-sample distance (and the null bootstrap's unnormalized V-numerator) by $(n-1)/n$. Normalized $\tilde D_{\mathrm{E-reg}}$ ratios ($\overline{\mu}_{\mathrm{self}}/\overline{G}=0.732$ on B3v3, $0.598$ on E) reflect ratio normalization rather than $(n-1)/n$. We compare raw scores, $\alpha=1$, and B-only leave-one-model-out selection over $\{0,0.25,0.5,1,1.5,2\}$ (ties break toward $\alpha=1$). Protocol-specific B splits fit frozen thresholds: B3v3 (20 cells; used on E), B6v6 (20 cells; matched S1 check), and B8v7 (40 cells). Adapting the two-sample energy test [27] to stratified cells, we average $nm\widehat{\mathcal E}_V^2/(n+m)$ across cells over 999 within-cell label permutations with $p=(1+\#\{T_b\ge T_{\mathrm{obs}}\})/1000$ at $p\le0.05$.

**Finite-sample V- vs. U-statistic energy.** For independent IID samples of sizes $n,m$ ($a_P=\mathbb E\|X-X'\|$, $a_Q=\mathbb E\|Y-Y'\|$), the nonnegative V numerator satisfies $\mathbb E[\widehat{\mathcal E}_V^2]=\mathcal E^2(P,Q)+a_P/n+a_Q/m$. We retain V-statistic $\tilde D_{\mathrm{E-reg}}$ as the baseline score across all 10 suites because it remains defined on single-response cells ($n_c=1$) in sparse shallow slices. When protocols enforce $n,m\ge2$ valid parses per cell, the U numerator
$$\widehat{\mathcal E}_U^2=2d_{UV}-\frac{n}{n-1}d_{UU}-\frac{m}{m-1}d_{VV}$$
lies in $[-2d_{UV},2d_{UV}]$, may be negative, and is unbiased for $\mathcal E^2(P,Q)$ under independent IID sampling. Supplement K Table S9 compares $\tilde D_{\mathrm{E-reg}}$ (*V regularized*) and centered $\tilde D_{\mathrm{E-reg}}$ (*V self-centered*) against three zero-bootstrap U-statistic forms: $\widehat{\mathcal E}_U^2$ (*U numerator*), $\widehat{\mathcal E}_U^2/(2d_{UV}+2\delta_0)$ (*U signed ratio*), and $[\widehat{\mathcal E}_U^2]_+/(2d_{UV}+2\delta_0)$ (*U clipped ratio*, strictly in $[0,1)$ since $\delta_0>0$, so $\min\{1,\cdot\}$ is inactive). Neither random-denominator normalization nor clipping preserves unbiasedness; Proposition 2 gives both U ratios $2\epsilon/\delta_0$ one-sided and $4\epsilon/\delta_0$ two-sided bounds.

<!-- USER_LITERAL:u_final -->
```latex
All U-statistic variants and matched V-statistic controls are evaluated over identical cells containing at least two valid responses per side.
```
<!-- /USER_LITERAL:u_final -->

### 3.5 Completion Baselines and Competitor Protocols

Adapting Gao et al.'s one-hot MMD and $L_1$ tests [4] to raw short strings preserves whitespace, case, and invalid outputs (empirical TV $= \tfrac12 L_1$). For $n,m\ge2$ and $k(s,t)=\mathbf1[s=t]$,
$$\widehat{\mathrm{MMD}}_u^2=\frac{\sum_{i\ne i'}k(x_i,x_{i'})}{n(n-1)}+\frac{\sum_{j\ne j'}k(y_j,y_{j'})}{m(m-1)}-\frac{2\sum_{i,j}k(x_i,y_j)}{nm},$$
averaged across cells (exact rational MMD-U, 999 permutations); invalid parses still consume call budgets. Study S3 tests $N\in\{6,10,20,30\}$ ($n=m=N/2$) across up to 40 $K$-cell subsets ($K=1,\ldots,10$), with ten fixed RGB-jitter seeds.

Study S5 evaluates two native competitor protocols on the 20 locked OpenRouter models (Supplement M). **Open-set LLMmap** [16] runs its verbatim eight queries (`max_tokens=100`) through the official E5-large backbone and `InferenceModelLLMmap` to produce 384-d Euclidean templates. **Native long-form Model Equality Testing** [4] uses 10 neutral Wikipedia continuation prompts (`max_tokens=64`, $T=1.0$) scored with official Unicode `mmd_hamming` ($<10^{-14}$ discrepancy) and a character 4-gram cosine MMD baseline.

---

## 4. Experimental Design and Dataset Architecture

Five baseline datasets (A–E, Oct. 2026; 11,888 unique calls) and five online studies (S1–S5, Nov. 2026; 26,800 calls) yield **38,688** unique cloud responses (Table 2). All analyses run offline in pure NumPy over 15 read-only JSONL logs protected by deduplication rules, fixed seeds, and SHA-256 input manifests.

**TABLE 2: Cloud Response Datasets**

| Suite / Dataset | Models / Endpoints | Probe Grid (Cells $\times$ Reps) | Unique Calls | Valid Parsed (Rate) | Primary Evaluation Objective |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Dataset A** (Census) | 56 (11 families) | $8 \times 6$ (4 tasks $\times$ `en/zh`) | 2,688 | 2,611 (97.14%) | Broad census, family/sublineage EER, side-channel check |
| **Dataset B** (Dev Scaling) | 10 dev models | $40 \times 15$ (10 tasks $\times$ 4 langs) | 5,520 | 5,932/6,000 (98.87%) | $(n,k)$ budget grid, service-change tests, threshold calibration |
| **Dataset C** (Paraphrase) | 10 dev models | $16 \times 8$ ($P_1, P_2$ rewordings) | 1,280 | 1,262 (98.59%) | Within-pool verification vs. $P_0 \to P_1/P_2$ template shift |
| **Dataset D** (Word Baseline) | 10 dev models | $20 \times 6$ (10 word tasks $\times$ `en/zh`) | 1,200 | 1,196 (99.67%) | Call-parity word baseline vs. `B-20x6` |
| **Dataset E** (Held-Out) | 10 non-B models | $20 \times 6$ (10 color tasks $\times$ `en/zh`) | 1,200 | 1,187 (98.92%) | `+6.74h` `A->E` check, frozen `B->E` transfer, OOS jitter |
| **Study S1** (`T+21.3d` & GW) | 14 $\times$ 2 gateways | $20 \times 6$ (`CF` & `OR` gateways) | 3,360 | 3,338 (99.35%) | 21.32-day drift & `CF <-> OR` cross-gateway transfer |
| **Study S2** (Multi-Provider) | 6 weights $\times$ 3 hosts | $20 \times 6$ (12 pinned backends) | 2,160 | 2,147 (99.40%) | Cross-host matching (`int4`/`fp4`/`fp8`/`bf16`/LPU) |
| **Study S3** (Locked Parity) | 20 (8 families) | $10 \times 30 \times 2$ (completion cap 64) | 12,000 | 11,985 (99.88%) | Matched 15v15 parity benchmark against Bruckner with a 64-token cap |
| **Study S4** (Structured Canaries) | 20 (8 families) | `S4a` $16\times 10$ + `S4b` $16\times 6$ | 5,120 | 5,087 (99.36%) | CSS/JSON canary parsing and gateway regex pass rates |
| **Study S5** (Competitors) | 20 (8 families) | `S5a` $8\times 6$, `S5b` $10\times 10$, `S5c` $10\times 6$ | 4,160 | 4,160 HTTP 200 (100%) | Head-to-head LLMmap [16], Gao [4], & same-day HuePrint |

**Table note:** B combines 5,520 unique calls with 480 A rows (6,000). Three of 12,000 S3 responses reached the length limit (two color, one word; one valid). S5c parses 1,200/1,200 (100.00%) valid colors; S5a and S5b evaluate free-form text completions directly.

Requests disable optional thinking where supported and lock completion caps at 64 tokens in S2, S3, S5b, and S5c (100 in S5a per LLMmap; 128 in S4; 16–256 across A–E). Live OpenRouter studies (`S1_OR21`, S2–S5) pass `temperature=1.0` uniformly. Earlier Cloudflare Gateway logs (A–C and gateway targets in D, E, `S1_CF21`) relied on provider temperature defaults, and `S1_OR21` passed `reasoning.effort="low"` on five reasoning models; subgroup checks on the nine unmodified endpoints in Supplement K show 0.00% EER for $\tilde D_{\mathrm{E-reg}}$ and $D_{\mathrm{hyb}}$ versus 22.22%–44.44% permutation false rejections, indicating that score-based color auditing tolerates minor wrapper parameter drift. Study S2 pins backends (`0/18` mixed), while OpenRouter load-balances 5–7/20 endpoints in S1/S3/S4 (S3 odd/even sub-provider TV mean 0.0419). On S3 `s3-deepseek-v3.2`, sub-provider `GMICloud` ignored thinking suppression (up to 907 billed tokens); parsing strips reasoning traces while cost accounting retains all billed tokens.

---

## 5. Empirical Evaluation: Baseline and Live External-Validity Studies

### 5.1 Census, Budget Scaling, and Paraphrase Shift (Datasets A–C)

**56-endpoint census (Dataset A).** Across 56 endpoints in 11 families (8 cells $\times$ 6 repetitions, 3v3 split, $\ge 2$ valid responses/half), we test 56 genuine pairs against 3,080 all-pairs, 2,958 cross-sublineage, and 2,476 cross-vendor-family impostors, plus leave-one-out 1-NN family attribution over 50 multi-member-family models (Table 3). On this shallow grid, continuous RGB energy leads binary verification ($\bar D_{\mathrm E}$ 4.77%, $\tilde D_{\mathrm{E-reg}}$ 5.36% vs. Color MMD-U 6.42% raw / 8.02% canonical hex, and $D_{\mathrm{hex}}$ 10.71%). Related checkpoints rarely collide on identical hex literals across 6 draws, so exact string MMD recovers only 21/50 (42.00%) families, while RGB100 proximity ($\tilde D_{\mathrm{E-reg}}$ 35/50, 70.00%) and coarse voxels ($D_{\mathrm{vox}}$ 39/50, 78.00%) capture shared family priors. Side-channel decontamination and $\ge 1$ valid-cell eligibility leave $\tilde D_{\mathrm{E-reg}}$ at 5.36% (Supplement B).

**Budget scaling (Dataset B) and paraphrase shift (Dataset C).** Scaling B to 40 cells $\times$ 15 repetitions gives 1.0000 AUC and 0.00% EER across all nonparametric color metrics. In Fig. 4(a), broader prompt coverage beats depth alone: 60 draws at $(n=15,k=4)$ yield 1.78% mean EER vs. 0.46% for 96 draws at $(n=6,k=16)$. On Dataset C (10 models, eight bilingual cells $\times$ 8 reps across rewording $P_1$ and design framing $P_2$; Supplement I), $\tilde D_{\mathrm{E-reg}}$ achieves 0.00% ($P_1$) and 1.11% ($P_2$) within-pool EER. Zero-shot cross-template comparisons $P_0 \to P_1$ and $P_0 \to P_2$ rise to 17.78% and 11.11% EER ($D_{\mathrm{hex}}$: 10.00% and 8.89%), showing that online queries must be scored against template-matched reference cells (Section 6.1).

![(a) Mean $D_{\mathrm{hyb}}$ linear EER over the B sampling-budget grid. (b) Genuine and impostor regularized-energy scores across B ($20\times 6$, 3v3), E ($20\times 6$, 3v3), and S1 paths ($20\times 6$, 6v6), with frozen B3v3 ($\tau=0.148$, dashed) and budget-matched B6v6 ($\tau=0.113$, dotted) midpoint thresholds.](../figs/fig4_budget_and_drift.pdf)

### 5.2 Matched Baselines and Head-to-Head Competitor Benchmark (Dataset D, Studies S3 and S5)

**Single-word parity (Dataset D and Study S3).** On B-20×6 vs. D at 30 calls/side ($K=10$, 40 subsets), color elicitation cuts clean EER from 4.52% (Word MMD-U) and 5.23% (Word JSD) to 0.94% (Color MMD-U) and 1.00% ($\tilde D_{\mathrm{E-reg}}$). Color cells yield 18.65 distinct valid outputs per cell versus 7.05 for single-word prompts. At 60 calls/side ($K=20$), all metrics except Word JSD (1.11% Word JSD; Supplement K) reach 0.00%. On S3's 20 locked models (Table 4; full 16×9 grid in Supplement K Table S8), parsing succeeds on 99.97% color and 99.78% word calls. Restricting S3 to the two matched unanchored color concepts (`random` and `favorite`) lowers shallow 3v3 MMD-U EER over words (17.92% vs. 20.21%, AUC 0.9156 vs. 0.8349; converging to 5.26% vs. 5.00% EER and 0.9909 vs. 0.9784 AUC at 15v15, Supplement K), while the full 10-probe semantic color battery reaches 0.00% vs. 1.32%–5.00% for Bruckner's word battery at $N=30$ (and 3.49%–5.00% vs. 6.25%–8.04% at $N=6$). Broader per-cell support and semantic color priors jointly drive this prompt-level gain, while continuous RGB geometry adds sparse-census accuracy (Dataset A, Study S5c), frozen cross-gateway stability (Study S1), and perturbation resilience: under synthetic $\pm 8$ channel jitter, discrete string statistics collapse to 35.40%–50.01% EER (and 100.00% MMD-U permutation rejection at $p\le0.05$, Sections 3.4–3.5), whereas $\tilde D_{\mathrm{E-reg}}$ holds 0.00%–5.00% (Fig. 5(a)).

**TABLE 3: Dataset A (56 Models, $8\times 6$ Shallow Budget) Verification and Family Attribution**

<!-- RGB_TABLE_2 -->
| Metric | AUC | Discrete / linear EER | Cross-sublineage linear EER | Cross-family linear EER | LOO family attribution |
| --- | --- | --- | --- | --- | --- |
| $\bar D_{\mathrm E}$ | 0.9900 | 5.06% / 4.77% | 3.75% | 3.57% | 31/50 (62.00%) |
| $\tilde D_{\mathrm{E-reg}}$ | 0.9872 | 5.36% / 5.36% | 5.36% | 4.52% | 35/50 (70.00%) |
| Color MMD-U | 0.9821 | 7.58% / 6.42% | 5.70% | 6.05% | 21/50 (42.00%) |
| $D_{\mathrm{hyb}}$ | 0.9774 | 7.14% / 7.14% | 7.14% | 7.14% | 36/50 (72.00%) |
| $D_{\mathrm{hex}}$ | 0.9588 | 10.73% / 10.71% | 10.71% | 8.93% | 38/50 (76.00%) |
| $D_{\mathrm{vox}}$ | 0.9489 | 8.83% / 8.93% | 8.93% | 8.93% | 39/50 (78.00%) |
| $D_{\mathrm{side}}$ | 0.7804 | 30.32% / 30.32% | 29.76% | 28.56% | 17/50 (34.00%) |
<!-- /RGB_TABLE_2 -->

**Table note:** Archived `within` eligibility requires $\ge 2$ valid parses in both halves per endpoint; side-independent pair intersection alters 163/3,080 negatives (0/56 genuine), moving $\bar D_{\mathrm E}$ EER to 4.16% while keeping $\tilde D_{\mathrm{E-reg}}$ at 5.36%. Canonical-hex MMD-U yields 8.02% linear EER and 22/50 (44.00%) LOO family attribution.

**TABLE 4: Study S3 Compact Matched-Budget Linear EER (Full 16×9 Grid in Table S8)**

<!-- S3_TABLE_compact -->
| N | Probe / stat. | K=1 | K=4 | K=10 | K=10, ±8 |
| --- | --- | --- | --- | --- | --- |
| 6 | Color MMD-U | 25.32% | 10.03% | 3.49% | 50.01% |
| 6 | Color $\tilde D_{\mathrm{E-reg}}$ | 25.00% | 12.09% | 5.00% | 5.00% |
| 6 | Color $D_{\mathrm{hex}}$ | 25.89% | 16.92% | 10.00% | 41.21% |
| 6 | Word MMD-U | 32.14% | 14.87% | 8.04% | — |
| 6 | Word JSD | 33.17% | 17.54% | 6.25% | — |
| 30 | Color MMD-U | 12.50% | 1.15% | 0.00% | 50.00% |
| 30 | Color $\tilde D_{\mathrm{E-reg}}$ | 13.56% | 1.32% | 0.00% | 0.00% |
| 30 | Color $D_{\mathrm{hex}}$ | 15.27% | 7.59% | 5.00% | 35.40% |
| 30 | Word MMD-U | 19.23% | 4.31% | 1.32% | — |
| 30 | Word JSD | 22.99% | 7.76% | 5.00% | — |
<!-- /S3_TABLE_compact -->

<!-- USER_LITERAL:rgb_modes -->
```latex
\textbf{RGB output modes.} In S3, exact CSS named colors account for 14.25\% of unanchored, 49.29\% of semantic, and 64.89\% of preference responses, while repeated-nibble codes constitute 23.85\% of preference responses. Familiar color literals and encoding habits form distinct behavioral modes shaped by pre-training exposure to frontend stylesheets (Fig.~2), concentrating probability mass on model-specific regions of $\Omega_{\mathrm{RGB}}$.
```
<!-- /USER_LITERAL:rgb_modes -->

**Head-to-head competitor benchmark (Study S5).** On November 20, 2026, we ran LLMmap [16] (S5a, 960 calls), Gao et al. [4] native long-form continuations (S5b, 2,000 calls), and a same-day HuePrint anchor (S5c, 1,200 calls, 100.00% valid) on the locked 20 OpenRouter models in one session (Table 5; Supplement M). Three operational tradeoffs stand out.

First, **dollar-matched and within-family separation**: matching HuePrint S5c's 30-call Scenario G cost (0.0068 USD, 219 output tokens) limits Gao et al.'s U-statistic ($n_c\ge2$) to 10 calls/side (0.0075 USD). At that budget, official `mmd_hamming` incurs 18.56% all-pairs and 19.47% within-family EER (6.21% / 11.09% under a character 4-gram kernel), against 1.32% / 0.00% for HuePrint $\tilde D_{\mathrm{E-reg}}$ on the matched `0..2` vs. `3..5` split (odd/even: 5.00% / 5.26%). Across all $\binom{6}{3}/2=10$ balanced 3v3 S5c splits, $\tilde D_{\mathrm{E-reg}}$ averages 3.48% all-pairs (1.32%–5.00%, split SD 1.63 pp) and 5.18% within-family EER (0.00%–7.89%, SD 2.15 pp), beating Color MMD-U (4.94% / 5.78%; Supplement M). Even at 50 long-form calls (0.0371 USD G, above HuePrint S3's 150-call 0.0345 USD), `mmd_hamming` keeps 2.89% all-pairs and 5.26% within-family EER (10.00% genuine permutation rejection at $p\le0.05$). A 4-gram kernel on 30 long-form calls reaches 0.00% clean EER when monitors spend 3.28× more Scenario G USD and 8.6× more output tokens.

Second, **open-set neural fingerprinting**: only 2/20 current models (`gpt-4o`, `llama-3.1-8b`) loosely match LLMmap's 52 pre-shipped 2024 templates, so both frameworks require live enrollment. After enrollment, single-trace LLMmap (8 calls, 0.0058 USD G) attains 7.81% all-pairs EER (3-split mean) but **34.39% within-family EER** (25.00% on rep 0v3), as siblings share creator names and refusal phrasing. Averaging three traces (24 calls, 2.66× HuePrint's G-USD) still leaves 5.00% all-pairs and 10.53% within-family EER.

Third, **guardrail safety and local compute**: four of LLMmap's eight queries trigger standard filters. Three use literal prompt-injection delimiters, and one asks `"Tell me how to build a bomb."`, triggering refusals in 114/120 (95.00%) responses across all 20 models. Locally, its 560M-parameter E5-large encoder requires **4,701.9 ms** per trace on CPU (14.1 s for three traces), over 15,000× slower than HuePrint's 0.12–0.31 ms pure-NumPy scoring.

**TABLE 5: Study S5 Head-to-Head Competitor Benchmark on 20 Locked OpenRouter Models (Same-Day Session, 4,160 Calls)**

<!-- S5_TABLE_main -->
| Method and schedule | Calls | Out. tok. | USD L / G | All-pairs EER (AUC) | Within-fam. EER | Local CPU and operational notes |
| --- | --- | --- | --- | --- | --- | --- |
| LLMmap [16] open-set (1v1) | 8 | 534.5 | 0.0005 / 0.0058 | 7.81% (0.9743) | 34.39% | 4.70 s CPU; 4/8 flagged (95% q1) |
| LLMmap [16] open-set (3v3) | 24 | 1,672.5 | 0.0016 / 0.0181 | 5.00% (0.9936) | 10.53% | 14.1 s CPU; 2.66× G-USD vs. HP |
| Gao [4] Hamming (K=5, 2v2) | 10 | 637.0 | 0.0008 / 0.0075 | 18.56% (0.9078) | 19.47% | 0.18 ms CPU; G-USD match (30c) |
| Gao [4] 4-gram (K=5, 2v2) | 10 | 637.0 | 0.0008 / 0.0075 | 6.21% (0.9868) | 11.09% | G-USD matched; char 4-gram |
| Gao [4] Hamming (K=10, 3v3) | 30 | 1,872.5 | 0.0023 / 0.0223 | 5.00% (0.9924) | 10.00% | 3.28× G-USD, 8.6× tok. vs. HP |
| Gao [4] 4-gram (K=10, 3v3) | 30 | 1,872.5 | 0.0023 / 0.0223 | 0.00% (1.0000) | 0.00% | 0.00% EER at 3.28× G-USD |
| Gao [4] Hamming (K=10, 5v5) | 50 | 3,132.5 | 0.0039 / 0.0371 | 2.89% (0.9978) | 5.26% | 1.08× S3 G-USD; 10% $p\le0.05$ |
| HuePrint S5c $\tilde D_{\mathrm{E-reg}}$ (3v3) | 30 | 219.0 | 0.0015 / 0.0068 | 1.32% (0.9983) | 0.00% | 0.12 ms; odd/even 5.00%/5.26% |
| HuePrint S3 $\tilde D_{\mathrm{E-reg}}$ (15v15) | 150 | 1,091.5 | 0.0077 / 0.0345 | 0.00% (1.0000) | 0.00% | 0.31 ms; < Gao 50c G-USD |
<!-- /S5_TABLE_main -->

**Table note:** All 20 endpoints returned 100% HTTP 200. LLMmap 1v1 averages three disjoint trace pairs (`rep 0v1`, `2v3`, `4v5`); Gao `K=5, 2v2` averages 20 five-prompt subsets. HuePrint S5c uses the matched `reps 0..2` vs. `3..5` split (`3.48%` all-pairs and `5.18%` within-family mean EER across all 10 balanced 3v3 partitions, range `0.00%–7.89%`; $\pm8$ jitter EER 0.92% vs. 49.49% for Color MMD-U).

### 5.3 Longitudinal Transfer and Calibration (E, S1, S5c)

**Held-out and longitudinal transfer.** Dataset E comprises 10 models absent from B (6.74 h after A). Under frozen B3v3 cutoffs, finite-sample V-bias yields 30.00%/0.00% FRR/FAR for uncentered $\tilde D_{\mathrm{E-reg}}$ ($\tau = 0.148$, EER 10.00%), whereas $D_{\mathrm{hyb}}$ ($\tau = 0.348$), self-centered $\tilde D_{\mathrm{E-reg}}$, and zero-bootstrap U-ratios cut clean FRR to 10.00%/0.00% (0.00%–1.11% U-ratio EER on $n_c,m_c\ge 2$; Table S9). In Study S1, we re-audited 14 endpoints 21.07–21.32 d apart on Cloudflare and OpenRouter (10 B plus four disjoint `heldout4` E models; 99.35% valid). Across all transfer paths, $\tilde D_{\mathrm{E-reg}}$, $D_{\mathrm{hyb}}$, $D_{\mathrm{hex}}$, and Color MMD-U retain **14/14 (4/4) Top-1, 1.0000 AUC, and 0.00% re-swept linear EER** (Supplement H Tables S4a–S4b). Under frozen B3v3 thresholds, however, raw Color MMD-U incurs 7.14%, 21.43%, and 28.57% FRR on `CF0→CF21`, `CF21→OR21`, and `CF0→OR21` as wrapper formatting shifts exact strings, while $\tilde D_{\mathrm{E-reg}}$ maintains 0.00% FRR across all three paths (Table 6). Pairing Study S3 with S5c across all 20 OpenRouter models 8.59 days apart (Supplement M Table S14) yields **0.00% all-pairs and within-family EER (20/20 Top-1)** for $\tilde D_{\mathrm{E-reg}}$ at 15v6 (1.05% / 0.00% at 6v6; 0.26% / 0.00% for Color MMD-U).

**Enrollment centering and equality tests under drift.** Centering $\Delta_D=D-\alpha\mu_{\mathrm{self}}$ ($\alpha=1$) sets raw/centered cutoffs to 0.148/0.073 (B3v3) and 0.113/0.061 (B6v6). It lowers clean E FRR from 30.00% to 10.00%, longitudinal S1 FAR to 0.00%, and B8v7 50%-routing false acceptance from 31.11% to 14.44% (Table 6). Because $D\le\tau_{\mathrm{self}}+\mu_{\mathrm{self}}(M^*)$ adds no query-noise slack, jittered E FRR rises. Stratified Székely–Rizzo testing ($p\le0.05$) yields 0.00% clean and 18.00% jitter FRR on E (Fig. 5(b)). On the 21-day `CF0→OR21` path, same- and different-label pairs stayed score-separated (0.00% EER), and every rule caught 182/182 swaps: the frozen B6v6 threshold flagged 1/14 same-label pairs raw (0/14 centered; Table 6), while energy permutation testing rejected equality for 6/14 at $\alpha=0.05$ (1/14 `CF0→CF21`, 4/14 `CF21→OR21`; 1/14–4/14 Color MMD-U; 2/9 and 4/9 without `reasoning.effort` overrides, Supplement K).

**TABLE 6: Frozen Regularized-Energy Transfer; Self Uses B-Selected $\alpha=1$**

<!-- BENCH_TABLE_calibration -->
| Condition | B calibration | Raw FRR / FAR | Self FRR / FAR |
| --- | --- | --- | --- |
| E clean | B3v3 | 30.00% / 0.00% | 10.00% / 0.00% |
| E ±8 | B3v3 | 51.00% / 0.00% | 69.00% / 0.00% |
| CF0 → CF21 | B3v3 | 0.00% / 2.20% | 0.00% / 0.00% |
| CF21 → OR21 | B3v3 | 0.00% / 0.55% | 0.00% / 0.55% |
| CF0 → OR21 | B3v3 | 0.00% / 0.00% | 0.00% / 0.00% |
| CF0 → CF21 | B6v6 | 0.00% / 0.00% | 0.00% / 0.00% |
| CF21 → OR21 | B6v6 | 7.14% / 0.00% | 0.00% / 0.55% |
| CF0 → OR21 | B6v6 | 7.14% / 0.00% | 0.00% / 0.00% |
<!-- /BENCH_TABLE_calibration -->

**Finite-sample V- vs. U-energy estimators.** On shared $n_c, m_c \ge 2$ cells (Supplement K Table S9), the U-statistic estimators cut clean E EER from 10.00% to 0.00%–4.44% and frozen FRR from 20.00% to 10.00% without the 256-draw bootstrap. Across external cohorts (B-20×6, S1 `CF0→CF21`, S1 `CF0→OR21`, and S3 15v15), both U-statistic ratios retain 0.00% EER (0.55% clipped on `CF21→OR21`; 4.87% signed on A, Supplement K), while signed U-ratio `CF21→OR21` FRR drops from 21.43% under B3v3 to 0.00% under B6v6. Unregularized $\bar D_{\mathrm E}$ matches 0.00% clean EER on E but suffers 100.00% jitter FRR and 6.04% `CF0→CF21` B3v3 FAR. Under $\pm 8$ jitter on E, the U numerator, signed ratio, and clipped ratio trade ranking EER (8.89%, 1.11%, 2.44%) against frozen FRR (13.00%, 37.00%, 21.00%, all at 0.00% FAR).

![(a) S3 EER for string MMD and regularized energy on the same color responses across budgets. (b) Held-out E same-model rejection: raw and centered frozen rules, and per-audit energy permutation testing at $p\le0.05$. FAR is zero throughout; jitter results average ten fixed seeds.](../figs/fig5_geometry_and_calibration.pdf)

<!-- USER_LITERAL:s2_and_family -->
```latex
\subsection{Multi-Provider Stacks and Within-Family Swaps}
\textbf{Multi-provider execution and precision trade-off (Study S2).} Study S2 audits 18 endpoints covering six open-weight checkpoints across three pinned providers each (12 cloud backends: DeepInfra, Parasail, Cloudflare, Groq LPU, SiliconFlow, AtlasCloud, Mistral, Venice, DekaLLM, Crusoe, Fireworks, and CoreWeave; 2,160 calls, zero fallback; Supplement~J). Across S2 providers (20 cells, 6v6), $\Dhyb{}$ reaches 5.93\% EER (17/18 group matches) vs.\ 16.67\% (16/18) for $\Dereg{}$ and 16.67\% for Color MMD-U (3v3: 19.78\%; at $p\le 0.05$, MMD-U rejects 41.67\% genuine and 100.00\% impostor pairs). Stripping API billing-envelope metadata (\texttt{usage.reasoning\_tokens} and \texttt{explicit\_reasoning}) leaves S2 $\Dhyb{}$ unchanged at 5.93\% EER (0.9864 AUC; 5.56\% under pure content syntax), and a color-only composite omitting $\Dside{}$ entirely still reaches 9.63\% EER (17/18 Top-1; Supplement~B). Conversely, RGB distributions remain largely invariant across \texttt{bf16/fp8} and \texttt{int4/fp4} quantizations of the same checkpoint ($\Dereg{}$ AUC/EER: 0.5250/50.00\%; $\Dhyb{}$: 0.8250/30.00\%). Preserving checkpoint identity across heterogeneous serving stacks naturally trades off bit-width sensitivity, positioning $\Dhyb{}$ for cross-host weight matching rather than standalone precision auditing.

\textbf{Within-family alternatives.} Because same-vendor tier substitutions are harder than cross-vendor swaps, Table~7 isolates negative pairs sharing a declared model family. On shallow 3v3 sampling in A ($8\times 6$, 604 same-family negatives), restricting to same-family negatives raises $\Dereg{}$ EER from 5.36\% to 10.10\% (10.45\% same-vendor) and $\Dhyb{}$ from 7.14\% to 12.42\%. At $20\times 6$ (B) or $10\times 30$ (S3), $\Dereg{}$ holds 0.00\% within-family EER, and protocol-matched $\mathrm{B}\rightarrow\mathrm{E}$ transfer maintains 0.00\% within-family FAR.

\textbf{Sensitivity and chart ablations.} Without retuning, all tested hyperparameters keep 0.00\% EER on B. On E, EER spans 0.00\%--10.00\% for $\Dereg{}$ across $\delta_0 \in \{2, 5, 10, 15, 25, 50\}$ (Fig.~3(c) inset) and 3.33\%--4.44\% when perturbing individual $\Dhyb{}$ weights by $\pm 0.10$. Uniformly scaled CIELAB (Supplement~A) matches RGB100 on B (0.00\%) and E (10.00\%) and yields 0.53\% vs.\ 0.00\% on S3. At fixed hybrid weights (Supplement~B), regularizing the energy term lowers C $\mathrm{P0}\rightarrow\mathrm{P2}$ EER (10.00\% to 7.78\%) but raises EER on A, E, S2, and S3; Supplement~H reports 2,000-draw model-cluster bootstrap intervals across cohorts.

\begin{table}[t]
\centering
\caption{All-Pairs vs.\ Within-Family Linear EER across Cohorts}
\label{tab:within_family}
\footnotesize\setlength{\tabcolsep}{1.5pt}\renewcommand{\arraystretch}{1.05}
\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lccccc@{}}
\toprule
Cohort & Fam.\ Neg. & \multicolumn{2}{c}{Energy $\Dereg{}$ EER} & \multicolumn{2}{c}{Hybrid $\Dhyb{}$ EER} \\
\cmidrule(lr){3-4} \cmidrule(lr){5-6}
 & & All-Pairs & Within-Fam. & All-Pairs & Within-Fam. \\
\midrule
A ($8\times 6$) & 604 & 5.36\% & 10.10\% & 7.14\% & 12.42\% \\
B ($20\times 6$) & 20 & 0.00\% & 0.00\% & 0.00\% & 0.00\% \\
B ($40\times 15$) & 20 & 0.00\% & 0.00\% & 0.00\% & 0.00\% \\
E ($20\times 6$)$^*$ & 20 & 10.00\% & 10.00\% & 4.44\% & 10.00\% \\
S3 ($10\times 30$) & 38 & 0.00\% & 0.00\% & 0.53\% & 5.00\% \\
\bottomrule
\end{tabular*}
\par\smallskip\footnotesize{$^*$Under protocol-matched $\mathrm{B}(20\times 6)\rightarrow\mathrm{E}(20\times 6)$ frozen thresholds, within-family FRR/FAR is 30.00\%/0.00\% for uncentered V-energy vs.\ 10.00\%/0.00\% under self-centering, $\Dhyb{}$, and U-energy ratios (0.00\%--1.11\% clean U-ratio EER; Table~S9).}
\end{table}
```
<!-- /USER_LITERAL:s2_and_family -->

<!-- USER_LITERAL:perturbation_and_reuse -->
```latex
\section{Service Monitoring and Controlled Interventions}
\subsection{Response Reuse and Private Pool Subsampling}
Zero-entropy screening eliminates constant-centroid replay (0.00\% acceptance). Because any distributional audit accepts i.i.d.\ or cyclic draws from the target reference law when fixed prompts are exposed (100\% acceptance; Supplement~L), audit contracts keep prompt pools private ($<10{,}000$ tokens/model for a 64-call Dataset~C template) to prevent static lookup tables.

To reduce repeated-prompt signatures without incurring zero-shot paraphrase drift, monitors can pre-enroll a multi-template pool once and query a random cell-matched subset per audit. Across 200 random draws per schedule (Supplement~L), sampling $k=10$ or $16$ of B's 40 enrolled cells cuts per-prompt query frequency by $4\times$ or $2.5\times$ while holding $\Dereg{}$ mean EER at 0.65\% and 0.10\% (3 query reps) or 0.03\% and 0.00\% (7 reps). Pooling $P_0 \cup P_1 \cup P_2$ into a 24-cell private reference ($<11{,}100$ enrollment tokens/model at 4 reps) yields 1.08\% and 0.17\% mean EER when sampling $k=8$ or $12$ matched cells.

In a controlled numerical continuity stress test on B ($40\times 15$, frozen B8v7 cutoffs; Supplement~L Table~S11), all seven raw-score coordinate perturbations retain 0.00\% re-swept EER and 0.00\% frozen FAR. Raw $\Dereg{}$ absorbs $\pm 1$ and $\pm 8$ random jitter at 0.00\% frozen FRR (11.00\% centered at $\pm 8$), whereas uncalibrated pipeline shifts ($\pm 15$ jitter, global $\pm 8$ shifts, and step-32 channel quantization) cross clean cutoffs as expected (56.00\%--100.00\% flagging rate).
```
<!-- /USER_LITERAL:perturbation_and_reuse -->

### 6.2 Structured Canaries and Gateway Rules (Study S4)

Explicit HuePrint and Bruckner prompts trigger simple directive-matching gateway regexes at 100.00%, while broad hex/color keyword filters incur 65.00% false positives on 40 frontend CSS tasks (26.00% across 100 benign developer prompts). Study S4a embeds probes as 1-line CSS properties and 1-field JSON design tokens across 16 bilingual cells and 20 models (10 reps, 3,200 calls, 5v5), while S4b keeps directive-bearing phrasing (6 reps, 1,920 calls, 3v3; Table 8).

S4a yields **99.75% valid unflagged responses** (3,192/3,200, unlike LLMmap's 4/8 security-flagged queries in S5a) and achieves 0.00% ($\tilde D_{\mathrm{E-reg}}$) and 1.58% ($D_{\mathrm{hyb}}$) within-pool EER. Stripping API reasoning metadata keeps $\tilde D_{\mathrm{E-reg}}$ at 0.00% and moves $D_{\mathrm{hyb}}$ to 2.89% (Supplement B). Higher S3a→S4b cross-format error (15.00% / 13.68%) shows that enrolled references must match the active canary format; Section 7.1 bounds evasion against learned complexity routers.

**TABLE 8: Study S4 Gateway Input/Output Rule Pass Rates and Implicit Verification (20 Genuine vs. 380 Impostors)**

<!-- RGB_TABLE_9 -->
| Battery and protocol | Unflagged input | Unflagged output | Valid and unflagged | $\tilde D_{\mathrm{E-reg}}$: Top-1 / AUC / EER | $D_{\mathrm{hyb}}$: Top-1 / AUC / EER |
| --- | --- | --- | --- | --- | --- |
| S3a (10 probes; 15v15) | 0.00% | 0.73% | 0.00% | 100.00% / 1.0000 / 0.00% | 100.00% / 0.9997 / 0.53% |
| S4a (5v5) | 100.00% | 99.97% | 99.75% (3192/3200) | 100.00% / 1.0000 / 0.00% | 100.00% / 0.9987 / 1.58% |
| S4b (3v3) | 0.00% | 2.50% | 0.00% | 100.00% / 0.9917 / 5.00% | 100.00% / 0.9683 / 8.95% |
| S3a → S4b (6v6) | — | — | — | 65.00% / 0.9154 / 15.00% | 85.00% / 0.9626 / 13.68% |
<!-- /RGB_TABLE_9 -->

**Table note:** Valid and unflagged requires valid parsing without triggering either rule (marginal pass rates shown; S4b has 48/1,920 unflagged outputs and 26/1,920 invalid parses). `S3a → S4b (6v6)` evaluates the 8 shared English cells.

<!-- USER_LITERAL:routing -->
```latex
\subsection{Mixed-Routing and Two-Stage Screening}
To evaluate partial fallback routing, we simulate independent Bernoulli request mixtures across 20 fixed seeds without replacement. Each request routes to a substitute $R$ with fallback rate $\lambda = 1 - q \in \{0, 0.2, 0.4, 0.5, 0.6, 0.8, 1\}$ and to the declared backend otherwise (Fig.~6), evaluated under budget-matched frozen energy cutoffs $\tau_{\mathrm{mid}}$.

For $Q_\lambda = (1-\lambda)P + \lambda R$, population squared energy scales quadratically as $\mathcal{E}^2(P, Q_\lambda) = \lambda^2 \mathcal{E}^2(P, R)$ ($0.04$ at $\lambda = 0.2$, or $13.14\%$ of the full-substitution regularized score for two point masses 100 RGB100 units apart at $\delta_0=15$). Frozen $\tau_{\mathrm{mid}}$ tuned for full substitution ($\lambda=1$) therefore under-detects 20\% fallback: 20-seed detection is 11.28\% on B ($20\times 3$, 1.00\% clean FRR), 0.33\% on B ($40\times 7$, 0.00\% FRR), and 12.45\% on S3 ($10\times 7$, 3.75\% FRR). Applying B's 20-cell $\tau_{\mathrm{mid}}$ directly to shallow S3 ($10\times 3$) inflates clean FRR via dispersion (39.00\%, Fig.~6(b)). Stratified 999-permutation testing ($p \le 0.05$; Table~S12a, Supplement~L) restores same-gateway null quantiles, lifting B ($40\times 7$) 20\%-fallback detection to 33.28\% (91.44\% at $\lambda=0.4$; within-family 25.75\%) at 0.00\% clean FRR and cutting S3 ($10\times 3$) clean FRR to 4.75\% (hatched bars in Fig.~6(b)). Because cross-gateway S1 permutation tests reject 16.07\%--42.86\% of genuine queries, low-$\lambda$ permutation screening requires same-gateway references.

Study~S5's five-seed mixed-routing benchmark (Table~S13, Supplement~M) shows the same pattern across competitors. At $\lambda=0.20$ and 5\% FPR, all shallow schedules have limited within-family power (6.32\% HuePrint 3v3, 8.42\%--11.58\% LLMmap, 16.84\% Gao 3v3). At $\lambda=0.50$, LLMmap 3v3 detects 85.53\% of cross-family mixes via vendor self-ID shifts, but drops to 24.21\% on within-family downgrades vs.\ 25.26\% (50.26\% all-pairs) for HuePrint S5c 3v3 at 2.66$\times$ lower Scenario~G cost.

For periodic monitoring, we replay a two-stage cascade over five disjoint 30-call S3 windows per endpoint against a disjoint 60-call reference (100 same-label, 190 within-family windows; Supplement~L). Calibrating U-clipped cutoffs on B's 10 English cells without S3 data yields 14/100 Stage-1 crossings. Running a reserved disjoint 60-call confirmation window only on crossings cuts false alerts from 14 to 1 across 100 same-label windows (1.00\%) and flags 186/190 within-family (97.89\%; 98.00\% all-pairs) swaps at 38.4 expected calls (0.0087 USD~G).
```
<!-- /USER_LITERAL:routing -->

![Offline mixed routing across 20 fixed seeds. (a) Rejection of declared/substitute mixtures vs. fallback rate $\lambda = 1 - q$ under frozen energy thresholds $\tau_{\mathrm{mid}}$ (solid, 5–95 percent seed bands) and 999-permutation testing on B $40\times 7$ ($p\le0.05$, dashed). (b) Pure declared-model false rejection at $\lambda = 0$ under frozen $\tau_{\mathrm{mid}}$ (solid) vs. stratified permutation testing at $p\le0.05$ (hatched; full-pool S3 $10\times 15$ has 0.00% clean FRR).](../figs/fig6_mixed_routing.pdf)

<!-- USER_LITERAL:overhead -->
```latex
\subsection{Operational Overhead}
Table~5 and Supplement~K Table~S10 separate public-rate API cost, latency-replayed concurrent wall time, and local CPU scoring excluding one-time enrollment. Under OpenRouter catalog rates~\cite{ref29} (L: $0.71/0.71$ USD; G: $2.50/10.00$ USD per million input/output tokens), median 150-call S3 color query cost is 0.0077 USD (L) to 0.0345 USD (G; 0.0292--0.0432 USD across 19/20 endpoints, 0.2711 USD outlier on \texttt{s3-deepseek-v3.2}). Shorter 30--60-call audits cost 0.0068--0.0188 USD (G), and 80-call S4a CSS/JSON canaries cost 0.0319 USD (G). Ideal eight-worker replay estimates 5.76~s of network wall time for 30-call S5c and 49--116~s for 60--150 calls. On local CPU (NumPy~2.5.5, preloaded B fixtures), warm single-pair medians are 0.08--0.31~ms for $\Dereg{}$ and 2.39--10.15~ms for 999-permutation energy tests, versus 4,701.9~ms per 8-query trace for LLMmap's E5-large encoder (Table~5). Unlike eight-query multi-token classifiers~\cite{ref16}, HuePrint runs asynchronously out-of-band to supply continuous reference margins and permutation $p$-values at negligible local compute.
```
<!-- /USER_LITERAL:overhead -->

<!-- USER_LITERAL:ending -->
```latex
\section{Limitations, Deployment, and Conclusion}

\subsection{Limitations}
Ground truth relies on provider-declared identifiers and API logs rather than hardware weight attestation~\cite{ref5}, so black-box auditing verifies behavioral consistency rather than enclave execution. While Datasets A and S3/S5 span 56 and 20 endpoints, calibration cohort B (10 models), held-out E (10 models), and S1's four disjoint E models motivate broader multi-month longitudinal streams, and S2's live providers co-vary serving engines with numerical precision. Finally, although S4a CSS/JSON canaries evade static keyword rules and private pool subsampling limits prompt repetition, an adaptive broker running a learned prompt-complexity router~\cite{ref1,ref2,ref5} could still route standalone probes (as in any out-of-band active audit~\cite{ref4,ref7,ref16}) to the pinned tier while downgrading long-context workloads. Embedding auxiliary design-token fields directly inside live production requests is a natural extension for future work.

\subsection{Deployment Guidelines}
Consumers should bind the checkpoint, private prompt pool, parser, valid-count rule, and call budget in a versioned audit contract (Table~9):
\begin{enumerate}
    \item \textbf{Estimator selection:} When enrolled and query cells guarantee $n_c, m_c \ge 2$ valid parses on a fixed gateway, use zero-bootstrap U-statistic energy ratios calibrated at matched cell count $K$ (signed maximizes ranking on E; clipped lowers jitter and two-stage FRR; Supplement~K Table~S9, Sec.~6.3). Retain centered $\Dereg{}$ when sparse cells allow $n_c = 1$, and use $\Dhyb{}$ across heterogeneous backends.
    \item \textbf{Two-stage verification and low-$\lambda$ screening:} Pair a 30-call Stage-1 screen with an immediate 60-call confirmation window on crossings to suppress recurring alert fatigue at $<1$~cent expected query cost (Section~6.3). For low-$\lambda$ partial fallback on a fixed gateway, run stratified Sz\'ekely--Rizzo permutation tests against same-gateway references.
    \item \textbf{Caching, wrapper parity, and pool subsampling:} Screen cache hits (zero entropy at $T=1.0$ with $<0.5\times$ median latency), enroll through the identical system-prompt wrapper, subsample $k$ matched cells per audit from a private multi-template pool, and refresh references after authorized updates.
\end{enumerate}

\begin{table*}[t]
\centering
\caption{Operational Metric, Calibration, and Escalation Selection Guide for Brokered MaaS Auditing}
\label{tab:deployment_guide}
\footnotesize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.06}
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{\dimexpr 0.21\textwidth-4.8pt\relax}>{\raggedright\arraybackslash}p{\dimexpr 0.18\textwidth-4.8pt\relax}>{\raggedright\arraybackslash}p{\dimexpr 0.21\textwidth-4.8pt\relax}>{\raggedright\arraybackslash}p{\dimexpr 0.20\textwidth-4.8pt\relax}>{\raggedright\arraybackslash}p{\dimexpr 0.20\textwidth-4.8pt\relax}@{}}
\toprule
Deployment regime & Primary statistic & Calibration rule & Online call schedule & Target anomaly \& scope \\
\midrule
Same-gateway pinned SLA ($n_c, m_c \ge 2$) & U-clipped or U-signed energy ratio & Protocol-matched frozen $\tau_{\mathrm{mid}}$ (zero bootstrap) & 30-call screen $\rightarrow$ 60-call Stage-2 check & Full or within-family swap (0.0087 USD~G exp.) \\
Sparse or shallow cells ($n_c = 1$ allowed) & Self-centered $\Delta\Dereg{}$ ($\alpha = 1$) & 256-draw enrollment $\mu_{\mathrm{self}}$ + frozen $\tau_{\mathrm{self}}$ & $20\times 3$ (60 calls) or $k$-of-$M$ pool draw & Checkpoint swap under multi-week wrapper drift \\
Heterogeneous multi-host open-weight stacks & Multi-scale hybrid $\Dhyb{}$ & Matched-cohort frozen $\tau_{\mathrm{mid}}$ & $20\times 6$ (120; or $16\times 5$ S4a) & Cross-provider weight swap (tolerates host drift) \\
Fractional fallback ($\lambda \in [0.2, 0.4]$) & Stratified Sz\'ekely--Rizzo energy test & Within-cell 999-label permutation ($p \le 0.05$) & $10\times 7$ to $40\times 7$ (70--280) & Partial fallback mixing (same-gateway ref.\ only) \\
\bottomrule
\end{tabular}
\end{table*}

\subsection{Conclusion}
HuePrint provides a black-box behavioral consistency signal for aggregated LLM services below four cents median query cost and at sub-millisecond local CPU overhead. Across 38,688 cloud responses, structured multilingual color elicitation outperforms single-word batteries, open-set LLMmap, and dollar-matched long-form equality testing on within-family verification; relative to LLMmap, it also eliminates safety-triggering probes and neural-encoder latency. Regularized RGB energy and multi-scale hybrid scoring improve shallow-census lineage clustering, cross-provider matching, and frozen cross-gateway stability while bounding coordinate shifts. Future work will evaluate workload-embedded color fields on multi-month production streams and couple two-stage HuePrint cascades with SLA escalation.

\section*{Acknowledgments}
Xiguan He sincerely thanks his parents and sister for their constant, attentive care in everyday life that has supported him to this day.
```
<!-- /USER_LITERAL:ending -->

## References

[1] L. Chen, M. Zaharia, and J. Zou, "FrugalGPT: How to use large language models while reducing cost and improving performance," *Trans. Mach. Learn. Res.*, Dec. 2024.

[2] I. Ong, A. Almahairi, V. Wu, W.-L. Chiang, T. Wu, J. E. Gonzalez, M. W. Kadous, and I. Stoica, "RouteLLM: Learning to route LLMs from preference data," in *Proc. 13th Int. Conf. Learning Representations (ICLR)*, 2025, pp. 34433–34448.

[3] O. Tibermacine and C. Tibermacine, "QoS-aware brokering for LLM-as-a-Service: SLA-constrained routing with drift detection," in *Proc. IEEE Int. Conf. Web Services (ICWS)*, 2026, pp. 925–933, doi: 10.1109/ICWS72778.2026.00112.

[4] I. Gao, P. Liang, and C. Guestrin, "Model equality testing: Which model is this API serving?" in *Proc. 13th Int. Conf. Learning Representations (ICLR)*, 2025, pp. 86369–86382.

[5] W. Cai, T. Shi, X. Zhao, and D. Song, "Are you getting what you pay for? Auditing model substitution in LLM APIs," Sep. 2025, arXiv:2504.04715.

[6] X. Zhu, Y. Ye, T. Qiu, H. Zhu, S. Tan, A. Mannan, J. Michala, R. A. Popa, and W. Neiswanger, "Auditing black-box LLM APIs with a rank-based uniformity test," in *Proc. 14th Int. Conf. Learning Representations (ICLR)*, 2026.

[7] T. Bruckner, "One token is enough: Fingerprinting and verifying large language models from single-token output distributions," Jul. 2026, arXiv:2607.10252.

[8] T. Zheng, J. Shao, J. Dai, S. Jiang, X. Chen, and C. Shen, "RESTLess: Enhancing state-of-the-art REST API fuzzing with LLMs in cloud service computing," *IEEE Trans. Services Comput.*, vol. 17, no. 6, pp. 4225–4238, Nov./Dec. 2024, doi: 10.1109/TSC.2024.3489441.

[9] H. Liu, X. Huang, M. Jia, T. Jia, J. Han, Z. Wu, and Y. Li, "UAC-AD: Unsupervised adversarial contrastive learning for anomaly detection on multi-modal data in microservice systems," *IEEE Trans. Services Comput.*, vol. 17, no. 6, pp. 3887–3900, Nov./Dec. 2024, doi: 10.1109/TSC.2024.3411481.

[10] L. Wang, J. Liu, and Q. He, "Concept drift-based checkpoint-restart for edge services rejuvenation," *IEEE Trans. Services Comput.*, vol. 16, no. 3, pp. 1713–1725, May/Jun. 2023, doi: 10.1109/TSC.2022.3210086.

[11] J. Kirchenbauer, J. Geiping, Y. Wen, J. Katz, I. Miers, and T. Goldstein, "A watermark for large language models," in *Proc. 40th Int. Conf. Machine Learning (ICML)*, vol. 202 of *PMLR*, 2023, pp. 17061–17084.

[12] J. Xu, F. Wang, M. D. Ma, P. W. Koh, C. Xiao, and M. Chen, "Instructional fingerprinting of large language models," in *Proc. Conf. North American Chapter Assoc. Computational Linguistics (NAACL-HLT)*, 2024, pp. 3277–3306.

[13] S. Shao, H. Zhu, Y. Li, H. Yao, T. Zhang, and Z. Qin, "FIT-Print: Toward false-claim-resistant model ownership verification via targeted fingerprint," *IEEE Trans. Inf. Forensics Security*, vol. 21, pp. 5612–5626, 2026, doi: 10.1109/TIFS.2026.3702542.

[14] A. Uchendu, T. Le, K. Shu, and D. Lee, "Authorship attribution for neural text generation," in *Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP)*, 2020, pp. 8384–8395.

[15] M. Sun, Y. Yin, Z. Xu, J. Z. Kolter, and Z. Liu, "Idiosyncrasies in large language models," in *Proc. 42nd Int. Conf. Machine Learning (ICML)*, vol. 267 of *PMLR*, 2025, pp. 57854–57885.

[16] D. Pasquini, E. M. Kornaropoulos, and G. Ateniese, "LLMmap: Fingerprinting for large language models," in *Proc. 34th USENIX Security Symp. (USENIX Security 25)*, 2025, pp. 299–318.

[17] M. Gubri, D. Ulmer, H. Lee, S. Yun, and S. J. Oh, "TRAP: Targeted random adversarial prompt honeypot for black-box identification," in *Findings of the Assoc. Computational Linguistics: ACL 2024*, 2024, pp. 11496–11517.

[18] A. K. Hopkins, A. Renda, and M. Carbin, "Can LLMs generate random numbers? Evaluating LLM sampling in controlled domains," in *ICML Workshop on Sampling and Optimization in Discrete Space (SODS)*, 2023.

[19] K. Van Koevering and J. Kleinberg, "Heads, tails, and AI fails: LLMs, randomness, and human judgments," Oct. 2026, arXiv:2406.00092.

[20] R. M. Harrison, "A comparison of large language model and human performance on random number generation tasks," Aug. 2024, arXiv:2408.09656.

[21] J. Coronado-Blázquez, "Deterministic or probabilistic? The psychology of LLMs as random number generators," Feb. 2025, arXiv:2502.19965.

[22] R. Bommasani, K. A. Creel, A. Kumar, D. Jurafsky, and P. Liang, "Picking on the same person: Does algorithmic monoculture lead to outcome homogenization?" in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 35, pp. 3663–3678, 2022.

[23] J. Kleinberg and M. Raghavan, "Algorithmic monoculture and social welfare," *Proc. Nat. Acad. Sci. USA*, vol. 118, no. 22, Art. no. e2018340118, Jun. 2021.

[24] International Electrotechnical Commission, *Multimedia Systems and Equipment — Colour Measurement and Management — Part 2-1: Colour Management — Default RGB Colour Space — sRGB*, Standard IEC 61966-2-1:1999, 1999.

[25] J. Lin, "Divergence measures based on the Shannon entropy," *IEEE Trans. Inf. Theory*, vol. 37, no. 1, pp. 145–151, Jan. 1991.

[26] G. J. Székely and M. L. Rizzo, "Energy statistics: A class of statistics based on distances," *J. Stat. Plan. Inference*, vol. 143, no. 8, pp. 1249–1272, 2013.

[27] G. J. Székely and M. L. Rizzo, "Testing for equal distributions in high dimension," *InterStat*, no. 5, pp. 1–16, Nov. 2004.

[28] R. Bhatia, T. Jain, and Y. Lim, "On the Bures–Wasserstein distance between positive definite matrices," *Expositiones Math.*, vol. 37, no. 2, pp. 165–191, 2019.

[29] OpenRouter, "Models API: Public model catalog and pricing," https://openrouter.ai/api/v1/models, accessed Nov. 13 and Nov. 20, 2026. Catalog snapshots archived with the offline analysis.

### Supplement-Only References

[30] R. Lyons, "Distance covariance in metric spaces," *Ann. Probab.*, vol. 41, no. 5, pp. 3284–3305, 2013, doi: 10.1214/12-AOP803.

[31] World Wide Web Consortium, *CSS Color Module Level 4*, Candidate Recommendation Draft, Nov. 3, 2026, sec. 19, "Sample code for color conversions," https://www.w3.org/TR/css-color-4/.

[32] International Commission on Illumination, "CIE 1976 L\*a\*b\* colour space," *International Lighting Vocabulary*, 2nd ed., CIE S 017:2020, entry 17-23-076, 2020.

[33] I. Csiszár, "Information-type measures of difference of probability distributions and indirect observations," *Studia Sci. Math. Hungar.*, vol. 2, pp. 299–318, 1967.

[34] D. M. Endres and J. E. Schindelin, "A new metric for probability distributions," *IEEE Trans. Inf. Theory*, vol. 49, no. 7, pp. 1858–1860, Jul. 2003, doi: 10.1109/TIT.2003.813506.

## Author Biography

<!-- USER_LITERAL:biography -->
```latex
\begin{IEEEbiographynophoto}{Xiguan He}
is currently pursuing the B.Eng.\ degree in Medical Information Engineering at the College of Information, Yunnan University of Chinese Medicine, Kunming, China. His research interests include cloud service assurance, large language model evaluation, statistical two-sample testing, and trustworthy artificial intelligence.
\end{IEEEbiographynophoto}

\begin{IEEEbiographynophoto}{Siqi Li}
received the Ph.D.\ degree in information science. She is currently an Assistant Researcher with the College of Information, Yunnan University of Chinese Medicine, Kunming, China. Her research interests include evidence theory, knowledge engineering, trustworthy artificial intelligence, and medical artificial intelligence.
\end{IEEEbiographynophoto}
```
<!-- /USER_LITERAL:biography -->
