# Talk Is Cheap, Show Me Your Colors: Low-Budget Consistency Auditing for Aggregated LLM Services

**Abstract**—Aggregated large language model services expose declared model identifiers while abstracting the backend configurations that fulfill client requests. We present HuePrint, a lightweight framework that audits brokered endpoint consistency via short structured color elicitation and continuous geometric distribution comparison without model weights or token probabilities. Across 34,528 cloud responses spanning 56 endpoints and 12 backends, HuePrint lowers 30-call-per-side equal error rates from 4.52–5.23 to 0.94–1.00 percent on the development cohort and from 6.25–8.04 to 3.49–5.00 percent across 20 locked endpoints, reaching zero at moderate depth. Continuous and multi-scale RGB distances halve shallow-census error vs. exact-hex divergence (5.36 vs. 10.71 percent), cut cross-provider error from 16.67 to 5.93 percent, retain zero ranking error across three-week and cross-gateway checks where equality tests reject up to 42.86 percent of genuine pairs, and bound numerical perturbations. Unified Lipschitz bounds and estimator diagnostics guide calibration: self-centering lowers clean held-out false rejections to 10 percent, and U-statistic energy ratios eliminate the 256-draw bootstrap. Within-family, mixed-routing, and canary audits below four cents median query cost inform cloud assurance guidelines.

**Index Terms**—Services computing, model-as-a-service, service-level monitoring, API brokerage, behavioral consistency, energy statistics.

---

<!-- USER_LITERAL:introduction -->
```latex
\section{Introduction}
\IEEEPARstart{A}{pplications} consuming aggregated large language model (LLM) services specify a target model identifier, while the cloud broker selects which backend instance fulfills each request~\cite{ref1,ref2}. Dynamic cascades, learned routers, and multi-provider brokers trade inference cost against latency and quality~\cite{ref1,ref2,ref3}. When a service-level agreement (SLA) commits to a pinned checkpoint or serving tier, consumers need black-box evidence that the fulfilled endpoint remains behaviorally consistent with its declared configuration---a property latency, uptime, and billing logs cannot verify.

In this paper, we introduce HuePrint, a lightweight black-box consistency signal for brokered LLM endpoints. HuePrint elicits short hexadecimal (\texttt{\#RRGGBB}) or decimal RGB responses across multilingual prompts and compares their empirical distributions against an enrolled reference, requiring no model weights, hidden activations, or honest log-probabilities. Prior audits reveal statistical discrepancies across commercial endpoints~\cite{ref4} and motivate separating backend substitutions from benign serving nondeterminism~\cite{ref5,ref6}; rather than replacing functional benchmarks, it acts as a low-cost canary whose threshold crossings trigger targeted SLA investigation.

Two principles underpin HuePrint. First, \emph{structured RGB elicitation} pairs compact coordinates with multilingual semantic priors: at 30 calls/side ($K=10$), clean equal error rates (EERs) drop from 4.52\%--5.23\% for a single-word battery~\cite{ref7} to 0.94\%--1.00\% on development models and from 6.25\%--8.04\% to 3.49\%--5.00\% across 20 locked endpoints (0.00\% at deeper budgets). Second, \emph{continuous geometric and multi-scale comparison} improves resolution and drift tolerance: $\Dereg{}$ halves shallow 56-endpoint EER vs.\ exact-hex JSD (5.36\% vs.\ 10.71\%), $\Dhyb{}$ cuts cross-provider EER from 16.67\% to 5.93\%, score-based color auditing retains 0.00\% EER across Cloudflare/OpenRouter snapshots three weeks apart (where equality tests reject up to 42.86\% of genuine pairs), and RGB geometry bounds coordinate shifts.

This paper makes three contributions to cloud LLM service assurance:
\begin{itemize}
    \item \textbf{End-to-end MaaS consistency protocol:} We formulate versioned audit contracts connecting reference enrollment, budgeted structured probing, frozen threshold calibration, and reference refresh across 34,528 live cloud responses (Datasets A--E and Studies S1--S4).
    \item \textbf{Perturbation and finite-sample estimator analysis:} We characterize discrete JSD support escape, soft-voxel and regularized-energy perturbation sensitivity, and finite-sample V-statistic bias versus zero-bootstrap U-statistic ratios and enrollment self-centering.
    \item \textbf{Operational characterization across cloud backends:} We evaluate 56 endpoints, 12 pinned third-party serving stacks, within-family model alternatives, fractional fallback routing curves, schema-constrained CSS/JSON canary prompts, and per-audit monetary cost and wall-clock latency overheads across deployment tiers.
\end{itemize}
```
<!-- /USER_LITERAL:introduction -->

## 2. Related Work and Service Model

<!-- USER_LITERAL:related_work_first_two -->
```latex
\subsection{Cloud Service Assurance and LLM Brokerage}
\textbf{SLA governance and brokered routing.} FrugalGPT~\cite{ref1} and RouteLLM~\cite{ref2} optimize provider-side cost--quality tradeoffs via model cascades and learned routers, while QoS-aware LLM brokering~\cite{ref3} pairs SLA-constrained routing with CUSUM drift tracking. In multi-tenant cloud brokerage, however, consumers lack visibility into provider dispatch tables and require independent, low-budget active probing (canary testing) to verify that fulfilled endpoints honor pinned-checkpoint SLA commitments rather than silently substituting cheaper tiers.

\textbf{Service testing and sequential drift monitoring.} Services computing research addresses cloud API reliability from complementary layers, including LLM-guided REST API fuzzing (RESTLess~\cite{ref8}), multi-modal microservice anomaly detection (UAC-AD~\cite{ref9}), and concept-drift-triggered edge rejuvenation~\cite{ref10}. Whereas white-box telemetry and functional fuzzers inspect host metrics or schema faults, HuePrint provides an external, black-box distributional audit over standard chat completions that separates benign serving drift from unauthorized backend changes.
```
<!-- /USER_LITERAL:related_work_first_two -->

**Model and API auditing.** Provider-side watermarks, instructional backdoors, and IP ownership fingerprints [11]–[13] require provider or owner intervention, or target model-theft disputes rather than live endpoint monitoring. Passive attribution [14], [15] needs long outputs, while active probes (LLMmap [16], TRAP [17]) classify closed-set versions in roughly eight multi-token queries via distinctive prompts rather than tracking continuous reference drift. Gao et al. [4] test full-output equality; Zhu et al. [6] require white-box reference probabilities. Biased random priors [18], [19], [20], [21] motivate short probes despite shared-component correlations [22], [23]. Bruckner [7] applies JSD across 40 word prompts (7.3% EER over 165 models); HuePrint evaluates a structured color protocol under matched call budgets and isolates continuous versus discrete comparison on shared color responses.

<!-- USER_LITERAL:service_model -->
```latex
\subsection{Service Aggregation Architecture and Audit Contract}
\textbf{Roles and observables.} A consumer-side monitor enrolls a declared checkpoint $M^*$ via a trusted reference endpoint $E_{\mathrm{ref}}(M^*)$ and audits a brokered endpoint $E$ over $k$ task--language cells with $n_B$ completions per cell ($n=|U|, m=|V|$ valid parses; Fig.~1). Gateways such as Cloudflare AI Gateway and OpenRouter serve as observable routing paths under standard chat-completion access, without requiring model weights, hidden states, log-probabilities, or server-side seed control.

\textbf{Audit contract and deployment confounders.} An audit contract binds the reference profile, prompt battery, sampling budget, parser, and frozen threshold version to a pinned-checkpoint SLA commitment, rather than a declared complexity-cascaded router~\cite{ref1,ref2} whose lightweight branch legally serves short prompts. Checkpoint consistency and precision-tier consistency are evaluated as distinct objectives, providing behavioral evidence alongside QoS telemetry rather than cryptographic weight proof. Two gateway mechanisms require explicit operational handling: response or semantic caching collapses stochastic draws at $T=1.0$ (screened via zero output entropy paired with sub-median latency), and broker-injected system prompts shift conditional color priors unless enrollment is performed through the same gateway wrapper.

\textbf{Service-change scenarios and lifecycle.} We evaluate four scenarios: (1) full checkpoint substitution behind a fixed model identifier; (2) low-bit precision execution under an unchanged label; (3) probabilistic request-level fallback mixing declared and substitute backends; and (4) response reuse via lookup or histogram resampling from a public gallery. Scores below a frozen threshold $\tau$ yield \emph{accept}, whereas crossings trigger \emph{investigate} (or two-stage confirmation) and authorized updates initiate reference refresh.
```
<!-- /USER_LITERAL:service_model -->

