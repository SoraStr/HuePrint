# 空谈无益，亮出颜色：面向聚合式大语言模型服务的低预算一致性审计

**摘要**——聚合式大语言模型服务公开声明模型标识符，同时封装实际处理客户端请求的底层后端配置。本文提出轻量级框架 HuePrint，通过结构化颜色短响应与连续几何分布比较审计此类代理端点的行为一致性，无需模型权重或词元概率即可监测声明模型承诺。在覆盖 56 个端点与 12 个服务后端的 34,528 条云端响应中，结构化颜色协议将浅预算（每侧 30 次调用）等错误率在开发队列上从单词基线题组的 4.52%–5.23% 降至 0.94%–1.00%，在 20 个锁参端点上从 6.25%–8.04% 降至 3.49%–5.00%，并在中等采样深度达到零错误。连续与多尺度 RGB 距离在 56 端点浅层普查中将精确色号散度的错误率减半（5.36% 对 10.71%），将跨供应商开放权重错误率从 16.67% 降至 5.93%，在相隔三周与跨双网关观测中保持零排序错误（而严格分布相等检验误拒最高 42.86% 的真实同模型对），并在受控数值扰动下保持分离。统一的 Lipschitz 扰动界与有限样本估计量诊断刻画了标定迁移：注册自中心化将清洁持出误拒率降至 10%，U 统计量能量比值则消除了 256 次抽样的注册 bootstrap。同家族替代、分比例回退路由与结构化金丝雀探针的评估（估算单次查询费用中位数低于四美分），为云服务保障提供了部署准则。

**关键词**——服务计算，模型即服务，服务等级监测，API 代理，行为一致性，能量统计量。

---

## 1 引言

调用聚合式大语言模型（LLM）服务的应用指定目标模型标识符，而云服务代理商决定实际处理每个请求的后端实例 [1], [2]。动态模型级联、学习式路由器与多提供商代理在推理成本、延迟与响应质量之间权衡 [1]–[3]。当服务等级协议（SLA）承诺固定检查点或服务档位时，调用方需要黑盒证据确认履约端点在行为上仍与声明配置一致——仅凭延迟、在线率与计费日志无法核实这一点。

本文提出 HuePrint，为代理式 LLM 端点提供轻量黑盒一致性信号。HuePrint 通过多语言提示诱导十六进制（`#RRGGBB`）或十进制 RGB 短响应，并将其经验分布与注册参考比较，无需模型权重、隐藏激活或服务端如实返回的词元对数概率。既有审计揭示了商业端点中的统计差异 [4]，也说明需将后端替换与良性服务非确定性区分开 [5], [6]；HuePrint 不取代功能基准测试，而是作为低成本金丝雀监测器，在越过阈值时触发针对性的 SLA 调查。

两项设计原则支撑该框架。其一，**结构化 RGB 读出**结合紧凑颜色坐标与多语种语义先验：在每侧 30 次调用（$K=10$）下，HuePrint 将清洁等错误率（EER）在开发队列上从通用单词题组 [7] 的 4.52%–5.23% 降至 0.94%–1.00%，在 20 模型锁参基准上从 6.25%–8.04% 降至 3.49%–5.00%，并在更深预算下达到 0.00%。其二，**连续几何与多尺度比较**兼顾有限样本分辨率与服务漂移容忍度：$\tilde D_{\mathrm{E-reg}}$ 在 56 端点浅层普查中将精确色号 JSD 的 EER 减半（5.36% 对 10.71%），$D_{\mathrm{hyb}}$ 将跨 12 个异构服务栈的开放权重 EER 从 16.67% 降至 5.93%，基于颜色距离的审计在相隔约三周的两次 Cloudflare/OpenRouter 观测中保持 0.00% EER（严格相等检验拒绝最高 42.86% 的同模型对），且连续 RGB 几何有效约束受控坐标扰动下的得分偏移。

本文对云端 LLM 服务保障作出三项贡献：

- **端到端 MaaS 一致性协议：** 基于 34,528 条真实云端响应（数据集 A–E 和研究 S1–S4），制定连接参考注册、预算化结构探测、冻结阈值标定与参考更新的版本化审计约定。
- **扰动与有限样本估计量分析：** 刻画离散 JSD 的支撑逃逸、软体素与正则化能量距离的扰动敏感性，以及有限样本 V 统计量偏置对照零 bootstrap U 统计量比值与注册自离散度中心化的行为。
- **跨云后端运行特性：** 评估 56 个端点、12 个锁定的第三方服务栈、同家族候选替代、分比例回退路由曲线、模式约束的 CSS/JSON 金丝雀提示，以及单次审计的费用和延迟开销。

---

## 2 相关工作与服务模型

### 2.1 云服务保障与大模型服务聚合

**SLA 治理与代理路由。** FrugalGPT [1] 和 RouteLLM [2] 通过模型级联和偏好训练路由器在提供商侧优化成本—质量取舍，面向 LLM 的 QoS 代理 [3] 则将 SLA 约束路由与 CUSUM 漂移跟踪结合。然而在多租户云端代理中，调用方无法观察提供商的内部调度表，需要独立的低预算主动探测（金丝雀测试），核验实际履约端点是否兑现固定检查点 SLA 承诺，而非静默替换为廉价档位。

**服务测试与序贯漂移监测。** 服务计算研究从互补层面提升了云端 API 可靠性，包括 LLM 驱动的 REST API 模糊测试（RESTLess [8]）、多模态微服务异常检测（UAC-AD [9]）和概念漂移触发的边缘检查点恢复 [10]。不同于检查主机指标或模式错误的白盒遥测与功能模糊测试，HuePrint 通过标准聊天补全接口执行外部黑盒分布审计，区分良性服务漂移与未授权的后端变化。

**模型与 API 审计。** 服务端水印、指令后门与知识产权所有权指纹 [11]–[13] 需要服务商或模型拥有者介入，或面向模型盗用追责而非在线端点监测；被动来源归属 [14], [15] 需要较长生成，而 LLMmap [16] 与 TRAP [17] 等少查询主动探测通过特异提示在约八次多词元查询内分类闭集版本，并不跟踪连续的参考—查询漂移。Gao 等人 [4] 检验完整输出分布相等，Zhu 等人 [6] 需依赖白盒参考概率检验秩均匀性。随机生成任务中的有偏采样先验 [18]–[21] 支持短响应探针，尽管共享组件仍会使不同部署的输出产生相关性 [22], [23]。Bruckner [7] 在 40 个单词提示上应用 JSD（165 个模型上 7.3% EER）；HuePrint 则在匹配调用预算下评估结构化颜色协议，并在共享颜色响应上对比连续与离散统计量。

### 2.2 服务聚合架构与审计约定

**角色与观测。** 调用方监测器通过可信参考端点 $E_{\mathrm{ref}}(M^*)$ 注册声明检查点 $M^*$，在 $k$ 个任务—语言单元上审计代理端点 $E$，每单元采集 $n_B$ 条补全（有效解析数为 $n=|U|, m=|V|$；图 1）。Cloudflare AI Gateway 与 OpenRouter 等网关在标准聊天补全访问下提供可观测路由路径，无需模型权重、隐藏状态、对数概率或服务端随机种子控制。

**审计约定与部署混杂因素。** 审计约定将参考画像、提示集、采样预算、响应解析器和冻结阈值版本绑定到固定检查点 SLA 承诺，而非声明按复杂度级联路由的网关服务 [1], [2]（后者的轻量分支按约定合法处理短提示）。检查点一致性与精度档位一致性作为不同目标评估，与任务质量和 QoS 遥测共同提供行为证据，而非权重身份的密码学证明。两类网关机制需在运行中显式处理：响应缓存或语义缓存会在 $T=1.0$ 下使随机抽样坍缩（可通过零输出熵配合低于中位数的延迟予以筛除）；代理注入的系统提示封装则会偏移条件颜色先验，除非通过相同的网关封装完成注册。

**服务变化情景与生命周期。** 本文评估四种运行情景：（1）固定模型标识符下的完整检查点替换；（2）不变检查点标签下的低比特精度执行；（3）按请求概率混合声明与替代后端的回退；（4）通过已知参考库查表或直方图重采样复用响应。部署时，低于冻结阈值 $\tau$ 的得分给出**接受**，越过阈值则触发**调查**（或两阶段序贯复核），获授权的配置更新启动参考刷新。

---

![代理式 LLM 服务的调用方审计流程。注册参考与协议匹配探针生成冻结一致性决定；配置变化需要调查并更新参考。](../figs/fig1_service_audit.pdf)

## 3 方法论与扰动分析

### 3.1 探针、解析与 RGB 坐标

探针集将 10 项任务与四种语言（en、zh、ru、ar）组合为 40 个任务—语言单元，覆盖十六进制（`#RRGGBB`）与 RGB 语法下的随机色、偏爱色、暖色、自然、海洋、平静和夜晚色（图 2；例如 *"Pick a random color. Reply with only its #RRGGBB hex code."*）。S4 将颜色选择嵌入单行 CSS 自定义属性（如 `--brand-primary`）与单字段 JSON 设计令牌；补充材料 C–F 给出完整端点清单及逐字提示原文。解析器去除显式推理字段和内联标签后，提取首个合规 `#RRGGBB` 色号或经范围校验的 $0\text{--}255$ RGB 三元组（保留大写规范 `#RRGGBB`、坐标、语法及独立的“严格仅含色号”标记），提取失败记为无效。

对 sRGB 色号 $\mathbf c\in\Omega=\{0,\ldots,255\}^3$ [24]，使用线性缩放 $\mathbf x=T(\mathbf c)=100\mathbf c/255\in\Omega_{\mathrm{RGB}}=[0,100]^3$（仅改变单位，不执行伽马逆变换或 CIELAB 变换，也不将距离解释为感知色差）；若 $\mathbf c'=\operatorname{clip}_{[0,255]^3}(\mathbf c+\boldsymbol\eta)$ 且 $\|\boldsymbol\eta\|_\infty\le a$，则 $\|T(\mathbf c')-T(\mathbf c)\|_2\le 100\sqrt3 a/255$。下文连续得分统一使用 RGB100，硬、软体素分配仍使用原始通道单位。补充材料 A 分析单射与 Lipschitz 色彩坐标，补充材料 B 在混合权重固定条件下比较正则化。

![五个按端点标识固定选择的家族代表：标记面积为输出频次、填色为实际 RGB，两幅投影分别为 R/G 和 B/G；右侧为匹配端点的随机颜色单字分布。](../figs/fig2_rgb_geometry_vs_words.pdf)

### 3.2 离散 JSD 与支撑逃逸

令 $M=(P+Q)/2$，以 2 为底的 JSD [25] 为
$$D_{\mathrm{JSD}}(P\|Q)=\tfrac12\sum_xP(x)\log_2\frac{P(x)}{M(x)}+\tfrac12\sum_xQ(x)\log_2\frac{Q(x)}{M(x)},$$
其中略去零质量项；它满足 $0\le D_{\mathrm{JSD}}(P\|Q)\le 1$，且等于 $1$ 当且仅当 $\operatorname{supp}(P)\cap\operatorname{supp}(Q)=\emptyset$。$D_{\mathrm{hex}}$ 使用精确 RGB 色号，$D_{\mathrm{vox}}$ 使用 $(\lfloor R/32\rfloor,\lfloor G/32\rfloor,\lfloor B/32\rfloor)$，分别有 $256^3$ 和 $8^3$ 个类别。

**命题 1（支撑逃逸下界）**。*固定支撑大小为 $r$ 的参考经验分布 $P_{\mathrm{ref}}$，令 $Q^{\mathrm{jitter}}$ 表示源颜色 $\mathbf c\sim P_{\mathrm{src}}$ 经上述裁剪变换施加独立的 $\{-a,\ldots,a\}^3$ 上均匀整数噪声（$a\ge1$）所得的扰动总体分布。对从 $Q^{\mathrm{jitter}}$ 抽取的 $n$ 个独立同分布查询 $\hat Q_n^{\mathrm{jitter}}$，若逃离参考支撑的概率 $Q^{\mathrm{jitter}}(\Omega\setminus\operatorname{supp}(P_{\mathrm{ref}}))\ge t\in[0,1]$，则*
$$\mathbb E[D_{\mathrm{hex}}(P_{\mathrm{ref}},\hat Q_n^{\mathrm{jitter}})]\ge D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})\ge\psi(t),$$
$$\psi(t)=\tfrac12\log_2\frac2{2-t}+\tfrac{1-t}{2}\log_2\frac{2(1-t)}{2-t}+\tfrac t2\ge\tfrac t2,$$
*其中 $\psi$ 严格递增，按连续延拓有 $\psi(1)=1$，且总体下界是紧的。当 $\operatorname{supp}(P_{\mathrm{src}})\subseteq\{a,\ldots,255-a\}^3$ 时，可取 $t=\max(0,1-r/(2a+1)^3)$。*

固定各单元已观察到的清洁查询颜色并对每次观测各加一次随机裁剪扰动，图 3(a) 即可由查询经验直方图的精确逃逸概率计算式 (1) 下界。命题 1 解释了微小通道位移为何使正例 $D_{\mathrm{hex}}$ 得分迅速趋近于 $1$，而经验 EER 同时取决于负例得分分布（图 3(c)）；命题 1–2 与引理 1 的证明见补充材料 G。

### 3.3 软体素与正则化能量

取原始通道单位下的步长 $w=48$ 和节点集 $\mathcal I=\{0,\ldots,6\}^3$，定义
$$W_i(\mathbf c)=\prod_{d\in\{R,G,B\}}\max(0,1-|c_d/w-i_d|),\qquad P_{\mathrm{soft}}(i\mid S)=|S|^{-1}\sum_{\mathbf c\in S}W_i(\mathbf c).$$
因 $255/w=5.3125<6$，三线性帐篷权重在 $[0,255]^3$ 上满足 $W_i(\mathbf c)\ge 0$ 且 $\sum_{i\in\mathcal I}W_i(\mathbf c)=1$，故式 (2) 中 $P_{\mathrm{soft}}(\cdot\mid S)$ 构成概率分布，$D_{\mathrm{svox}}$ 定义为两个软直方图之间的 JSD。

**引理 1（软体素稳定性）**。*对任意 $\mathbf c,\mathbf c'\in[0,255]^3$，$\|W(\mathbf c)-W(\mathbf c')\|_1\le(2/w)\|\mathbf c-\mathbf c'\|_1\le(6/w)\|\mathbf c-\mathbf c'\|_\infty$；故每点逐通道位移至多 $a$ 的等规模配对样本 $S,S'$ 满足 $D_{\mathrm{JSD}}(P_{\mathrm{soft}}(S)\|P_{\mathrm{soft}}(S'))\le b$，其中 $b=\min(1,3a/w)$。*