![Consumer-side audit lifecycle for a brokered LLM service. Enrollment and protocol-matched probes feed a frozen consistency decision; configuration changes require investigation and reference refresh.](../figs/fig1_service_audit.pdf)

## 3. Methodology and Perturbation Analysis

### 3.1 Probes, Parsing, and RGB Coordinates

The battery crosses 10 tasks with four languages (en, zh, ru, ar) for 40 task-language cells requesting random, favorite, warm, nature, ocean, calm, and night colors in hex (`#RRGGBB`) and RGB syntax (Fig. 2; e.g., *"Pick a random color. Reply with only its #RRGGBB hex code."*). Study S4 embeds color choices inside 1-line CSS custom properties (e.g., `--brand-primary`) and 1-field JSON design tokens; Supplements C–F give complete inventories and verbatim prompts. After stripping reasoning fields and inline tags, the parser extracts the first valid `#RRGGBB` code or validated $0\text{--}255$ RGB triplet (retaining canonical uppercase `#RRGGBB`, coordinates, syntax, and a strict-only-color flag) and marks failures invalid.

For an sRGB code $\mathbf c\in\Omega=\{0,\ldots,255\}^3$ [24], let $\mathbf x=T(\mathbf c)=100\mathbf c/255\in\Omega_{\mathrm{RGB}}=[0,100]^3$; clipped perturbations $\mathbf c'=\operatorname{clip}_{[0,255]^3}(\mathbf c+\boldsymbol\eta)$ with $\|\boldsymbol\eta\|_\infty\le a$ satisfy $\|T(\mathbf c')-T(\mathbf c)\|_2\le 100\sqrt3 a/255$. RGB100 linearly rescales channels (without gamma inversion or Lab conversion) and underpins all continuous scores, whereas hard/soft voxels use raw channel units. Supplement A analyzes injective and Lipschitz color charts and Supplement B ablates fixed-weight regularization.

![Five deterministically selected family representatives on the random-color probe. Marker area denotes output frequency and fill denotes actual RGB; the two projections show (R, G) and (B, G). Word probabilities use the matched endpoints and random-color word probe.](../figs/fig2_rgb_geometry_vs_words.pdf)

### 3.2 Discrete JSD and Support Escape

With $M=(P+Q)/2$, base-2 JSD [25] is
$$D_{\mathrm{JSD}}(P\|Q)=\tfrac12\sum_xP(x)\log_2\frac{P(x)}{M(x)}+\tfrac12\sum_xQ(x)\log_2\frac{Q(x)}{M(x)},$$
omitting zero-mass terms; it satisfies $0\le D_{\mathrm{JSD}}(P\|Q)\le 1$, equaling $1$ iff $\operatorname{supp}(P)\cap\operatorname{supp}(Q)=\emptyset$. $D_{\mathrm{hex}}$ uses exact RGB codes; $D_{\mathrm{vox}}$ uses $(\lfloor R/32\rfloor,\lfloor G/32\rfloor,\lfloor B/32\rfloor)$, giving $256^3$ and $8^3$ categories, respectively.

**Proposition 1 (Support-escape lower bound).** *Fix a reference empirical distribution $P_{\mathrm{ref}}$ with support size $r$, and let $Q^{\mathrm{jitter}}$ draw source colors $\mathbf c\sim P_{\mathrm{src}}$ perturbed by independent uniform integer noise on $\{-a,\ldots,a\}^3$ ($a\ge1$) under the clipped transformation above. For $n$ i.i.d. draws $\hat Q_n^{\mathrm{jitter}}\sim Q^{\mathrm{jitter}}$ with support-escape probability $Q^{\mathrm{jitter}}(\Omega\setminus\operatorname{supp}(P_{\mathrm{ref}}))\ge t\in[0,1]$,*
$$\mathbb E[D_{\mathrm{hex}}(P_{\mathrm{ref}},\hat Q_n^{\mathrm{jitter}})]\ge D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})\ge\psi(t),$$
$$\psi(t)=\tfrac12\log_2\frac2{2-t}+\tfrac{1-t}{2}\log_2\frac{2(1-t)}{2-t}+\tfrac t2\ge\tfrac t2,$$
*where $\psi$ is strictly increasing with $\psi(1)=1$ by continuity, and the population bound is tight. When $\operatorname{supp}(P_{\mathrm{src}})\subseteq\{a,\ldots,255-a\}^3$, one may take $t=\max(0,1-r/(2a+1)^3)$.*

<!-- USER_LITERAL:support_escape -->
```latex
Conditioning on observed query colors per cell and adding one random clipped shift per draw, Fig.~3(a) evaluates Eq.~(1) via the empirical query histogram's escape probability. Proposition~1 explains why genuine $D_{\mathrm{hex}}$ scores saturate toward $1$ under small channel shifts while empirical EER depends jointly on the impostor distribution (Fig.~3(c)); Supplement~G proves Propositions~1--2 and Lemma~1.
```
<!-- /USER_LITERAL:support_escape -->

### 3.3 Soft Voxels and Regularized Energy

With $w=48$ in original channel units and nodes $\mathcal I=\{0,\ldots,6\}^3$, define
$$W_i(\mathbf c)=\prod_{d\in\{R,G,B\}}\max(0,1-|c_d/w-i_d|),\qquad P_{\mathrm{soft}}(i\mid S)=|S|^{-1}\sum_{\mathbf c\in S}W_i(\mathbf c).$$
Since $255/w=5.3125<6$, the trilinear tent weights satisfy $W_i(\mathbf c)\ge 0$ and $\sum_{i\in\mathcal I}W_i(\mathbf c)=1$ on $[0,255]^3$, so $P_{\mathrm{soft}}(\cdot\mid S)$ in Eq. (2) is a valid probability vector and $D_{\mathrm{svox}}$ is the JSD between two soft histograms.

**Lemma 1 (Soft-voxel stability).** *For $\mathbf c,\mathbf c'\in[0,255]^3$, $\|W(\mathbf c)-W(\mathbf c')\|_1\le(2/w)\|\mathbf c-\mathbf c'\|_1\le(6/w)\|\mathbf c-\mathbf c'\|_\infty$, so paired samples $S,S'$ shifted by at most $a$ per channel satisfy $D_{\mathrm{JSD}}(P_{\mathrm{soft}}(S)\|P_{\mathrm{soft}}(S'))\le b$ with $b=\min(1,3a/w)$.*