图 3(b) 的软体素曲线绘出上述查询与其扰动版之间的散度 $D_{\mathrm{JSD}}(P_{\mathrm{soft}}(S)\|P_{\mathrm{soft}}(S'))$。对照固定参考 $P_{\mathrm{ref}}$ 时，$\sqrt{D_{\mathrm{JSD}}}$ 的度量三角不等式给出 $|\Delta\sqrt{D_{\mathrm{svox}}}|\le\sqrt b$，而实际进入 $D_{\mathrm{RM}}$ 的原始得分变化满足 $|\Delta D_{\mathrm{svox}}|\le\min(1,2\sqrt b)$；判定是否翻转还需结合实际得分到冻结阈值 $\tau$ 的余量。

对非空 RGB100 点云 $U,V$，令 $n=|U|$、$m=|V|$，并定义
$$d_{UV}=\frac{\sum_{i,j}\|u_i-v_j\|_2}{nm},\qquad d_{UU}=\frac{\sum_{i,i'}\|u_i-u_{i'}\|_2}{n^2},$$
$d_{VV}$ 同理，类内求和包含对角项。经验 V 统计量平方能量为 $\widehat{\mathcal E}_V^2=2d_{UV}-d_{UU}-d_{VV}$。在有限一阶矩分布上，总体平方能量满足 $\mathcal E^2(\mu,\nu)\ge 0$ 且等于零当且仅当 $\mu=\nu$ [26], [27]；将其用于经验测度即知 $0\le\widehat{\mathcal E}_V^2\le 2d_{UV}$。据此定义归一化与正则化能量相异度
$$\bar D_{\mathrm E}=\frac{\widehat{\mathcal E}_V^2}{2d_{UV}},\qquad\tilde D_{\mathrm{E-reg}}=\frac{\widehat{\mathcal E}_V^2}{2d_{UV}+2\delta_0},$$
其中式 (3) 中 $\delta_0=15$（RGB100 长度单位），$d_{UV}=0$ 时令 $\bar D_{\mathrm E}=0$。浮点求值时以 $[\widehat{\mathcal E}_V^2]_+=\max(0,\widehat{\mathcal E}_V^2)$ 将分子截断至 $[0,2d_{UV}]$，并在 $d_{UV}<10^{-12}$ 时置零。对相距 $\epsilon>0$ 的两个常量点云（$d_{UU}=d_{VV}=0,d_{UV}=\epsilon$），$\bar D_{\mathrm E}$ 从重合时的 $0$ 直接跳变至 $1$，而 $\tilde D_{\mathrm{E-reg}}=\epsilon/(\epsilon+\delta_0)\le\epsilon/\delta_0$ 平滑变化。

**命题 2（正则化能量比值的 Lipschitz 稳定性）**。*对非空点云 $U,V\subset\mathbb R^3$、$\delta_0>0$、跨组均距 $d=d_{UV}$，以及含对角项（$\tilde D_{\mathrm{E-reg}}$）或排除对角项（$|U|,|V|\ge 2$，第 3.7 节）计算的两组组内均距平均 $h$，令 $F(d,h)=(d-h)/(d+\delta_0)$。若只移动 $V$ 中各点且每点欧氏位移至多 $\epsilon$（方向可任意不同），$F(d,h)$ 与 $[F(d,h)]_+$ 的变化均不超过 $2\epsilon/\delta_0$；若同时移动 $U$ 与 $V$ 中各点且每点位移至多 $\epsilon$，变化均不超过 $4\epsilon/\delta_0$。*

对取值在 $[0,1)$ 内的截断比值，逐通道位移 $a$ 给出单侧上界 $\min\{1,200\sqrt{3}a/(255\delta_0)\}$（$\delta_0=15$ 时 $a=1,8$ 分别对应 0.0906 与 0.7245），保证 $d_{UV}\to 0$ 处的连续性。命题 2 允许各点沿任意最坏方向移动，而图 3(b) 中各点独立均匀抖动相互未对齐，实测变化远低于该最坏包络。

高斯 Bures–Wasserstein 对照 [28] 使用有偏协方差及单位为 RGB100 长度平方的岭项 $10^{-3}I$，取 $D_{W_2}=1-e^{-W_2/50}$，其中长度尺度为 50 个 RGB100 单位。仅匹配两个矩不能像能量一样区分所有分布；其完整公式和限制见补充材料 G。

![每个扰动半径使用十个固定种子。(a) 精确 JSD 与考虑边界截断的条件期望下界；(b) 能量得分变化、查询与其扰动版的软体素 JSD 及各自上界；(c) 重扫线性 EER，插图为正则量敏感性。](../figs/fig3_stability_bounds.pdf)

### 3.4 复合得分与判定

$D_{\mathrm{side}}$ 对语法（大小写/前缀或逗号空格）、可获得的推理首词及对数分箱推理长度求 JSD 均值。由于十六进制大小写标签会区分纯数字色号（`numeric_only`，占 RGB 立方体的 $5.96\%$），且推理长度优先读取 API 返回的 `usage.reasoning_tokens` 再回退到可见字符数，$D_{\mathrm{side}}$ 作为辅助语法与信封侧信道而非与颜色或计费信封完全无关的不变量（纯文本去混杂消融见补充材料 B）。包含正则化多尺度复合量 $D_{\mathrm{RM}}$ 在内的固定组合为
$$\begin{aligned}D_{\mathrm{hyb}}&=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}+0.25\bar D_{\mathrm E}+0.15D_{\mathrm{side}},\\D_{\mathrm{hyb-reg}}&=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}+0.25\tilde D_{\mathrm{E-reg}}+0.15D_{\mathrm{side}},\\D_{\mathrm{RM}}&=0.50D_{\mathrm{svox}}+0.50\tilde D_{\mathrm{E-reg}}.\end{aligned}$$
式 (4) 中得分对共有合格单元取平均，$S\le\tau$ 时接受。开发集正、负例得分 $G,I$ 定义 $\tau_{\mathrm{mid}}=(\max G+\min I)/2$ 和 $\tau_{\mathrm{u0}}=\operatorname{nextafter}(\min I,-\infty)$（零 FAR 仅对开发负例有保证）。AUC 对平局计半权；线性 EER 在相邻 ROC 点间插值并重扫阈值，冻结 FAR/FRR 则评估部署判定。

### 3.5 注册标定与相等检验

对每个参考模型/单元，仅从注册观测独立 bootstrap 两个点云，规模匹配已观测注册数与计划查询数。对 256 次固定种子抽样和合格单元基线取均值得到 $\mu_{\mathrm{self}}$（不使用查询数据或测试标签），使用 $\Delta_D=D-\alpha\mu_{\mathrm{self}}$ 并保留负值。在规模为 $n$ 的独立同分布注册抽样下，从经验分布 $\hat P_n$ 有放回重采样以 $1/n$ 概率碰撞到同一样本点，使对注册样本取期望后的经验组内均距——从而零假设下 bootstrap 的期望未归一化 V 分子——乘以碰撞因子 $(n-1)/n$（而归一化得分 $\tilde D_{\mathrm{E-reg}}$ 在 B3v3 与 E 上的实测均值比 $\overline{\mu}_{\mathrm{self}}/\overline{G}=0.732$ 与 $0.598$ 反映比值归一化效应，不能用于验证 $(n-1)/n$）。比较原始得分、$\alpha=1$，以及仅在 B 上按留一模型平衡错误率从 $\{0,0.25,0.5,1,1.5,2\}$ 选择的系数（B6v6/B8v7 上的零错误平局优先取接近 $\alpha=1$ 的系数）。阈值仅在 B 上按协议拟合并冻结：B3v3（20 单元前六次奇偶划分，用于 E）、B6v6（20 单元前六次对后六次，用于预算匹配的 S1 核查）和 B8v7（40 单元全部 15 次奇偶划分；完整核验每半至少五个有效样本，服务变化标定至少一个）。

将两样本能量相等检验 [27] 推广至分层单元，我们对各单元的 $nm\widehat{\mathcal E}_V^2/(n+m)$ 取平均，在各单元内对合并标签作 999 次独立置换，并以 $p=(1+\#\{T_b\ge T_{\mathrm{obs}}\})/1000$ 标定。在单元内可交换条件下，$p\le0.05$ 拒绝条件有效颜色分布相等（逐对拒绝率未作多重比较校正，且共享端点的配对之间存在统计相关）。

### 3.6 完整响应基线与匹配预算

将 Gao 等人 [4] 的独热相等核 MMD 与 $L_1$ 检验适配至原始字符串（保留空格、大小写与无效输出，经验 TV 为类别 $L_1$ 差异的一半），对 $n,m\ge2$ 及相等核 $k(s,t)=\mathbf1[s=t]$ 计算
$$\widehat{\mathrm{MMD}}_u^2=\frac{\sum_{i\ne i'}k(x_i,x_{i'})}{n(n-1)}+\frac{\sum_{j\ne j'}k(y_j,y_{j'})}{m(m-1)}-\frac{2\sum_{i,j}k(x_i,y_j)}{nm},$$
逐单元统计量取平均（离散 MMD-U 按精确有理数计数求值），并使用相同的 999 次置换，同时分开报告统计量 EER/AUC 与置换拒绝率。无效解析响应仍消耗调用预算。S3 在多达 40 个共享 $K$ 单元提示子集（$K=1,\ldots,10$）上测试双侧总预算 $N\in\{6,10,20,30\}$（$n=m=N/2$；B-20×6/D 测试 $N=6$），十个固定种子在内存中扰动已解析的 RGB 色号。

### 3.7 有限样本能量估计量

对规模为 $n,m$ 的独立 IID 样本，令 $a_P=\mathbb E\|X-X'\|$、$a_Q=\mathbb E\|Y-Y'\|$，则非负 V 分子满足 $\mathbb E[\widehat{\mathcal E}_V^2]=\mathcal E^2(P,Q)+a_P/n+a_Q/m$。当 $n,m\ge2$ 时，U 分子
$$\widehat{\mathcal E}_U^2=2d_{UV}-\frac{n}{n-1}d_{UU}-\frac{m}{m-1}d_{VV}$$
取值于 $[-2d_{UV},2d_{UV}]$，可以取负，且在独立 IID 抽样下无偏估计 $\mathcal E^2(P,Q)$。对照 $\tilde D_{\mathrm{E-reg}}$（*V regularized*）与自中心化 $\tilde D_{\mathrm{E-reg}}$（*V self-centered*），表 7 比较 $\widehat{\mathcal E}_U^2$（*U numerator*）、$\widehat{\mathcal E}_U^2/(2d_{UV}+2\delta_0)$（*U signed ratio*）以及 $[\widehat{\mathcal E}_U^2]_+/(2d_{UV}+2\delta_0)$（*U clipped ratio*；因 $\delta_0>0$，截断后的比值严格属于 $[0,1)$，外层 $\min\{1,\cdot\}$ 截断不触发）。除以随机分母 $2d_{UV}+2\delta_0$ 和正部截断一般均不保持无偏性；由命题 2（补充材料 G），带符号与截断 U 比值共享单侧 $2\epsilon/\delta_0$ 与双侧 $4\epsilon/\delta_0$ 扰动上界。所有 U 统计量变体与匹配的 V 统计量对照均在两侧各包含至少两个有效响应的相同单元上评估。

---