Fig. 3(b) plots this query-to-perturbed-query term $D_{\mathrm{JSD}}(P_{\mathrm{soft}}(S)\|P_{\mathrm{soft}}(S'))$. Against a fixed reference $P_{\mathrm{ref}}$, metric triangle inequality on $\sqrt{D_{\mathrm{JSD}}}$ gives $|\Delta\sqrt{D_{\mathrm{svox}}}|\le\sqrt b$ and raw-score shift $|\Delta D_{\mathrm{svox}}|\le\min(1,2\sqrt b)$; decision flips also depend on the score's margin to $\tau$.

For nonempty RGB100 clouds $U,V$, let $n=|U|$, $m=|V|$ and
$$d_{UV}=\frac{\sum_{i,j}\|u_i-v_j\|_2}{nm},\qquad d_{UU}=\frac{\sum_{i,i'}\|u_i-u_{i'}\|_2}{n^2},$$
with $d_{VV}$ defined analogously, including diagonals. The V-statistic squared energy is $\widehat{\mathcal E}_V^2=2d_{UV}-d_{UU}-d_{VV}$. For distributions on $\mathbb R^3$ with finite first moments, population squared energy satisfies $\mathcal E^2(\mu,\nu)\ge 0$ with equality iff $\mu=\nu$ [26], [27]; applied to empirical measures, $0\le\widehat{\mathcal E}_V^2\le 2d_{UV}$. We therefore define
$$\bar D_{\mathrm E}=\frac{\widehat{\mathcal E}_V^2}{2d_{UV}},\qquad\tilde D_{\mathrm{E-reg}}=\frac{\widehat{\mathcal E}_V^2}{2d_{UV}+2\delta_0},$$
where $\delta_0=15$ RGB100 length units in Eq. (3) and $\bar D_{\mathrm E}=0$ at $d_{UV}=0$. Floating-point evaluation clips $[\widehat{\mathcal E}_V^2]_+=\max(0,\widehat{\mathcal E}_V^2)$ to $[0,2d_{UV}]$ and sets scores to zero when $d_{UV}<10^{-12}$. For constant clouds separated by $\epsilon>0$ ($d_{UU}=d_{VV}=0, d_{UV}=\epsilon$), $\bar D_{\mathrm E}$ jumps from $0$ at $\epsilon=0$ to $1$, whereas $\tilde D_{\mathrm{E-reg}}=\epsilon/(\epsilon+\delta_0)\le\epsilon/\delta_0$ varies smoothly.

**Proposition 2 (Lipschitz stability of regularized energy ratios).** *For nonempty $U,V\subset\mathbb R^3$, $\delta_0>0$, $d=d_{UV}$, and within-cloud mean distance average $h$ computed with diagonals ($\tilde D_{\mathrm{E-reg}}$) or without diagonals ($|U|,|V|\ge 2$, Section 3.7), let $F(d,h)=(d-h)/(d+\delta_0)$. Moving each point of $V$ by at most $\epsilon$ in Euclidean norm (in arbitrary directions) changes $F(d,h)$ and $[F(d,h)]_+$ by at most $2\epsilon/\delta_0$; moving every point of $U$ and $V$ by at most $\epsilon$ changes them by at most $4\epsilon/\delta_0$.*

<!-- USER_LITERAL:energy_corollary -->
```latex
For clipped ratios in $[0,1)$, channel shift $a$ bounds one-sided change by $\min\{1, 200\sqrt{3}a/(255\delta_0)\}$ ($0.0906$ at $a=1$, $0.7245$ at $a=8$ for $\delta_0=15$), ensuring continuity as $d_{UV}\to 0$. Proposition~2 permits arbitrary per-point worst-case directions, whereas uncoordinated uniform jitter in Fig.~3(b) stays far below this envelope.
```
<!-- /USER_LITERAL:energy_corollary -->

The Gaussian Bures–Wasserstein control [28] fits biased covariances with ridge $10^{-3}I$ in squared RGB100 units and uses $D_{W_2}=1-e^{-W_2/50}$ with a 50-unit RGB100 length scale. Unlike energy, matching two moments cannot distinguish all distributions; Supplement G gives its formula and limitations.

![Ten fixed jitter seeds per radius. (a) Exact JSD and its clipping-aware conditional expected lower bound. (b) Energy score change and query-to-perturbed-query soft JSD with their respective upper bounds. (c) Re-swept linear EER; inset shows energy regularization sensitivity.](../figs/fig3_stability_bounds.pdf)

### 3.4 Composite Scores and Decisions

$D_{\mathrm{side}}$ averages JSD over syntax (case/prefix or comma spacing), available first reasoning words, and log-binned reasoning lengths. Because hex case tags distinguish all-digit codes (`numeric_only`, $5.96\%$ of RGB) and reasoning lengths read API `usage.reasoning_tokens` when returned before falling back to visible character counts, $D_{\mathrm{side}}$ serves as an auxiliary syntax/envelope channel rather than a color-free or envelope-free invariant (pure-content ablations in Supplement B). Fixed composites—including the regularized multi-scale composite $D_{\mathrm{RM}}$—are
$$\begin{aligned}D_{\mathrm{hyb}}&=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}+0.25\bar D_{\mathrm E}+0.15D_{\mathrm{side}},\\D_{\mathrm{hyb-reg}}&=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}+0.25\tilde D_{\mathrm{E-reg}}+0.15D_{\mathrm{side}},\\D_{\mathrm{RM}}&=0.50D_{\mathrm{svox}}+0.50\tilde D_{\mathrm{E-reg}}.\end{aligned}$$
In Eq. (4), scores average shared eligible cells and accept at $S\le\tau$. Development genuine/impostor scores $G,I$ define $\tau_{\mathrm{mid}}=(\max G+\min I)/2$ and $\tau_{\mathrm{u0}}=\operatorname{nextafter}(\min I,-\infty)$ (zero FAR is guaranteed only on development negatives). AUC gives ties half weight, linear EER interpolates adjacent ROC points under re-swept thresholds, and frozen FAR/FRR evaluate deployment cutoffs.

### 3.5 Enrollment Calibration and Equality Testing

For each reference and cell, we bootstrap two enrollment-only clouds matching reference and planned query sizes across 256 fixed-seed draws, average across eligible cells to obtain $\mu_{\mathrm{self}}$ (using zero query data or test labels), and set $\Delta_D=D-\alpha\mu_{\mathrm{self}}$. Under IID enrollment sampling of size $n$, resampling $\hat P_n$ collides with probability $1/n$, scaling enrollment-expected empirical within-sample mean distance—and thus the null bootstrap's expected unnormalized V-numerator—by $(n-1)/n$ (whereas normalized $\tilde D_{\mathrm{E-reg}}$ mean ratios $\overline{\mu}_{\mathrm{self}}/\overline{G}=0.732$ on B3v3 and $0.598$ on E reflect ratio normalization rather than verifying $(n-1)/n$). We compare raw scores, $\alpha=1$, and B-only leave-one-model-out selection over $\{0,0.25,0.5,1,1.5,2\}$ (breaking zero-error ties on B6v6/B8v7 toward $\alpha=1$). Protocol-specific B splits fit frozen thresholds: B3v3 (odd/even of six draws, 20 cells; used on E), B6v6 (first vs. next six draws, 20 cells; matched S1 check), and B8v7 (15 draws, 40 cells; min-5 valid per half for verification, min-1 for service-change calibration).

Adapting the two-sample energy test [27] to stratified cells, we average $nm\widehat{\mathcal E}_V^2/(n+m)$ across cells over 999 within-cell label permutations with $p=(1+\#\{T_b\ge T_{\mathrm{obs}}\})/1000$; $p\le0.05$ rejects equal conditional valid-color distributions (pairwise rates are unadjusted and correlated across shared endpoints).

### 3.6 Completion Baselines and Matched Budgets

Adapting Gao et al.'s one-hot MMD and $L_1$ tests [4] to raw strings (preserving whitespace, case, and invalid outputs, with empirical TV equal to $\tfrac12 L_1$), we evaluate $n,m\ge2$ with $k(s,t)=\mathbf1[s=t]$ via
$$\widehat{\mathrm{MMD}}_u^2=\frac{\sum_{i\ne i'}k(x_i,x_{i'})}{n(n-1)}+\frac{\sum_{j\ne j'}k(y_j,y_{j'})}{m(m-1)}-\frac{2\sum_{i,j}k(x_i,y_j)}{nm},$$
averaging per-cell statistics (exact rational MMD-U) over 999 permutations while separating statistic EER/AUC from rejection rates. Invalid parses still consume call budgets. S3 tests $N\in\{6,10,20,30\}$ ($n=m=N/2$) across up to 40 shared $K$-cell subsets ($K=1,\ldots,10$; B-20×6/D test $N=6$), and ten fixed seeds perturb parsed RGB literals in memory.

### 3.7 Finite-Sample Energy Estimators

For independent IID samples of sizes $n,m$ ($a_P=\mathbb E\|X-X'\|$, $a_Q=\mathbb E\|Y-Y'\|$), the nonnegative V numerator satisfies $\mathbb E[\widehat{\mathcal E}_V^2]=\mathcal E^2(P,Q)+a_P/n+a_Q/m$. For $n,m\ge2$, the U numerator
$$\widehat{\mathcal E}_U^2=2d_{UV}-\frac{n}{n-1}d_{UU}-\frac{m}{m-1}d_{VV}$$
lies in $[-2d_{UV},2d_{UV}]$, may be negative, and is unbiased for $\mathcal E^2(P,Q)$ under independent IID sampling. Against $\tilde D_{\mathrm{E-reg}}$ (*V regularized*) and centered $\tilde D_{\mathrm{E-reg}}$ (*V self-centered*), Table 7 compares $\widehat{\mathcal E}_U^2$ (*U numerator*), $\widehat{\mathcal E}_U^2/(2d_{UV}+2\delta_0)$ (*U signed ratio*), and $[\widehat{\mathcal E}_U^2]_+/(2d_{UV}+2\delta_0)$ (*U clipped ratio*, strictly in $[0,1)$ since $\delta_0>0$, leaving $\min\{1,\cdot\}$ inactive). Neither random-denominator normalization nor clipping preserves unbiasedness; Proposition 2 gives both U ratios $2\epsilon/\delta_0$ one-sided and $4\epsilon/\delta_0$ two-sided bounds.

<!-- USER_LITERAL:u_final -->
```latex
All U-statistic variants and matched V-statistic controls are evaluated over identical cells containing at least two valid responses per side.
```
<!-- /USER_LITERAL:u_final -->

---

## 4. Experimental Design and Dataset Architecture

### 4.1 Datasets and Reproducibility Architecture

Five baseline datasets (A–E, Oct. 2026; 11,888 unique calls) and four online studies (S1–S4, Nov. 2026; 22,640 calls) provide **34,528** unique cloud responses (Table 1), backed by read-only JSONL logs, deduplication rules, SHA-256 input manifests, fixed seeds, and offline analysis/plotting scripts.

**TABLE 1: Cloud Response Datasets**

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

**Table note:** B: 5,520 unique calls + 480 A rows (6,000). Three of 12,000 S3 responses reached the length limit (two color, one word; one valid).

### 4.2 Decoding Hyperparameters and Temperature Handling Across Modern APIs

Requests disable optional thinking where supported and set completion caps of 16–256 tokens (locked at 64 in S2/S3 and 128 in S4; Supplement K). Datasets A–C omit explicit temperature (`temperature_sent=null`); D, E, and `S1_CF21` pass `temperature=1.0` only on direct Workers AI calls (1–2 endpoints); and `S1_OR21`, S2, S3, and S4 send `temperature=1.0` uniformly (with recorded stripping shared across paired requests on two S3 Claude endpoints). In S1, `OR21` sets `reasoning.effort="low"` on five reasoning endpoints, and Cloudflare maps `llama-3.3-70b-fp8-fast` to a speculative-decoding (`-sd`) variant absent on OpenRouter. Whereas S2 disables provider fallbacks (`0/18` mixed), OpenRouter load-balances 5/14 `S1_OR21`, 7/20 S3, and 5–6/20 S4 endpoints across sub-providers (S3 odd/even sub-provider TV mean 0.0419, max 0.1200). In A, 144 records expose reasoning summaries without raw text, and in S3 sub-provider `GMICloud` (`s3-deepseek-v3.2`, 158/300 calls) ignored thinking suppression and billed up to 907 output tokens; parsing strips reasoning traces while overhead accounting retains all billed tokens.

---

## 5. Empirical Evaluation: Baseline and Live External-Validity Studies

### 5.1 56-Endpoint Census and Formatting Side-Channel Ablation (Dataset A)

On Dataset A (56 endpoints across 11 families, 8 cells $\times$ 6 repetitions, 3v3 split with $\ge 2$ valid responses per half), we evaluate 56 genuine pairs against 3,080 all-pairs, 2,958 cross-sublineage, and 2,476 cross-vendor-family impostors, plus leave-one-out 1-NN family attribution over 50 multi-member-family models (Table 2).

**TABLE 2: Dataset A (56 Models, $8\times 6$ Shallow Budget) Verification and Family Attribution**

<!-- RGB_TABLE_2 -->
| Metric | AUC | Discrete / linear EER | Cross-sublineage linear EER | Cross-family linear EER | LOO family attribution |
| --- | --- | --- | --- | --- | --- |
| $\bar D_{\mathrm E}$ | 0.9900 | 5.06% / 4.77% | 3.75% | 3.57% | 31/50 (62.00%) |
| $\tilde D_{\mathrm{E-reg}}$ | 0.9872 | 5.36% / 5.36% | 5.36% | 4.52% | 35/50 (70.00%) |
| $D_{\mathrm{hyb}}$ | 0.9774 | 7.14% / 7.14% | 7.14% | 7.14% | 36/50 (72.00%) |
| $D_{\mathrm{hex}}$ | 0.9588 | 10.73% / 10.71% | 10.71% | 8.93% | 38/50 (76.00%) |
| $D_{\mathrm{RM}}$ | 0.9582 | 8.93% / 8.93% | 8.93% | 8.93% | 34/50 (68.00%) |
| $D_{\mathrm{vox}}$ | 0.9489 | 8.83% / 8.93% | 8.93% | 8.93% | 39/50 (78.00%) |
| $D_{\mathrm{side}}$ | 0.7804 | 30.32% / 30.32% | 29.76% | 28.56% | 17/50 (34.00%) |
<!-- /RGB_TABLE_2 -->

**Table note:** Archived `evaluate_cohort`/`within` requires $\ge 2$ valid parses in both halves per endpoint before pairing; side-independent filtering ($\ge 2$ enrollment parses for $i$, $\ge 2$ query parses for $j$, intersected) alters 163/3,080 negatives (0/56 genuine), giving 4.16% vs. 4.77% linear EER for $\bar D_{\mathrm E}$ and unchanged 5.36% for $\tilde D_{\mathrm{E-reg}}$ (`scripts/sensitivity_checks.py`).

Continuous distances lead binary verification in Table 2, whereas family attribution favors categorical retention (39/50 under $D_{\mathrm{vox}}$ vs. 35/50 under $\tilde D_{\mathrm{E-reg}}$). Merging `numeric_only` hex tags into `upper` and stripping API reasoning telemetry lowers $D_{\mathrm{side}}$ AUC/EER from 0.7804/30.32% to 0.6557/36.76% on A and from 0.9722/10.00% to 0.6933/36.00% on B (Supplement B; relaxing valid-cell eligibility from $\ge 2$ to $\ge 1$ for thinking-truncated `gw-gemini-2.5-flash` gives 5.62% $\bar D_{\mathrm E}$ and unchanged 5.36% $\tilde D_{\mathrm{E-reg}}$ EER).

---

### 5.2 Query-Budget Scaling and $(n, k)$ Grid Ablation (Dataset B)

Increasing B to 40 cells and 15 repetitions yields AUC 1.0000 and 0.00% discrete and linear EER for all six nonparametric color metrics, while Gaussian $D_{W_2}$ retains 2.22% linear EER (1.11% discrete EER, 0.9978 AUC), reflecting the two-moment information loss noted in Section 3.3. The budget grid in Fig. 4(a) shows how coverage and depth interact: 60 draws at $(n=15,k=4)$ give mean linear EER 1.78%, whereas 96 draws at $(n=6,k=16)$ give 0.46%.


---

![(a) Mean $D_{\mathrm{hyb}}$ linear EER over the B sampling-budget grid. (b) Genuine and impostor regularized-energy scores across B ($20\times 6$, 3v3), E ($20\times 6$, 3v3), and S1 paths ($20\times 6$, 6v6), with frozen B3v3 ($\tau=0.148$, dashed) and budget-matched B6v6 ($\tau=0.113$, dotted) midpoint thresholds.](../figs/fig4_budget_and_drift.pdf)

<!-- USER_LITERAL:paraphrase -->
```latex
\subsection{Within-Pool Self-Verification vs.\ Cross-Template Shift (Dataset C)}
Dataset C evaluates two paraphrase pools across eight bilingual cells (eight repetitions per cell): syntactic rewording $P_1$ and design-contextual framing $P_2$ (detailed per-metric results in Supplement~I). Regularized energy $\Dereg{}$ achieves 0.00\% and 1.11\% linear EER within $P_1$ and $P_2$, respectively, whereas cross-template comparisons $P_0 \rightarrow P_1$ and $P_0 \rightarrow P_2$ yield 17.78\% and 11.11\% EER. Because even synonymous phrasing shifts conditional color priors, reference profiles must remain conditioned on the exact prompt battery.
```
<!-- /USER_LITERAL:paraphrase -->