## 4 实验设计与数据集架构

### 4.1 数据集总览与可复现数据溯源

五套基准数据集（A–E，2026 年 10 月）和四项线上研究（S1–S4，2026 年 11 月）共提供 **34,528** 条唯一云端响应（表 1）。A 用于端点普查，B 支持预算分析和标定，C 测试改写，D 提供单词基线，E 评估持出模型；S1–S4 分别研究网关与会话迁移、多供应商、更深的配对采样，以及隐式探针。

**表 1：云端响应数据集总览**

| 模块与数据集代号 | 模型/端点数 | 探测规格（单元 $\times$ 重复） | 唯一调用数 | 有效解析数（有效率） | 核心评估目标 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Dataset A**（广谱普查集） | 56 端点（11 家族） | $8 \times 6$（4 任务 $\times$ 中/英） | 2,688 | 2,611 (97.14%) | 56 端点核验、跨子谱系/跨家族负例分析、LOO 家族归属、侧信道剥离 |
| **Dataset B**（开发深度集） | 10 开发模型 | $40 \times 15$（10 任务 $\times$ 4 语言） | 5,520 | 5,932/6,000 (98.87%) | 全深度核验精度、48 点 $(n,k)$ 预算网格消融、服务变化与冻结阈值标定 |
| **Dataset C**（显式改写集） | 10 开发模型 | $16 \times 8$（$P_1, P_2$ 两套改写） | 1,280 | 1,262 (98.59%) | 同改写池自核验 vs. $P_0 \to P_1/P_2$ 零样本跨句式条件偏移诊断 |
| **Dataset D**（单字基线集） | 10 开发模型 | $20 \times 6$（10 单字任务 $\times$ 中/英） | 1,200 | 1,196 (99.67%) | 与 `B-20x6` 同请求预算对照及提示词/输出粒度与统计量的分层比较 |
| **Dataset E**（非 B 确认集） | 10 样本外模型 | $20 \times 6$（10 色彩任务 $\times$ 中/英） | 1,200 | 1,187 (98.92%) | `+6.74h` 跨会话核验（`A->E`）、`B->E` 冻结阈值零样本迁移与样本外抗抖动 |
| **Study S1**（跨三周+跨网关） | 14 模型 $\times$ 2 网关 | $20 \times 6$（`CF` 与 `OR` 双网关） | 3,360 | 3,338 (99.35%) | `T+21.32d` 时序漂移与 `Cloudflare <-> OpenRouter` 跨网关冻结阈值核验 |
| **Study S2**（多供应商比较） | 6 开源权重 $\times$ 3 供应商 | $20 \times 6$（锁定 12 家独立后端） | 2,160 | 2,147 (99.40%) | 异构推理栈与 `int4`/`fp4`/`fp8`/`bf16`/LPU 硬件量化跳变下的权重归属 |
| **Study S3**（锁参 $N=30$ 配对） | 20 模型（8 大家族） | $10 \times 30$ $\times$ 2 方法（completion cap 64） | 12,000 | 11,985 (99.88%) | 64 Token 上限下的等样本（15v15）配对比较 |
| **Study S4**（结构化金丝雀测试） | 20 模型（8 大家族） | `S4a` $16\times 10$ + `S4b` $16\times 6$ | 5,120 | 5,087 (99.36%) | CSS/JSON 提示解析、固定输入/输出正则规则及同池核验 |

**表注：** B 的 5,520 次独立调用加上从 A 共享的 480 条种子响应，共构成 6,000 条网格记录。S3 的 12,000 条响应中有 3 条触及长度上限（颜色 2 条、单词 1 条，其中 1 条仍有效解析）。

复现包提供只读响应日志、去重规则、输入校验值、固定种子，以及用于全部分数、ROC 曲线、EER 和冻结 FAR/FRR 的分析与矢量绘图代码。A–E 贡献 11,888 次唯一调用，S1–S4 贡献 22,640 次。

### 4.2 采样超参数与商业 API 温度参数兼容性说明

请求在接口支持时关闭可选思考模式，并设置较短的生成长度上限（16–256 Token；S2/S3 锁定为 64，S4 锁定为 128；补充材料 K）。Datasets A–C 完全省略温度字段（`temperature_sent=null`，使用提供商默认采样策略），D、E 和 `S1_CF21` 仅在直连 Workers AI 的 1–2 个端点上显式传入 `temperature=1.0`（经代理网关路由时省略）；`S1_OR21`、S2、S3 和 S4 则统一显式传入 `temperature=1.0`（S3 的颜色与单词臂统一设 `max_tokens=64`，两个 Claude 端点的参数剥离行为在配对请求中相同）。在 S1 中，五个支持推理的 `S1_OR21` 端点额外传入 `reasoning.effort="low"`，而 Cloudflare 的 `llama-3.3-70b-fp8-fast` 记录了 `-sd` 投机解码，因此跨网关对比同时反映网关后端差异与客户端封装差异。在未锁定后端的 OpenRouter 采集（`S1_OR21`、S3、S4）中，网关分别对 5/14、7/20 和 5–6/20 个模型在多个子提供商间动态负载均衡（而 S2 关闭回退，混合比例为 `0/18`）；但 S3 奇偶折半间的子提供商构成保持平衡（经验 TV 均值 0.0419，最大值 0.1200），且 `GMICloud` 在 `s3-deepseek-v3.2` 的 158/300 次调用中忽略了思考关闭参数，单次输出最高达 907 Token（补充材料 K）。此外，A 中三个模型的 144 条记录仅返回推理摘要而缺少原始推理文本；解析阶段剥离推理轨迹，而开销核算保留全部计费 Token。

---

## 5 基准与跨服务评估

### 5.1 56 端点普查与格式侧信道对照（Dataset A）

我们在涵盖 11 个厂商家族的 56 个模型端点上采集了浅预算颜色响应（8 单元 $\times$ 6 重复，奇偶 3v3 划分且每侧至少 2 个有效响应），产生 56 对同模型正例与 3,080 对全量有向冒充负例（剔除同子谱系多日期检查点后为 2,958 对跨子谱系负例，不同厂商间为 2,476 对跨家族负例），并在 50 个多成员家族模型上评估留一法最近邻（LOO 1-NN）家族归属准确率（表 2）。

**表 2：Dataset A（56 模型，$8\times 6$ 浅预算）二元身份核验与家族谱系归属结果**

<!-- RGB_TABLE_2 -->
| 指标 | AUC | 离散 / 线性 EER | 跨子谱系线性 EER | 跨家族线性 EER | LOO 家族归属 |
| --- | --- | --- | --- | --- | --- |
| $\bar D_{\mathrm E}$ | 0.9900 | 5.06% / 4.77% | 3.75% | 3.57% | 31/50 (62.00%) |
| $\tilde D_{\mathrm{E-reg}}$ | 0.9872 | 5.36% / 5.36% | 5.36% | 4.52% | 35/50 (70.00%) |
| $D_{\mathrm{hyb}}$ | 0.9774 | 7.14% / 7.14% | 7.14% | 7.14% | 36/50 (72.00%) |
| $D_{\mathrm{hex}}$ | 0.9588 | 10.73% / 10.71% | 10.71% | 8.93% | 38/50 (76.00%) |
| $D_{\mathrm{RM}}$ | 0.9582 | 8.93% / 8.93% | 8.93% | 8.93% | 34/50 (68.00%) |
| $D_{\mathrm{vox}}$ | 0.9489 | 8.83% / 8.93% | 8.93% | 8.93% | 39/50 (78.00%) |
| $D_{\mathrm{side}}$ | 0.7804 | 30.32% / 30.32% | 29.76% | 28.56% | 17/50 (34.00%) |
<!-- /RGB_TABLE_2 -->

**表注：** 已归档的历史 `evaluate_cohort`/`within` 口径先按每个端点在奇偶两半均满足 $\ge 2$ 个有效解析筛选单元，再构造配对；若按部署时可直接实施的独立筛选规则对有向对 $(i,j)$ 分别按注册侧 $i$ 的注册有效数 $\ge 2$ 与查询侧 $j$ 的查询有效数 $\ge 2$ 筛选后取交集，3,080 个有向负例中有 163 对的合格单元集合改变（56 个正例对为 0 对），$\bar D_{\mathrm E}$ 线性 EER 为 4.16%（历史口径为 4.77%），$\tilde D_{\mathrm{E-reg}}$ 保持 5.36% 不变（`scripts/sensitivity_checks.py`）。