### 5.4 Matched Probe and Statistic Comparisons (Dataset D and Study S3)

**Structured color elicitation.** Averaging 40 overlapping 10-cell subsets ($K=10$, three draws/cell/side, 30 calls/side) across the 10 development models on B-20×6 and D yields clean EERs of 0.94% (Color MMD-U) and 1.00% ($\tilde D_{\mathrm{E-reg}}$) vs. 4.52% (Word MMD-U) and 5.23% (Word JSD), reaching 0.00% at $K=20$ (60 calls/side; 1.11% Word JSD; Supplement K) with 18.65 vs. 7.05 distinct valid outputs/cell (111,305 vs. 79,398 tokens; $\pm8$ jitter EER at $K=10$: 49.73% vs. 1.59%). Because D also queries animals, cities, numbers, letters, and coins, full-battery gaps reflect joint prompt-and-coordinate efficiency. S3 tests 20 models (8 families, 10 English probes, 15v15, cap 64; Table 3), parsing 99.97% color (5,998/6,000) and 99.78% word (5,987/6,000) calls; on S3's two shared color-concept tasks under raw-string MMD-U (`hex_random`, `hex_favorite` vs. `brk_rand_color`, `brk_fav_color`; Supplement K), hex coordinates raise 3v3/15v15 AUC from 0.8349/0.9784 to 0.9156/0.9909 (17.92% vs. 20.21% and 5.26% vs. 5.00% EER) while enabling 3D continuous distances.

**TABLE 3: S3 Matched-Budget Raw-Statistic Linear EER; Final Column Averages Ten RGB Jitter Seeds**

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

**Continuous RGB comparison.** On S3 ($K=10$), $N=6$ yields 3.49% (Color MMD-U) and 5.00% ($\tilde D_{\mathrm{E-reg}}$) versus 8.04% (Word MMD-U), 6.25% (Word JSD), and 10.00% exact-hex $D_{\mathrm{hex}}$ (empirical), and canonical `#RRGGBB` versus normalized-word MMD-U keeps this gain (5.00% vs. 9.31% at $N=6$; 0.00% vs. 0.53% at $N=30$). At $N=30$, Color MMD-U and $\tilde D_{\mathrm{E-reg}}$ reach 0.00% clean EER (1.0000 AUC) versus 1.32% (Word MMD-U) and 5.00% ($D_{\mathrm{hex}}$, Color TV, Word JSD); under controlled $\pm8$ jitter, Color MMD-U/TV/$D_{\mathrm{hex}}$ degrade to 50.00%/35.99%/35.40% (0.5184 MMD-U AUC) while energy holds 0.00% (Fig. 5). At $p\le0.05$, Color MMD-U rejects 10.00% genuine and 100.00% impostor pairs cleanly, rising to 100.00% under jitter (Sections 3.5–3.6).

![(a) S3 EER for string MMD and regularized energy on the same color responses across budgets. (b) Held-out E same-model rejection: raw and centered frozen rules, and per-audit energy permutation testing at $p\le0.05$. FAR is zero throughout; jitter results average ten fixed seeds.](../figs/fig5_geometry_and_calibration.pdf)


<!-- USER_LITERAL:rgb_modes -->
```latex
\textbf{RGB output modes.} In S3, exact CSS named colors account for 14.25\% of unanchored, 49.29\% of semantic, and 64.89\% of preference responses, while repeated-nibble codes constitute 23.85\% of preference responses. Familiar color literals and structured encoding habits thus form distinct behavioral modes shaped by pre-training exposure to frontend code and stylesheets (Fig.~2), concentrating mass onto model-specific regions of $\Omega_{\mathrm{RGB}}$.
```
<!-- /USER_LITERAL:rgb_modes -->

<!-- USER_LITERAL:s1_main -->
```latex
\subsection{Held-Out, Longitudinal, and Gateway Transfer (Dataset E and Study S1)}
\textbf{Held-out transfer.} Dataset E comprises 10 models absent from B, collected a median 6.74~h after A. Transferring frozen B3v3 cutoffs yields E FRR/FAR of 10.00\%/0.00\% for $\Dhyb{}$ ($\tau = 0.348407$) and 30.00\%/0.00\% for raw $\Dereg{}$ ($\tau = 0.148017$, re-swept EER 10.00\%).

\textbf{Longitudinal and cross-gateway audit (S1).} Across two observations $21.07\text{--}21.32$~d apart (median 21.32~d), we re-audited 14 provider-declared endpoints---B's 10 development models (\texttt{CF0} shares 1,200 enrollment rows with B calibration) plus four held-out E models (\texttt{heldout4}, disjoint from B; Section~5.7)---on Cloudflare AI Gateway (CF) and OpenRouter (OR) over 20 bilingual cells $\times$ 6 draws (3,360 calls; 99.23\% and 99.46\% valid). Table~4 evaluates 6v6 scores under frozen B3v3 (budget-matched B6v6 appears in Table~5, where raw $\mathrm{CF0}\rightarrow\mathrm{OR21}$ rejects \texttt{cf-qwen2.5-coder-32b}, giving 1/4 = 25.00\% raw \texttt{heldout4} FRR vs.\ 0.00\% centered). Against all 13 non-self models ($4\times 13 = 52$ open-set impostors vs.\ 12 within-slice), raw B3v3 yields 1/52 (1.92\%) FAR on $\mathrm{CF0}\rightarrow\mathrm{CF21}$ (\texttt{gw-gpt-4.1}$\rightarrow$\texttt{gw-gpt-4o}, score $0.1336$) and 0.00\% centered or under B6v6.

\begin{table*}[t]
\centering
\caption{Study S1 Longitudinal ($T+21.32\text{d}$) and Cloudflare $\leftrightarrow$ OpenRouter Cross-Gateway Verification (14 Genuine vs.\ 182 Impostors)}
\label{tab:s1_transfer}
\footnotesize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.05}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llccccc@{}}
\toprule
Enrollment $\rightarrow$ Query (6v6) & Metric & Top-1 & AUC & Linear EER & Genuine /\allowbreak{} Impostor Mean & Frozen B3v3 FRR /\allowbreak{} FAR \\
\midrule
$\mathrm{CF0} \rightarrow \mathrm{CF21}$ & $\Drm{}$ & 14/14 & 1.0000 & 0.00\% & 0.0728 /\allowbreak{} 0.3544 & 0.00\% /\allowbreak{} 1.10\% \\
$\mathrm{CF0} \rightarrow \mathrm{CF21}$ & $\Dereg{}$ & 14/14 & 1.0000 & 0.00\% & 0.0511 /\allowbreak{} 0.2690 & 0.00\% /\allowbreak{} 2.20\% \\
$\mathrm{CF0} \rightarrow \mathrm{CF21}$ & $\Dhyb{}$ & 14/14 & 1.0000 & 0.00\% & 0.1600 /\allowbreak{} 0.5348 & 0.00\% /\allowbreak{} 0.55\% \\
$\mathrm{CF0} \rightarrow \mathrm{CF21}$ (heldout4) & $\Dereg{}$ & 4/4 & 1.0000 & 0.00\% & 0.0599 /\allowbreak{} 0.2989 & 0.00\% /\allowbreak{} 0.00\% \\
$\mathrm{CF0} \rightarrow \mathrm{CF21}$ (heldout4) & $\Dhyb{}$ & 4/4 & 1.0000 & 0.00\% & 0.1790 /\allowbreak{} 0.5721 & 0.00\% /\allowbreak{} 0.00\% \\
$\mathrm{CF21} \rightarrow \mathrm{OR21}$ & $\Drm{}$ & 14/14 & 1.0000 & 0.00\% & 0.0864 /\allowbreak{} 0.3613 & 0.00\% /\allowbreak{} 0.00\% \\
$\mathrm{CF21} \rightarrow \mathrm{OR21}$ & $\Dereg{}$ & 14/14 & 1.0000 & 0.00\% & 0.0619 /\allowbreak{} 0.2809 & 0.00\% /\allowbreak{} 0.55\% \\
$\mathrm{CF21} \rightarrow \mathrm{OR21}$ & $\Dhyb{}$ & 14/14 & 1.0000 & 0.00\% & 0.1834 /\allowbreak{} 0.5543 & 0.00\% /\allowbreak{} 0.00\% \\
$\mathrm{CF0} \rightarrow \mathrm{OR21}$ & $\Drm{}$ & 14/14 & 1.0000 & 0.00\% & 0.0937 /\allowbreak{} 0.3642 & 0.00\% /\allowbreak{} 1.10\% \\
$\mathrm{CF0} \rightarrow \mathrm{OR21}$ & $\Dereg{}$ & 14/14 & 1.0000 & 0.00\% & 0.0697 /\allowbreak{} 0.2830 & 0.00\% /\allowbreak{} 0.00\% \\
$\mathrm{CF0} \rightarrow \mathrm{OR21}$ & $\Dhyb{}$ & 14/14 & 1.0000 & 0.00\% & 0.1960 /\allowbreak{} 0.5564 & 0.00\% /\allowbreak{} 0.00\% \\
\bottomrule
\end{tabular*}
\end{table*}
```
<!-- /USER_LITERAL:s1_main -->

**Enrollment self-dispersion calibration.** Centering $\Delta_D=D-\alpha\mu_{\mathrm{self}}$ ($\alpha=1$) sets raw/centered cutoffs to 0.148017/0.073044 on B3v3 and 0.113100/0.060830 on B6v6, cutting clean E FRR, longitudinal S1 FAR, and B8v7 50%-routing false acceptance (31.11% to 14.44%, Supplement L); because $D\le\tau_{\mathrm{self}}+\mu_{\mathrm{self}}(M^*)$ adds no query-noise slack, jittered E FRR rises (Table 5).

**TABLE 5: Frozen Regularized-Energy Transfer; Self Uses B-Selected $\alpha=1$**

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

**Ranking, frozen cutoffs, and equality testing under drift.** Stratified Székely–Rizzo testing yields 0.00% clean and 18.00% jitter FRR on E at 0.00% FAR (Fig. 5(b)). Across S1's CF0→CF21, CF21→OR21, and CF0→OR21 paths, equality tests ($p\le0.05$) reject 7.14%, 28.57%, and 42.86% of declared genuine pairs for energy and 7.14%, 21.43%, and 28.57% for Color MMD-U (100% of impostors; 22.22% and 44.44% on the nine endpoints without `reasoning.effort` overrides, Supplement K). Meanwhile, $\tilde D_{\mathrm{E-reg}}$, $D_{\mathrm{RM}}$, $D_{\mathrm{hyb}}$, and raw-string Color MMD-U all retain 0.00% EER across all 14 endpoints and subgroups alongside low frozen FAR/FRR (Tables 4–5), complementing RGB geometry's finite-sample, cross-host, and perturbation gains (Tables 2–3; Sections 5.4, 5.6, 6.1).

<!-- USER_LITERAL:s2_intro -->
```latex
\subsection{Multi-Provider Serving Stacks and Precision Configurations (Study S2)}
Study S2 audits 18 endpoints covering six open-weight checkpoints across three providers each, spanning 12 pinned cloud backends (DeepInfra, Parasail, Cloudflare, Groq LPU, SiliconFlow, AtlasCloud, Mistral, Venice, DekaLLM, Crusoe, Fireworks, and CoreWeave) with fallback disabled across all 2,160 confirmed calls. Serving regimes include matched \texttt{fp8}, Fireworks \texttt{int4} vs.\ CoreWeave \texttt{bf16}, DeepInfra \texttt{fp4} vs.\ SiliconFlow \texttt{fp8}, and Groq LPU vs.\ GPU \texttt{fp8} (Supplement~J).
```
<!-- /USER_LITERAL:s2_intro -->

Treating same-checkpoint cross-provider pairs as positives and high-to-low-bit queries as anomalies (LPU/official unspecified), the four high-to-low-bit pairs vs. 20 high-precision controls yield 0.8250/30.00% AUC/EER for $D_{\mathrm{hyb}}$ and 0.5250/50.00% for $\tilde D_{\mathrm{E-reg}}$, reflecting backend tolerance versus precision shift. Across S2 providers (20 cells, 6v6), $D_{\mathrm{hyb}}$ reaches 5.93% EER (17/18 group matches) versus 16.67% (16/18) for $\tilde D_{\mathrm{E-reg}}$ and 16.67% for Color MMD-U (3v3: 19.78%; at $p\le0.05$, MMD-U rejects 41.67% genuine and 100.00% impostor pairs), favoring $D_{\mathrm{hyb}}$ across hosts.

<!-- USER_LITERAL:uncertainty -->
```latex
\subsection{Hyperparameter Sensitivity and Uncertainty}
Without retuning, all tested settings preserve 0.00\% EER on B, while E EER spans 0.00\%--10.00\% for $\Dereg{}$ across $\delta_0 \in \{2, 5, 10, 15, 25, 50\}$ (Fig.~3(c) inset), 4.44\%--10.00\% for $\Drm{}$ across $\delta_0$, $w \in \{24, 32, 48, 64\}$, and soft-voxel weights $\{0.4, 0.5, 0.6\}$, and 3.33\%--4.44\% when perturbing individual $\Dhyb{}$ weights by $\pm 0.10$. Supplement~H reports 2,000 model-cluster $\Dereg{}$ bootstrap intervals (seed 20261111) weighted by identity multiplicities. For the four-model held-out subset in S1, zero-width bootstrap intervals reflect zero empirical errors on that small cohort ($n=4$) rather than a tight population ceiling (Supplement~H), motivating larger held-out pools when certifying strict error bounds.
```
<!-- /USER_LITERAL:uncertainty -->

### 5.8 Energy, Hybrid, and Color-Chart Ablations

At fixed weights (Supplement B), hybrid regularization raises EER on A, E, S2 6v6, and S3, lowers C P0→P2 EER from 10.00% to 7.78%, and keeps 0.00% EER on B and S1's three transfer paths, while energy regularization trades clean E EER (0.00% to 10.00%) for smoothness. Uniformly scaled CIELAB (Supplement A) matches RGB100 on B (0.00%) and E (10.00% clean/jitter) and yields 0.53% vs. 0.00% on S3, supporting direct RGB100 evaluation without nonlinear chart conversion.

<!-- USER_LITERAL:family_and_u -->
```latex
\subsection{Within-Family Alternatives}
Because cross-vendor differences are easier to separate than models from the same provider lineage, Table~6 isolates negative pairs sharing a declared model family while retaining all genuine pairs. Dataset A contains 604 directed same-family negatives (584 same-vendor and 122 same-sublineage). On shallow 3v3 sampling in A ($8\times 6$), restricting negatives to the same family raises $\Dereg{}$ EER from 5.36\% to 10.10\% (10.45\% same-vendor) and $\Dhyb{}$ EER from 7.14\% to 12.42\%. Once probe coverage increases to $20\times 6$ (B) or $10\times 30$ (S3), regularized energy retains 0.00\% within-family EER, and protocol-matched $\mathrm{B}\rightarrow\mathrm{E}$ transfer maintains 0.00\% within-family FAR. Evaluating candidate substitutes within the declared vendor family is therefore essential when sizing shallow production monitoring budgets across vendor model tiers.

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
\par\smallskip\footnotesize{$^*$Under protocol-matched $\mathrm{B}(20\times 6)\rightarrow\mathrm{E}(20\times 6)$ frozen thresholds, within-family FRR/FAR is 30.00\%/0.00\% for raw energy (10.00\%/0.00\% centered) and 10.00\%/0.00\% for $\Dhyb{}$.}
\end{table}

\subsection{Finite-Sample V- vs.\ U-Energy Estimators}
Whereas Table~5 keeps all $n_c, m_c \ge 1$ shared cells (3/10 raw, 1/10 centered clean V FRR on E), Table~7 compares V and U estimators on identical $n_c, m_c \ge 2$ cells (18--20 in B; dropping \texttt{rgb\_warm|zh} on \texttt{gw-gemini-3.6-flash} leaves 19--20 in E with 2/10 raw, 1/10 centered clean V FRR under separately B-fitted B3v3 cutoffs). At fixed $\delta_0=15$, replacing the V numerator with the unbiased U numerator cuts clean E EER from 10.00\% to 0.00\%--1.11\% and frozen FRR from 20.00\% to 10.00\% without the 256-draw bootstrap (unregularized $\Denergy{}$ also reaches 0.00\% EER / 10.00\% FRR cleanly, but suffers 100.00\% jitter FRR and 6.04\% $\mathrm{CF0}\rightarrow\mathrm{CF21}$ B3v3 FAR). Under $\pm 8$ jitter on E, the U numerator, signed ratio, and clipped ratio yield 8.89\%, 1.11\%, and 2.44\% EER vs.\ 13.00\%, 37.00\%, and 21.00\% frozen FRR (0.00\% empirical FAR), separating ranking from fixed cutoffs; signed U-ratio $\mathrm{CF21}\rightarrow\mathrm{OR21}$ FRR drops from 21.43\% (B3v3) to 0.00\% under matched B6v6.
```
<!-- /USER_LITERAL:family_and_u -->