表 2 中，连续距离在二元核验中表现更优，保留类别偏好的统计量在家族归属中更有优势（$D_{\mathrm{vox}}$ 为 39/50，$\tilde D_{\mathrm{E-reg}}$ 为 35/50）。若将纯数字十六进制标签 `numeric_only` 并入 `upper` 并剥离 API 推理计费遥测，A 上的 $D_{\mathrm{side}}$ AUC/EER 从 0.7804/30.32% 降至 0.6557/36.76%，B 上则从 0.9722/10.00% 降至 0.6933/36.00%（补充材料 B；对因思考截断仅保留 2/8 个单元的 `gw-gemini-2.5-flash` 将有效响应门槛放宽至 $\ge 1$ 时，$\bar D_{\mathrm E}$ EER 为 5.62%，$\tilde D_{\mathrm{E-reg}}$ 保持 5.36%）。

---

### 5.2 查询预算扩展曲线与二维 $(n, k)$ 网格消融（Dataset B）

将 B 扩展至 40 单元、15 次重复后，六个非参数色彩指标的 AUC 均为 1.0000，离散与线性 EER 均为 0.00%；高斯 $D_{W_2}$ 仍留有 2.22% 线性 EER（离散 EER 1.11%，AUC 0.9978），印证了第 3.3 节仅匹配前两阶矩的信息损失。图 4(a) 的预算网格展示探针覆盖与采样深度的权衡：$(n=15,k=4)$ 的 60 次采样平均线性 EER 为 1.78%，$(n=6,k=16)$ 的 96 次采样降至 0.46%。


---

![(a) B 采样预算网格上 $D_{\mathrm{hyb}}$ 的平均线性 EER；(b) B（$20\times 6$，3v3）、E（$20\times 6$，3v3）及 S1 路径（$20\times 6$，6v6）上的正负例正则化能量得分，并绘出冻结 B3v3（$\tau=0.148$，虚线）与预算匹配的 B6v6（$\tau=0.113$，点线）中点阈值。](../figs/fig4_budget_and_drift.pdf)

### 5.3 同池自验证与跨模板偏移（Dataset C）

Dataset C 在八个双语单元上评估两个改写池（每单元重复八次）：句法重述 $P_1$ 和设计语境框架 $P_2$（各指标详细结果见补充材料 I）。正则化能量 $\tilde D_{\mathrm{E-reg}}$ 在 $P_1$ 与 $P_2$ 内分别取得 0.00% 和 1.11% 线性 EER，而跨模板比较 $P_0\rightarrow P_1$ 和 $P_0\rightarrow P_2$ 分别为 17.78% 和 11.11%。即使同义措辞也会改变条件颜色先验，因此参考画像必须始终以精确提示集为条件。

---

### 5.4 同预算的探针与统计量对照（Dataset D 与 Study S3）

**结构化颜色探针。** 在同一批 10 个开发模型上对 B-20×6 与 D 的 40 个相互重叠的十单元子集（$K=10$，每单元每侧 3 次，单侧共 30 次调用）求平均，Color MMD-U 与 $\tilde D_{\mathrm{E-reg}}$ 的清洁 EER 分别为 0.94% 和 1.00%，Word MMD-U 与 Word JSD 分别为 4.52% 和 5.23%；汇总全部 $K=20$ 个单元（单侧 60 次调用）时，Color MMD-U、$\tilde D_{\mathrm{E-reg}}$、$D_{\mathrm{hex}}$ 与 Word MMD-U 均达到 0.00%（Word JSD 为 1.11%；补充材料 K），颜色与单词每单元分别提供 18.65 与 7.05 个不同有效输出（总 Token 数分别为 111,305 与 79,398；$K=10$ 下 $\pm8$ 抖动 EER 为 49.73% 对 1.59%）。由于单词题组还包含动物、城市、数字、字母与硬币，完整题组差距体现固定预算下探针设计与坐标表示的联合协议效率。S3 在 20 个模型（8 个家族、10 个英文探针、15v15、上限 64；表 3）上分别有效解析 99.97% 颜色（5,998/6,000）和 99.78% 单词（5,987/6,000）响应；即便仅在 S3 两道共享颜色概念题上计算原始字符串 MMD-U（`hex_random`、`hex_favorite` 对照 `brk_rand_color`、`brk_fav_color`；补充材料 K），色号坐标仍将 3v3/15v15 的 AUC 从 0.8349/0.9784 提升至 0.9156/0.9909（EER 分别为 17.92% 对 20.21% 及 5.26% 对 5.00%），并支撑下文的连续三维几何比较。

**表 3：S3 同预算原始统计量线性 EER；末列为十种子 RGB 抖动均值**

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

**连续 RGB 比较。** 在 S3（$K=10$）上，浅层 $N=6$ 采样给出 3.49%（Color MMD-U）与 5.00%（$\tilde D_{\mathrm{E-reg}}$）清洁 EER，优于 Word MMD-U（8.04%）、Word JSD（6.25%）以及精确色号 $D_{\mathrm{hex}}$ 的实测值（10.00%）；若剥离原始格式并在规范 `#RRGGBB` 色号与归一化单词上计算 MMD-U，该差距依然保持（$N=6$ 时 5.00% 对 9.31%，$N=30$ 时 0.00% 对 0.53%）。在 $N=30$ 下，Color MMD-U 与 $\tilde D_{\mathrm{E-reg}}$ 的清洁 EER 均为 0.00%（AUC 1.0000），而 Word MMD-U 为 1.32%，$D_{\mathrm{hex}}$、Color TV 与 Word JSD 均为 5.00%；在受控 $\pm8$ 抖动下，Color MMD-U、Color TV 与 $D_{\mathrm{hex}}$ 分别退化至 50.00%（AUC 0.5184）、35.99% 与 35.40% EER，而能量仍保持 0.00% EER（AUC 1.0000；图 5）。

在 $p\le0.05$ 时，S3 Color MMD-U 拒绝清洁数据中 10.00% 的同模型对和 100.00% 的异模型对，抖动后两者均为 100.00%。这些相等检验拒绝率与 EER 的区别见第 3.5–3.6 节。

![(a) S3 同颜色响应在不同预算下的字符串 MMD 与正则化能量 EER；(b) 持出集 E 的同模型拒绝率：原始与中心化冻结规则，以及 $p\le0.05$ 的逐次审计能量置换检验。FAR 均为零；抖动结果平均十个固定种子。](../figs/fig5_geometry_and_calibration.pdf)


**RGB 输出模态。** S3 中，精确 CSS 命名色在无锚点、语义和偏好响应中分别占 14.25%、49.29% 和 64.89%，重复半字节编码则占偏好响应的 23.85%。常见颜色字面量与结构化编码习惯由此构成不同的行为模态，体现了预训练阶段前端代码与网页样式表语料对输出分布的塑造（图 2），使概率质量集中于 $\Omega_{\mathrm{RGB}}$ 中因模型而异的区域。

### 5.5 持出、纵向与跨网关迁移（Dataset E 与 Study S1）

**持出迁移。** Dataset E 包含 10 个不在 B 中的模型，采集时间晚于 A 的中位间隔为 6.74 小时。迁移冻结 B3v3 阈值后，$D_{\mathrm{hyb}}$ 在 E 上的 FRR/FAR 为 10.00%/0.00%（$\tau=0.348407$），原始 $\tilde D_{\mathrm{E-reg}}$ 为 30.00%/0.00%（$\tau=0.148017$，重扫 EER 为 10.00%）。

**纵向与跨网关审计（S1）。** 在相隔 $21.07\text{--}21.32$ 天（中位数 21.32 天）的两次观测中，我们通过 Cloudflare AI Gateway（CF）与 OpenRouter（OR）复审了 14 个按服务商声明标识的端点——包括 B 的 10 个开发模型（`CF0` 与 B 标定共享 1,200 条注册记录）及 4 个独立于 B 的持出集 E 模型（`heldout4`；二项上界见第 5.7 节）——覆盖 20 个双语单元、每单元六次重复（3,360 次调用，有效率 99.23% 与 99.46%）。表 4 在冻结 B3v3 阈值下评估 6v6 得分（预算匹配的 B6v6 见表 5，其中原始 $\mathrm{CF0}\rightarrow\mathrm{OR21}$ 拒绝 `cf-qwen2.5-coder-32b`，对应 `heldout4` 原始 FRR 为 1/4 = 25.00%、中心化后为 0.00%）。相对切片内的 12 个冒充对（0.00% FAR），将 4 个持出参考与全部 13 个异模型候选配对（$4\times 13 = 52$ 个开放集冒充对）时，原始 B3v3 在 $\mathrm{CF0}\rightarrow\mathrm{CF21}$ 上产生 1/52（1.92%）FAR（`gw-gpt-4.1`$\rightarrow$`gw-gpt-4o`，得分 $0.1336$），中心化或 B6v6 下均为 0.00%。

**表 4：Study S1 纵向（$T+21.32\mathrm d$）与 Cloudflare $\leftrightarrow$ OpenRouter 跨网关核验（14 个正例对与 182 个冒充对）**

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