<!-- USER_LITERAL:perturbation_and_reuse -->
```latex
\section{Service Monitoring and Controlled Interventions}
\subsection{Numerical Perturbation Sensitivity and Response Reuse}
To isolate coordinate-level sensitivity from live provider confounders in S1--S2, Table~S8 (Supplement~L) evaluates synthetic in-memory RGB perturbations on B ($40\times 15$) as a controlled numerical continuity stress test under frozen B8v7 cutoffs. All seven raw-score rows in Table~S8 retain 0.00\% re-swept EER and 0.00\% frozen FAR (self-centered $\pm 8$ shifts: 1.11\%--2.22\% EER; raw $\Dhybreg{}$ at $-8$: 10.00\% EER), and raw $\Dereg{}$ holds 0.00\% frozen FRR at $\pm 1$ and $\pm 8$ uniform jitter (vs.\ 100.00\% for $\Dhybreg{}$ at $\pm 8$, and 56.00\%--100.00\% under $\pm 15$ jitter, $\pm 8$ shifts, or step-32 channel quantization), whereas centering raises B jitter FRR to 11.00\% ($\pm 8$) and 89.00\% ($\pm 15$), as on E (Table~5).

Because marginal distributional scores depend only on unordered per-cell outputs, constant centroid replay is trivially eliminated by zero-entropy screening, whereas cyclic replay or i.i.d.\ resampling from an exposed reference histogram stays within finite-sample draw tolerance of $\hat P_{\mathrm{ref}}$ (recording 100\% empirical acceptance on B across $\Dhex{}, \Dvox{}, \Drm{}, \Dereg{}, \Dhyb{}$; Supplement~L). Keeping prompt sets private and rotating them mitigates static lookup tables ($<10{,}000$ tokens per model for a 64-call Dataset~C battery).
```
<!-- /USER_LITERAL:perturbation_and_reuse -->

**TABLE 7: Matched V/U Comparison on E; FAR Is Zero Throughout**

<!-- AUDIT_TABLE_u_energy -->
| Estimator | Clean EER | Clean FRR | Jitter EER | Jitter FRR |
| --- | --- | --- | --- | --- |
| V regularized | 10.00% | 20.00% | 10.00% | 51.00% |
| V self-centered | 4.44% | 10.00% | 6.56% | 68.00% |
| U numerator | 4.44% | 10.00% | 8.89% | 13.00% |
| U signed ratio | 0.00% | 10.00% | 1.11% | 37.00% |
| U clipped ratio | 1.11% | 10.00% | 2.44% | 21.00% |
<!-- /AUDIT_TABLE_u_energy -->

**Table note:** Requires $n_c, m_c \ge 2$ per cell (excluding `rgb_warm|zh` on `gw-gemini-3.6-flash`, leaving 19–20 cells on E; 2/10 raw, 1/10 centered clean V FRR under matched B3v3 cutoffs) vs. $n_c, m_c \ge 1$ in Table 5 (20/20; 3/10, 1/10).

### 6.2 Structured Canary Probes and Fixed Gateway Rules (S4)

Against simple gateway regexes flagging literal format tokens, single-token directives, or bare-color outputs, explicit HuePrint and Bruckner prompts trigger directive rules at 100.00%, whereas broad hex/color keyword filters incur 65.00% false positives on 40 frontend CSS tasks (26.00% across 100 synthetic author-constructed benign developer prompts). To evaluate realistic schema-constrained traffic, S4a embeds probes as 1-line CSS properties and 1-field JSON design tokens across 16 bilingual cells and 20 models (10 reps, 3,200 calls, 5v5), while S4b retains directive-bearing implicit phrasing (6 reps, 1,920 calls, 3v3; Table 8).

**TABLE 8: Study S4 Gateway Input/Output Rule Pass Rates and Implicit Verification (20 Genuine vs. 380 Impostors)**

<!-- RGB_TABLE_9 -->
| Battery and protocol | Unflagged input | Unflagged output | Valid and unflagged | $\tilde D_{\mathrm{E-reg}}$: Top-1 / AUC / EER | $D_{\mathrm{hyb}}$: Top-1 / AUC / EER |
| --- | --- | --- | --- | --- | --- |
| S3a (10 probes; 15v15) | 0.00% | 0.73% | 0.00% | 100.00% / 1.0000 / 0.00% | 100.00% / 0.9997 / 0.53% |
| S4a (5v5) | 100.00% | 99.97% | 99.75% (3192/3200) | 100.00% / 1.0000 / 0.00% | 100.00% / 0.9987 / 1.58% |
| S4b (3v3) | 0.00% | 2.50% | 0.00% | 100.00% / 0.9917 / 5.00% | 100.00% / 0.9683 / 8.95% |
| S3a → S4b (6v6) | — | — | — | 65.00% / 0.9154 / 15.00% | 85.00% / 0.9626 / 13.68% |
<!-- /RGB_TABLE_9 -->

**Table note:** Valid and unflagged requires valid parsing without triggering either the input or output rule. Unflagged input and output columns report marginal (single-stage) pass rates; S4b has 48/1,920 unflagged outputs and 26/1,920 invalid parses. `S3a → S4b (6v6)` evaluates the 8 shared English task cells.

The parser checks color extraction, not full CSS/JSON schema validity or production side effects. S4a yields 99.75% valid unflagged responses (3,192/3,200), with within-pool energy and hybrid EERs of 0.00% and 1.58% (removing API reasoning metadata alone leaves $\tilde D_{\mathrm{E-reg}}$ at 0.00% and raises $D_{\mathrm{hyb}}$ to 2.89%, vs. 2.63% when also merging `numeric_only` into `upper`; Supplement B). The higher S3a→S4b cross-format error reinforces matching references to the implicit prompt pool; Section 7.1 addresses session-level detection.

---