---

**注册自离散度校正。** 中心化 $\Delta_D=D-\alpha\mu_{\mathrm{self}}$（$\alpha=1$）将 B3v3 原始/中心化阈值设为 0.148017/0.073044（B6v6 为 0.113100/0.060830），降低了清洁 E 的 FRR、纵向 S1 的 FAR 以及 B8v7 下 50% 混合路由的误受率（31.11% 降至 14.44%，补充材料 L）；由于等价规则 $D\le\tau_{\mathrm{self}}+\mu_{\mathrm{self}}(M^*)$ 未增加查询侧噪声余量，抖动 E 的冻结 FRR 相应升高（表 5）。

**表 5：正则化能量的冻结阈值迁移；Self 为仅在 B 选择的 $\alpha=1$**

<!-- BENCH_TABLE_calibration -->
| 条件 | B calibration | Raw FRR / FAR | Self FRR / FAR |
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

**身份排序、冻结阈值与严格相等检验。** 分层 Székely–Rizzo 检验在 E 上给出 0.00% 清洁 FRR、18.00% 抖动 FRR 和 0.00% FAR（图 5(b)）。在 S1 的 CF0→CF21、CF21→OR21 和 CF0→OR21 路径上，严格分布相等检验（$p\le0.05$）对声明同模型对分别拒绝 7.14%、28.57% 和 42.86%（能量）及 7.14%、21.43% 和 28.57%（Color MMD-U；异模型对拒绝率均为 100%；在无 `reasoning.effort` 覆盖的九个标准端点上，能量仍拒绝 22.22% 与 44.44%，补充材料 K）。相比之下，$\tilde D_{\mathrm{E-reg}}$、$D_{\mathrm{RM}}$、$D_{\mathrm{hyb}}$ 以及原始字符串 Color MMD-U 在全部 14 个端点及子组上的身份排序 EER 均为 0.00%，冻结 FAR/FRR 亦保持低位（表 4–5），与连续及多尺度 RGB 几何在浅层有限样本（表 2–3）、跨异构服务栈（第 5.6 节）及受控数值扰动（第 5.4 与 6.1 节）上的增益形成互补。

### 5.6 多提供商服务栈与精度配置（Study S2）

Study S2 审计 18 个端点，覆盖六个开放权重检查点、每个检查点各三个提供商，涉及 12 个锁定的云端后端（DeepInfra、Parasail、Cloudflare、Groq LPU、SiliconFlow、AtlasCloud、Mistral、Venice、DekaLLM、Crusoe、Fireworks 和 CoreWeave），全部 2,160 次已确认调用均关闭回退。服务配置包括匹配 `fp8`、Fireworks `int4` 与 CoreWeave `bf16`、DeepInfra `fp4` 与 SiliconFlow `fp8`，以及 Groq LPU 与 GPU `fp8`（按精度分层的详细结果见补充材料 J）。

S2 将同检查点跨供应商对作为检查点一致性正例，将高精度到低比特查询作为精度一致性异常。精度标签来自采集配置；LPU 与 official 端点单列为未指定类别，每组保留合格的同检查点参考和全部异检查点参考。以 20 个有向高精度跨供应商对作为对照，四个高精度到低比特对的混合量 AUC/EER 为 0.8250/30.00%，能量为 0.5250/50.00%，体现了后端容忍与精度敏感性的取舍。

跨 S2 供应商，$D_{\mathrm{hyb}}$ 给出 5.93% EER 和 17/18 组别匹配，正则化能量对应 16.67% 和 16/18。在相同的 20 单元、6v6 协议下，Color MMD-U 的 EER 也为 16.67%；在 $p\le0.05$ 时，它拒绝 41.67% 的同检查点对和 100.00% 的异检查点对，3v3 EER 为 19.78%。组合类别与几何信息改善了该队列的区分，支持用混合量匹配第三方后端上的开放权重检查点。

### 5.7 超参数敏感性与 bootstrap 不确定性

在不重新调参的情况下，所有测试配置在 B 上均保持 0.00% EER；在 E 上，$\tilde D_{\mathrm{E-reg}}$ 跨 $\delta_0\in\{2,5,10,15,25,50\}$ 的 EER 为 0.00%–10.00%（图 3(c) 插图），$D_{\mathrm{RM}}$ 跨 $\delta_0$、$w\in\{24,32,48,64\}$ 及软体素权重 $\{0.4,0.5,0.6\}$ 网格为 4.44%–10.00%，将 $D_{\mathrm{hyb}}$ 单个混合权重扰动 $\pm0.10$ 时为 3.33%–4.44%。补充材料 H 报告以身份重复次数加权的 2,000 次 $\tilde D_{\mathrm{E-reg}}$ 模型聚类 bootstrap 区间（种子 20261111）。对于 S1 的四模型持出子集，零宽 bootstrap 区间反映该小规模队列（$n=4$）上的零经验错误而非紧总体上界（补充材料 H），说明认证严格错误率上限仍需更大的持出模型池。

### 5.8 能量与混合量的正则化消融

在固定权重与样本的对照中（补充材料 B），混合量正则化提高了 A、E、S2 6v6 和 S3 的 EER，使 C P0→P2 从 10.00% 降至 7.78%，并保留 B 两种预算及 S1 三条路径的零 EER。能量正则化也体现了平滑性与区分能力的取舍：E 的 EER 从 0.00% 升至 10.00%。

CIELAB 敏感性对照（补充材料 A）在清洁与 $\pm8$ RGB 抖动下均保持完整 B 的 0.00% EER 和 E 的 10.00% EER；S3 的 RGB100 与 CIELAB EER 分别为 0.00% 和 0.53%。这一结果支持直接采用 RGB，并显示总体可辨识性与有限样本排序是不同性质。

### 5.9 同家族候选替代

跨厂商差异比同一提供商谱系内的模型更容易分离，因此表 6 在保留全部真实正例对的同时，单独分析共享声明模型家族的负例对。Dataset A 包含 604 个有向同家族负例（584 个同厂商负例和 122 个同子谱系负例）。在 A 的浅层 3v3 采样（$8\times6$）下，将负例限制在同家族内，会使 $\tilde D_{\mathrm{E-reg}}$ 的 EER 从 5.36% 升至 10.10%（同厂商为 10.45%），$D_{\mathrm{hyb}}$ 则从 7.14% 升至 12.42%。当探针覆盖增加到 B 的 $20\times6$ 或 S3 的 $10\times30$ 时，正则化能量仍保持 0.00% 同家族 EER，协议匹配的 $\mathrm B\rightarrow\mathrm E$ 迁移也保持 0.00% 同家族 FAR。因此，在确定浅层监测预算时，必须评估声明厂商家族内部的候选替代模型。

**表 6：各队列全配对与同家族线性 EER 对比**

<!-- AUDIT_TABLE_family -->
| 队列 | 同家族负例 | 能量 $\tilde D_{\mathrm{E-reg}}$：全配对 EER | 能量：同家族 EER | 混合量 $D_{\mathrm{hyb}}$：全配对 EER | 混合量：同家族 EER |
| --- | --- | --- | --- | --- | --- |
| A ($8\times6$) | 604 | 5.36% | 10.10% | 7.14% | 12.42% |
| B ($20\times6$) | 20 | 0.00% | 0.00% | 0.00% | 0.00% |
| B ($40\times15$) | 20 | 0.00% | 0.00% | 0.00% | 0.00% |
| E ($20\times6$)$^*$ | 20 | 10.00% | 10.00% | 4.44% | 10.00% |
| S3 ($10\times30$) | 38 | 0.00% | 0.00% | 0.53% | 5.00% |
<!-- /AUDIT_TABLE_family -->

**表注：** $^*$在协议匹配的 $\mathrm B(20\times6)\rightarrow\mathrm E(20\times6)$ 冻结阈值下，同家族 FRR/FAR 对原始能量为 30.00%/0.00%（中心化后为 10.00%/0.00%），对 $D_{\mathrm{hyb}}$ 为 10.00%/0.00%。

### 5.10 有限样本 V 与 U 能量估计量

表 5 保留全部满足 $n_c,m_c\ge 1$ 的共享单元（E 上原始与中心化清洁 V FRR 分别为 3/10 与 1/10），而表 7 在相同满足 $n_c,m_c\ge 2$ 的有效单元上比较 V 与 U 统计量估计量（B 保留 18–20 个单元；E 剔除 `gw-gemini-3.6-flash` 上的 `rgb_warm|zh` 后保留 19–20 个单元，在各自从 B 拟合的 B3v3 阈值下对应 2/10 原始与 1/10 中心化清洁 V FRR）。固定 $\delta_0=15$ 不变，将有偏 V 分子替换为无偏 U 分子使清洁 E 上的 EER 从 10.00% 降至 0.00%–1.11%、清洁冻结 FRR 从 20.00% 降至 10.00%，同时省去 256 次注册 bootstrap（未正则化 V 比值 $\bar D_{\mathrm E}$ 在清洁 E 上亦达到 0.00% EER 与 10.00% 冻结 FRR，但在抖动下 FRR 为 100.00%、在 `CF0 → CF21` B3v3 下 FAR 为 6.04%）。在 E 的 $\pm8$ 抖动下，U 分子、带符号 U 比值与截断 U 比值的重扫 EER 分别为 8.89%、1.11% 与 2.44%，冻结 FRR 分别为 13.00%、37.00% 与 21.00%（经验 FAR 均为 0.00%），需分别解读排序精度与固定阈值决策；在同期跨网关 S1（$\mathrm{CF21}\rightarrow\mathrm{OR21}$）上，带符号 U 比值的 FRR 从不匹配 B3v3 阈值下的 21.43% 降至预算匹配 B6v6 阈值下的 0.00%。

**表 7：E 上匹配的 V/U 对照；全部 FAR 为零**

<!-- AUDIT_TABLE_u_energy -->
| 估计量 | Clean EER | Clean FRR | Jitter EER | Jitter FRR |
| --- | --- | --- | --- | --- |
| V regularized | 10.00% | 20.00% | 10.00% | 51.00% |
| V self-centered | 4.44% | 10.00% | 6.56% | 68.00% |
| U numerator | 4.44% | 10.00% | 8.89% | 13.00% |
| U signed ratio | 0.00% | 10.00% | 1.11% | 37.00% |
| U clipped ratio | 1.11% | 10.00% | 2.44% | 21.00% |
<!-- /AUDIT_TABLE_u_energy -->

**表注：** 表 7 要求每单元两侧有效数满足 $n_c, m_c \ge 2$（剔除 `gw-gemini-3.6-flash` 上的 `rgb_warm|zh`，在 E 上保留 19–20 个单元；在匹配 B3v3 阈值下原始与中心化清洁 V FRR 为 2/10 与 1/10），而表 5 保留全部 $n_c, m_c \ge 1$ 的共享单元（E 上 20/20 个单元，对应 3/10 与 1/10）。

## 6 服务监测与受控干预

### 6.1 数值扰动敏感性与响应复用

为将坐标层面的数值敏感性与 S1–S2 中的真实服务变异剥离开，表 S8（补充材料 L）在 Dataset B（$40\times15$）上施加内存中的合成 RGB 扰动，作为冻结 B8v7 阈值下的受控数值连续性压力测试。表 S8 的全部七个原始得分行均保持 0.00% 重扫 EER 和 0.00% 冻结 FAR（自中心化 $\pm8$ 恒定偏移的重扫 EER 为 1.11%–2.22%，原始 $D_{\mathrm{hyb-reg}}$ 在 $-8$ 偏移下为 10.00%）；原始 $\tilde D_{\mathrm{E-reg}}$ 在 $\pm1$ 与 $\pm8$ 均匀抖动下保持 0.00% 冻结 FRR（对照 $D_{\mathrm{hyb-reg}}$ 在 $\pm8$ 下的 100.00% FRR，以及 $\pm15$ 抖动、$\pm8$ 偏移或步长 32 通道量化下的 56.00%–100.00% 能量 FRR），而注册中心化因未增加查询噪声余量，使 B 抖动 FRR 升至 11.00%（$\pm8$）与 89.00%（$\pm15$），与持出集 E 表现一致（表 5）。

由于边际分布得分仅依赖每单元无序输出，常数质心重放会被零熵筛查直接剔除，而从公开或暴露的参考直方图中循环重放或独立同分布重采样保持在 $\hat P_{\mathrm{ref}}$ 的有限样本抽样容差内（在 B 上五项指标 $D_{\mathrm{hex}},D_{\mathrm{vox}},D_{\mathrm{RM}},\tilde D_{\mathrm{E-reg}},D_{\mathrm{hyb}}$ 实测均记录到 100% 接受；补充材料 L）。因此需对提示集保密并轮换以防范静态查找表（Dataset C 单套 64 次调用模板在每个参考模型上的重注册开销低于 $10{,}000$ Token）。

### 6.2 结构化金丝雀探针与固定网关规则（S4）

针对检测字面格式标记、单字指令或裸色号输出的简单网关正则，显式 HuePrint 与 Bruckner 探针均以 100.00% 触发指令规则，而宽泛十六进制与颜色词过滤在 100 条作者构造的合成正常开发请求中产生 26.00% 误报（其中 40 条前端 CSS 任务误报率为 65.00%）。为评估贴近真实负载的模式约束请求，S4a 将探针嵌入单行 CSS 属性与单字段 JSON 设计令牌（20 个模型、16 个双语探针、10 次重复，共 3,200 次调用；5v5），S4b 则保留带指令的隐式措辞（6 次重复，1,920 次调用；3v3；表 8）。

**表 8：Study S4 网关双端规则未触发率与 20 模型隐式核验精度对比（20 正例 vs. 380 冒充对）**

<!-- RGB_TABLE_9 -->
| 探针及协议 | 输入未触发率 | 输出未触发率 | 有效且未触发 | $\tilde D_{\mathrm{E-reg}}$: Top-1 / AUC / EER | $D_{\mathrm{hyb}}$: Top-1 / AUC / EER |
| --- | --- | --- | --- | --- | --- |
| S3a (10 probes; 15v15) | 0.00% | 0.73% | 0.00% | 100.00% / 1.0000 / 0.00% | 100.00% / 0.9997 / 0.53% |
| S4a (5v5) | 100.00% | 99.97% | 99.75% (3192/3200) | 100.00% / 1.0000 / 0.00% | 100.00% / 0.9987 / 1.58% |
| S4b (3v3) | 0.00% | 2.50% | 0.00% | 100.00% / 0.9917 / 5.00% | 100.00% / 0.9683 / 8.95% |
| S3a → S4b (6v6) | — | — | — | 65.00% / 0.9154 / 15.00% | 85.00% / 0.9626 / 13.68% |
<!-- /RGB_TABLE_9 -->

**表注：** 有效且未触发要求颜色解析有效且输入、输出规则均不触发；输入/输出未触发率报告各阶段边际通过率，S4b 含 48/1,920 条输出未触发响应和 26/1,920 条无效解析。`S3a → S4b (6v6)` 评估两者共享的 8 个英文任务单元。

解析器检查颜色提取，不验证完整 CSS/JSON 语法或生产业务副作用。S4a 产生 99.75% 的有效且未触发响应（3,192/3,200），同池能量与混合量 EER 分别为 0.00% 和 1.58%（仅移除 API 推理元数据后 $\tilde D_{\mathrm{E-reg}}$ 仍为 0.00%，$D_{\mathrm{hyb}}$ 升至 2.89%，若再将 `numeric_only` 合并入 `upper` 则为 2.63%；补充材料 B）。S3a→S4b 更高的跨形式误差进一步说明，参考应匹配隐式提示池。第 7.1 节讨论这些静态规则之外的会话级检测。

---

### 6.3 混合路由检出曲线

为评估部分回退路由，使用 20 个固定种子、无放回抽样模拟独立 Bernoulli 请求混合：以概率 $q\in\{0,0.2,0.4,0.5,0.6,0.8,1\}$ 路由至声明后端，以回退率 $\lambda=1-q$ 路由至替代后端 $R$（图 6；B 的 $40\times 7$ 查询池每单元恰有 7 条响应，故 $q\in\{0,1\}$ 端点跨种子确定不变）。每个协议均使用在 B 上冻结的预算匹配能量阈值 $\tau_{\mathrm{mid}}$。