<!-- USER_LITERAL:routing -->
```latex
\subsection{Mixed-Routing Detection Curves}
To evaluate partial fallback routing, we simulate independent Bernoulli request mixtures routing to the declared backend with probability $q \in \{0, 0.2, 0.4, 0.5, 0.6, 0.8, 1\}$ and to a substitute $R$ with fallback rate $\lambda = 1 - q$ across 20 fixed seeds without replacement (Fig.~6; B's $40\times 7$ query pool has seven draws per cell, making its $q\in\{0,1\}$ endpoints deterministic). Each protocol applies its budget-matched energy threshold $\tau_{\mathrm{mid}}$ frozen on B.

At 20\% fallback ($q = 0.8, \lambda = 0.2$), 20-seed frozen-$\tau_{\mathrm{mid}}$ detection is 11.28\% for B's 60-call schedule (1.00\% clean FRR) vs.\ 0.33\% for 280 calls (0.00\% clean FRR), and 55.97\% vs.\ 12.45\% for S3's 30- and 70-call schedules (39.00\% and 3.75\% clean FRR). For $Q_\lambda = (1-\lambda)P + \lambda R$, unnormalized population squared energy satisfies $\mathcal{E}^2(P, Q_\lambda) = \lambda^2 \mathcal{E}^2(P, R)$ ($0.04$ at $\lambda = 0.2$); with $d_{AB} = \mathbb{E}\|X - Y\|_2$ for independent draws, the regularized population score is $\lambda^2 \mathcal{E}^2(P, R) / \{2[(1-\lambda)d_{PP} + \lambda d_{PR} + \delta_0]\}$ (for two point masses 100 RGB100 units apart at $\delta_0=15$ and $\lambda=0.2$, $4\%$ of the numerator vs.\ $13.14\%$ of the full-substitution regularized score). Distinct from this population ratio, empirical $\tau_{\mathrm{mid}}$ detection reflects finite-sample V-statistic bias and variance against a $\lambda = 1$ cutoff: $40\times 7$ suppresses variance and $O(1/n + 1/m)$ bias (Section~3.7) below $\tau_{\mathrm{mid}}$, whereas $10\times 3$ crosses $\tau_{\mathrm{mid}}$ via dispersion (39.00\% clean FRR). Stratified 999-permutation testing ($p \le 0.05$) on the same 20-seed mixtures recovers same-gateway null quantiles, lifting B ($40\times 7$) 20\%-fallback detection to 33.28\% (91.44\% at $\lambda=0.4$; within-family 25.75\% vs.\ 0.00\%) at 0.00\% clean FRR, lifting S3 ($10\times 7$) to 17.57\% (within-family 16.71\% vs.\ 5.00\%) at 4.50\% clean FRR, and cutting S3 ($10\times 3$) clean FRR to 4.75\% (Table~S9, Supplement~L). On cross-gateway S1 ($\mathrm{CF0}\rightarrow\mathrm{OR21}$, $20\times 3$), enrollment and genuine query distributions differ across gateways, so permutation testing rejects 16.07\% of pure genuine queries ($q=1$; 42.86\% at 6v6), motivating same-gateway references for low-$\lambda$ monitoring.
```
<!-- /USER_LITERAL:routing -->

![Offline mixed routing across 20 fixed seeds. Left: rejection of declared/substitute mixtures across subsampled 3- and 7-draw curves under frozen energy thresholds $\tau_{\mathrm{mid}}$ (solid, 5–95 percent seed bands) and 999-permutation testing on B $40\times 7$ ($p\le0.05$, dashed). Right: pure declared-model false rejection at $q=1$ (full-pool S3 $10\times 15$ has 0.00% clean FRR).](../figs/fig6_mixed_routing.pdf)

<!-- USER_LITERAL:overhead -->
```latex
\subsection{Operational Overhead}
Table~9 separates public-rate estimated API cost, latency-replayed estimated concurrent wall time, and measured local CPU scoring excluding one-time enrollment (Supplement~K). Under November~13, 2026 OpenRouter catalog rates~\cite{ref29}---scenario L ($0.71/0.71$ USD) and scenario G ($2.50/10.00$ USD per million input/output tokens)---estimated 150-call S3 color query cost has median 0.0077 USD (L) to 0.0345 USD (G; 0.0292--0.0432 USD across 19/20 endpoints, 0.2711 USD on \texttt{s3-deepseek-v3.2}; Section~4.2), and a 60-call B/E audit costs under 0.02 USD. Ideal eight-worker replay of recorded single-call latencies estimates 49--116~s of network wall time across 60--150 calls, whereas measured warm single-pair CPU scoring (NumPy~2.5.5, three preloaded B fixtures; API I/O, parsing, and gallery search excluded) has medians of 0.12, 0.31, and 0.08~ms for $\Dereg{}$ and 2.39, 10.15, and 2.51~ms for 999-permutation stratified energy testing on 20-cell 3v3, 40-cell 8v7, and 10-cell 8v7 batches. Unlike eight-query multi-token classifiers~\cite{ref16} with lower round-trip latency, HuePrint runs asynchronously out-of-band to supply continuous reference margins and permutation $p$-values.
```
<!-- /USER_LITERAL:overhead -->

**TABLE 9: Median Per-Endpoint Query Overhead; Enrollment Excluded**

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

<!-- USER_LITERAL:ending -->
```latex
\section{Limitations, Deployment, and Conclusion}

\subsection{Limitations}
Ground truth relies on provider-declared labels and API logs rather than cryptographic weight attestation, so endpoint behavior alone cannot confirm authorization; shallow 3v3 cells under-sample tails, and S1's four disjoint E identities motivate larger multi-month cohorts. In S2, hosts and quantization co-vary across providers, precluding causal isolation of quantization. Under complexity cascades~\cite{ref1,ref2} or burst detectors, short standalone probes hit low-complexity branches, motivating workload-embedded color fields with private prompt rotation.

\subsection{Deployment Guidelines}
Consumers should bind the checkpoint, private prompts, parser, valid-count rule, and budget in a versioned audit contract:
\begin{enumerate}
    \item \textbf{Metric and estimator:} Use centered $\Dereg{}$---or zero-bootstrap U-statistic ratios for $n, m \ge 2$ calibrated at matched cell budgets (signed vs.\ clipped trade off ranking and jitter FRR on E; Table~7)---for standard monitoring, and $\Dhyb{}$ across heterogeneous backends.
    \item \textbf{Calibration and two-stage confirmation:} Freeze $\tau_{\mathrm{mid}}$ or $\tau_{\mathrm{self}}$ where gateway drift is allowed, and apply Sz\'ekely--Rizzo permutation tests against same-gateway references for low-$\lambda$ screening. To avoid alert fatigue (where a 10\% 3v3 FRR compounds across hourly checks), confirm any 3v3 crossing via an immediate 6v6 or 15v15 window before escalating.
    \item \textbf{Caching, wrapper parity, and refresh:} Screen cache hits (zero entropy at $T=1.0$ and $<0.5\times$ median latency), enroll via the identical system-prompt wrapper, corroborate alerts with task telemetry, and rotate private prompts ($<10{,}000$ tokens/model per 64-call battery) upon refresh.
\end{enumerate}

\subsection{Conclusion}
HuePrint provides a black-box behavioral consistency signal for brokered cloud LLM services below four cents median query cost. Across 34,528 cloud responses, structured RGB elicitation cuts 30-call/side EER from 4.52\%--5.23\% for the word battery to 0.94\%--1.00\% on B/D and from 6.25\%--8.04\% to 3.49\%--5.00\% across 20 locked endpoints (0.00\% at deeper budgets), while continuous and multi-scale RGB distances improve shallow-census and cross-provider separation, tolerate three-week drift, and bound coordinate shifts. Together with unified Lipschitz bounds, zero-bootstrap U ratios, within-family and mixed-routing benchmarks, and structured canaries, these results support practical MaaS consistency monitoring.

\section*{Acknowledgments}
The author deeply thanks his parents and sister for their unwavering emotional and daily-life support throughout this research, and sincerely thanks his advisor, Dr.\ Vicky Li at Yunnan University of Chinese Medicine, for introducing him to computer science research.
```
<!-- /USER_LITERAL:ending -->

## References

[1] L. Chen, M. Zaharia, and J. Zou, "FrugalGPT: How to use large language models while reducing cost and improving performance," *Trans. Mach. Learn. Res.*, Dec. 2024.

[2] I. Ong, A. Almahairi, V. Wu, W.-L. Chiang, T. Wu, J. E. Gonzalez, M. W. Kadous, and I. Stoica, "RouteLLM: Learning to route LLMs from preference data," in *Proc. 13th Int. Conf. Learning Representations (ICLR)*, 2025, pp. 34433–34448.

[3] O. Tibermacine and C. Tibermacine, "QoS-aware brokering for LLM-as-a-Service: SLA-constrained routing with drift detection," in *Proc. IEEE Int. Conf. Web Services (ICWS)*, 2026, pp. 925–933, doi: 10.1109/ICWS72778.2026.00112.

[4] I. Gao, P. Liang, and C. Guestrin, "Model equality testing: Which model is this API serving?" in *Proc. 13th Int. Conf. Learning Representations (ICLR)*, 2025.

[5] W. Cai, T. Shi, X. Zhao, and D. Song, "Are you getting what you pay for? Auditing model substitution in LLM APIs," Apr. 2025, arXiv:2504.04715.

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

[29] OpenRouter, "Models API: Public model catalog and pricing," https://openrouter.ai/api/v1/models, accessed Nov. 13, 2026. Catalog snapshot archived with the offline analysis.

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
```
<!-- /USER_LITERAL:biography -->