在 20% 回退（$q=0.8,\lambda=0.2$）时，二十种子重抽样下的冻结阈值检出率在 B 的 60 次调用方案上为 11.28%（清洁 FRR 1.00%），280 次调用方案上为 0.33%（清洁 FRR 0.00%）；S3 的 30 和 70 次调用方案分别为 55.97% 和 12.45%（清洁 FRR 39.00% 和 3.75%）。当 $Q_\lambda=(1-\lambda)P+\lambda R$ 时，未归一化总体平方能量满足 $\mathcal E^2(P,Q_\lambda)=\lambda^2\mathcal E^2(P,R)$（$\lambda=0.2$ 时 $\lambda^2=0.04$）；记 $d_{AB}=\mathbb E\|X-Y\|_2$ 为两分布独立抽样间的期望距离，则正则化总体分数为 $\lambda^2\mathcal E^2(P,R)/\{2[(1-\lambda)d_{PP}+\lambda d_{PR}+\delta_0]\}$（对相距 100 个 RGB100 单位的两个点质量，取 $\delta_0=15,\lambda=0.2$ 时分子为完全替代时的 $4\%$，正则化总体分数则为其 $13.14\%$）。不同于该总体比值，冻结 $\tau_{\mathrm{mid}}$ 的经验检出率还取决于有限样本估计量的偏差与方差相对完全替换（$\lambda=1$）标定阈值的位置：$40\times 7$ 同时抑制采样方差与 V 统计量的 $O(1/n+1/m)$ 正偏（第 3.7 节），使 20% 回退得分落在 $\tau_{\mathrm{mid}}$ 以下，而浅层 $10\times 3$ 主要依靠有限样本离散性越过 $\tau_{\mathrm{mid}}$（39.00% 清洁 FRR）。对同一组二十种子混合样本施加分层 999 次置换能量检验（$p\le0.05$）可恢复同网关池的零假设分位数：B（$40\times 7$）上的 20% 回退检出率从 0.33% 升至 33.28%（$\lambda=0.4$ 时达 91.44%；同家族负例为 25.75% 对 0.00%），清洁 FRR 保持 0.00%；S3（$10\times 7$）从 12.45% 升至 17.57%（同家族 16.71% 对 5.00%），清洁 FRR 为 4.50%，且 S3（$10\times 3$）的清洁 FRR 降至 4.75%（表 S9，补充材料 L）。在跨网关 S1 混合（$\mathrm{CF0}\rightarrow\mathrm{OR21}$，$20\times 3$）上，跨网关的注册分布与真实查询分布本身存在差异，因此置换检验对纯声明正例查询（$q=1$）产生 16.07% 拒绝率（6v6 下为 42.86%），说明低 $\lambda$ 监测应配置同网关参考。

![二十个固定种子的离线混合路由。左图：各子采样 3 次与 7 次协议在冻结能量中点阈值 $\tau_{\mathrm{mid}}$（实线，阴影为种子的 5–95 百分位带）及 B $40\times 7$ 的 999 次置换检验（$p\le0.05$，虚线）下对声明/替代混合的拒绝率；右图：$q=1$ 时纯声明模型的清洁误拒率（完整池 S3 $10\times 15$ 的清洁 FRR 为 0.00%）。](../figs/fig6_mixed_routing.pdf)

### 6.4 运行开销

表 9 区分按公开费率估算的 API 费用、根据单请求时延估算的并发墙钟时间，以及实测本地 CPU 评分耗时（均不含一次性注册，详见补充材料 K）。按 2026 年 11 月 13 日采集的 OpenRouter 公开目录费率 [29]——情景 L（0.71/0.71 USD）与情景 G（每百万输入/输出 Token 2.50/10.00 USD）——150 次调用的 S3 颜色查询估算费用中位数为 0.0077 USD（L）至 0.0345 USD（G；其中 19/20 个端点介于 0.0292–0.0432 USD，`s3-deepseek-v3.2` 因未剥离的子提供商推理 Token 为 0.2711 USD；第 4.2 节），60 次调用的 B/E 审计估算费用低于 0.02 USD。按记录的单次请求延迟在理想八工作线程调度下回放，60–150 次调用的网络墙钟时间估算为 49–116 秒；而在三组预加载的 Dataset B 单对样本上（NumPy 2.5.5，不含 API I/O、解析、注册与图库检索），预热后实测本地 CPU 评分耗时中位数在 20 单元 3v3、40 单元 8v7 和 10 单元 8v7 批次上分别为 0.12、0.31 和 0.08 毫秒（$\tilde D_{\mathrm{E-reg}}$），999 次分层能量置换检验分别为 2.39、10.15 和 2.51 毫秒。不同于往返延迟更低的八查询多词元分类器 [16]，HuePrint 在带外异步运行，提供连续参考距离余量与置换检验 $p$ 值。

**表 9：逐端点查询开销的中位数，不含注册**

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

**表注：** 各列分别计算跨端点中位数，费用中位数不必等于输入/输出 Token 中位数代入公式的值。Call p50 是各端点单次请求延迟中位数的中位数；末列按记录时长在理想八工作线程上列表调度估算，并非实测并发墙钟耗时。

## 7 局限性、部署准则与结论

### 7.1 局限性

实验真实标签依赖提供商声明的模型标识符与 API 日志而非密码学权重证明，仅凭端点行为无法确认观察到的后端变更是否获授权；浅层 3v3 单元对分布尾部的采样有限，S1 的四个独立持出身份仍需更大规模的多月跟踪以给出更紧的错误率上界。在 Study S2 中，第三方主机的底层栈与量化配置共同变化，无法单独剥离量化本身的因果效应。此外，在按复杂度分流的级联路由 [1], [2] 或会话突发检测下，独立短探针仅触发低复杂度分支，因此需在实际业务负载中嵌入结构化颜色字段并配合私有提示轮换。

### 7.2 部署准则

调用方应维护版本化审计约定，绑定注册检查点、私有提示集、解析器、最小有效样本规则和查询预算：

1. **度量与估计量选择：** 标准端点监测使用带注册中心化的 $\tilde D_{\mathrm{E-reg}}$，或在每单元有效计数满足 $n,m\ge2$ 时使用可省去 256 次注册 bootstrap 的 U 统计量能量比值（需在匹配的单元预算上标定冻结阈值；带符号与截断形式在 E 上体现排序与抖动阈值敏感性的权衡，见表 7）；匹配异构第三方后端上的开放权重检查点时，采用 $D_{\mathrm{hyb}}$。
2. **阈值标定与两阶段序贯复核：** 允许跨网关或跨时间服务漂移时，在持出的开发队列上冻结 $\tau_{\mathrm{mid}}$ 或 $\tau_{\mathrm{self}}$；对照同网关参考筛查低比例 $\lambda$ 回退混合时，切换为逐次审计的 Székely–Rizzo 置换检验。为避免周期性轮询下的告警疲劳（单次 3v3 窗口 10% 的 FRR 在按小时轮询下会迅速累积），任何 3v3 越界应先升级触发即时 6v6 或 15v15 复核窗口，再上报 SLA 告警。
3. **缓存筛除、封装对齐与参考轮换：** 筛除响应缓存或语义缓存命中（$T=1.0$ 下零熵且延迟低于中位数的 $0.5\times$），通过完全一致的代理系统提示封装完成注册，结合业务任务遥测交叉核实告警，并在约定刷新时轮换私有提示集（单套 64 次调用提示集在每个参考模型上低于 $10{,}000$ Token）。

### 7.3 结论

HuePrint 以估算单次查询费用中位数低于四美分的开销，为聚合式云端 LLM 服务提供黑盒行为一致性信号。在 34,528 条云端响应中，结构化 RGB 协议将每侧 30 次调用的浅预算 EER 在开发队列上从单词题组的 4.52%–5.23% 降至 0.94%–1.00%，在 20 个锁参端点上从 6.25%–8.04% 降至 3.49%–5.00%（更深预算下达 0.00%），连续与多尺度 RGB 距离则同步提升浅层普查与跨供应商后端区分度、容忍三周跨网关漂移并约束坐标扰动偏移。连同统一的 Lipschitz 扰动界、零 bootstrap U 统计量比值、同家族与混合路由基准以及模式约束金丝雀测试，这些结果为固定检查点 MaaS 承诺提供了可落地的调用方持续监测方案。

## 致谢

作者衷心感谢父母与姐姐在整个研究期间于精神和日常生活中给予的坚定支持；同时诚挚感谢云南中医药大学导师 Dr. Vicky Li，引领作者步入计算机科学研究领域。

---

## 参考文献

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

### 补充材料专用文献

[30] R. Lyons, "Distance covariance in metric spaces," *Ann. Probab.*, vol. 41, no. 5, pp. 3284–3305, 2013, doi: 10.1214/12-AOP803.

[31] World Wide Web Consortium, *CSS Color Module Level 4*, Candidate Recommendation Draft, Nov. 3, 2026, sec. 19, "Sample code for color conversions," https://www.w3.org/TR/css-color-4/.

[32] International Commission on Illumination, "CIE 1976 L\*a\*b\* colour space," *International Lighting Vocabulary*, 2nd ed., CIE S 017:2020, entry 17-23-076, 2020.

[33] I. Csiszár, "Information-type measures of difference of probability distributions and indirect observations," *Studia Sci. Math. Hungar.*, vol. 2, pp. 299–318, 1967.

[34] D. M. Endres and J. E. Schindelin, "A new metric for probability distributions," *IEEE Trans. Inf. Theory*, vol. 49, no. 7, pp. 1858–1860, Jul. 2003, doi: 10.1109/TIT.2003.813506.

## 作者简介

**Xiguan He**，现于云南中医药大学信息学院（中国昆明）攻读医学信息工程工学学士学位，研究方向包括云服务保障、大语言模型评估、统计两样本检验与可信人工智能。
