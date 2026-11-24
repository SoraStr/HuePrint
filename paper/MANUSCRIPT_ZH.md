# 空谈无益，亮出颜色：面向聚合式大语言模型服务的低预算一致性审计

**摘要**——将生产负载接入聚合式大语言模型（LLM）代理服务的机构依赖声明的模型标识符，但实际处理每次请求的底层后端配置仍对调用方隐藏。本文提出黑盒审计框架 HuePrint，通过结构化颜色诱导与几何分布比较核验代理端点的行为一致性，无需模型权重或词元概率。在覆盖 56 个端点与 12 个后端的 38,688 条云端响应中，HuePrint 将单侧 30 次调用的等错误率（EER）相对单词基线在开发模型上从 4.52%–5.23% 降至 0.94%–1.00%，在 20 个锁参端点上从 6.25%–8.04% 降至 3.49%–5.00%，并在单侧 60–150 次调用下达到 0.00%。在这 20 个端点上，单侧 30 次调用的 HuePrint 在全部 10 种均衡划分上的同家族平均 EER 为 5.18%（范围 0.00%–7.89%），优于开放集 LLMmap（10.53%–34.39%，1–3 条轨迹）与等成本长文本核方法（11.09%–19.47%）；相比 LLMmap，HuePrint 避免了触发安全审查的探针，本地评分速度快出 15,000 倍以上。正则化 RGB 能量降低了浅层普查 EER（5.36%，优于精确色号的 10.71% 与字符串 MMD 的 6.42%），混合评分将跨供应商 EER 从 16.67% 降至 5.93%。在离线回放中，两阶段复核将 100 个同标签窗口的误报从 14 个压至 1 个，并标记 186/190 个同家族替换窗口，期望查询成本低于 1 美分。

**关键词**——服务计算，模型即服务，服务等级监测，API 代理，行为一致性，能量统计量。

---

## 1 引言

通过聚合服务访问大语言模型（LLM）的应用在请求中指定模型标识符，而实际处理每次请求的底层后端则由聚合服务选择 [1]–[3]。当服务等级协议（SLA）约定服务商绑定固定模型检查点时，调用方如何仅凭 API 界面核验该契约？在线率、延迟与账单记录刻画了服务的运行状态，却几乎无法直接证明究竟是哪个模型生成了响应 [4]–[6]。另一个现实难点在于，即便底层检查点保持不变，网关提示封装或输出格式的变动也会改变调用方观测到的返回结果。

本文提出用于监测代理式 LLM 端点行为一致性的低预算方法 HuePrint。HuePrint 通过多语种短提示诱导模型输出十六进制色号或十进制 RGB 三元组。在严苛查询预算下，色彩响应具有一项实用性质：两次采样虽可能给出不同色号，但在 RGB 空间中却处于邻近区域。HuePrint 利用这些空间距离，将新采集响应与可信参考端点建立的基准画像进行比对；若初始得分越过预设阈值，监测器将采集第二批响应进行复核，随后再将端点标记为待排查对象。

两项设计共同决定了 HuePrint 的样本效率。多语种颜色提示将三通道坐标与语义先验结合，相比单词题组 [7] 拓宽了单题有效输出支撑，使 20 个锁参端点的等错误率（EER）在单侧 30 次调用下达到 3.49%–5.00%，并在单侧 60–150 次调用下压至 0.00%。在此坐标上，正则化 RGB 能量（$\tilde D_{\mathrm{E-reg}}$）在 56 端点浅层普查中以 5.36% EER 将家族归属率从 42.00% 提升至 70.00%，混合评分（$D_{\mathrm{hyb}}$）将 12 主机跨供应商 EER 压至 5.93%，中心化 B6v6 阈值则在相隔 21 天的跨网关迁移中以 0/14 误报（对比严格相等性检验 6/14 误拒）检出全部 182/182 次替换。

本文作出三项贡献：

- **端到端模型即服务（MaaS）一致性协议：** 基于 38,688 条真实云端响应（数据集 A–E 与线上研究 S1–S5），建立涵盖参考注册、私有提示池子采样、冻结阈值标定、两阶段序贯复核与参考刷新的版本化审计约定。
- **扰动界与有限样本估计量分析：** 证明离散 Jensen–Shannon 散度（JSD）的支撑逃逸下界与正则化能量比值的 Lipschitz 稳定性上界，并系统对比有限样本 V 统计量偏置、注册自离散度中心化与零 bootstrap U 统计量能量比值。
- **跨云后端与竞品实证基准：** 在 56 个端点与 12 个锁定服务栈上，将 HuePrint 与开放集 LLMmap 及原生长文本相等性检验正面对照，并评估同家族替代、分比例回退路由、CSS/JSON 金丝雀探针及单次审计开销。

---

## 2 相关工作与服务模型

### 2.1 云服务保障与大模型服务聚合

**SLA 治理与代理路由。** FrugalGPT [1] 与 RouteLLM [2] 通过模型级联和偏好学习路由器优化提供商侧的成本与质量取舍，面向 LLM 的 QoS 代理 [3] 则结合 SLA 约束路由与 CUSUM 漂移跟踪。但在多租户代理场景下，调用方无法观察服务商内部调度表，需要低预算主动探测（金丝雀测试）来核验固定检查点 SLA 是否遭遇静默降级替换。

**服务测试与序贯漂移监测。** 云 API 保障涵盖 LLM 引导的 REST API 模糊测试（RESTLess [8]）、多模态微服务异常检测（UAC-AD [9]）以及概念漂移触发的边缘服务恢复 [10]。白盒遥测与模糊测试主要检查主机指标或接口模式错误，HuePrint 则通过标准聊天补全接口审计黑盒输出分布，把良性服务漂移与后端变更区分开。

**模型与 API 审计。** 服务端水印、指令后门与知识产权指纹 [11]–[13] 依赖模型拥有者配合处理盗用争议，无法直接审计第三方在线端点。被动文本归属 [14], [15] 依赖长文本输出。主动神经指纹方法（LLMmap [16]、TRAP [17]）使用约 8 次多词元查询；LLMmap 通过 560M 参数编码器支持闭集与开放集模板匹配，但面对新检查点仍需在线注册，且依赖注入或安全提示。Gao 等人 [4] 采用 Hamming 与 k-spectrum 字符串核检验长文本分布相等；Cai 等人 [5] 研究黑盒与对数概率替换检验，并讨论自适应路由与硬件飞地；Zhu 等人 [6] 依赖白盒参考词元概率。开放选择空间上的有偏先验 [18]–[21] 使输出偏好成为自然的一致性信号，尽管共享预训练组件仍会带来跨模型相关性 [22], [23]。Bruckner [7] 在禁用思考与短词元上限下对 40 道无锚点单词提示计算离散 JSD（165 个模型上 7.3% EER）。然而最新研究 [24] 表明，即便启用显式禁思考开关与仅答指令，开放生成仍会泄漏答案前推理：短上限可能在推理中途截断目标词，内联引导语会混入无锚点单词，而离散 JSD 对漂移后的词给出零相似度。HuePrint 则在适度补全上限下诱导自定界的 `#RRGGBB` 与 RGB 字面量，同时保持干净的正则提取与 $[0,100]^3$ 邻域几何（表 1）。

**表 1：黑盒 LLM 审计方法对比**

| 方法 | 访问条件 / 参考 | 探针类型 | 查询预算 | 漂移 / 扰动机制 | 护栏触发 / 本地 CPU |
| --- | --- | --- | --- | --- | --- |
| Gao et al. [4] | 仅文本；配对样本 | 长文本续写 | 30–50 次（64 tok.） | 严格相等（$p\le0.05$） | 温和提示；~0.2 ms |
| Cai et al. [5] | 文本 / 对数概率 | 任务提示 | 多查询批次 | 假设检验 | 温和提示；轻量 CPU |
| Zhu et al. [6] | 白盒参考概率 | 通用提示 | 秩均匀批次 | 严格相等 | 温和提示；需参考 logits |
| Bruckner [7] | 仅文本；注册参考 | 40 道单词提示 | 30–150 次（1–2 tok.） | 离散 JSD | 含格式指令；<1 ms |
| LLMmap [16] | 仅文本；开放集模板 | 8 道注入/安全/身份题 | 8–24 次（100 tok.） | 对比欧氏距离 | 4/8 触发规则；E5 需 4.7 s |
| TRAP [17] | 仅文本；优化后缀 | 对抗后缀 | 定向查询 | 后缀匹配 | 对抗字符串；高优化开销 |
| **HuePrint** | **仅文本；注册参考** | **RGB/hex 与 CSS/JSON** | **30–150 次（~7 tok.）** | **Lipschitz + 置换检验** | **S4a 0% 触发；0.12 ms** |

### 2.2 服务聚合架构与审计约定

**角色与可观测量。** 调用方监测器通过可信参考端点 $E_{\mathrm{ref}}(M^*)$ 注册声明检查点 $M^*$，在 $k$ 个任务—语言单元上审计代理端点 $E$，每单元采集 $n_B$ 条补全（有效解析数为 $n=|U|, m=|V|$；图 1）。Cloudflare AI Gateway 与 OpenRouter 等网关在标准聊天补全接口下提供可观测路由路径，不暴露模型权重、隐藏状态、对数概率或服务端随机种子。

**审计约定与部署混杂因素。** 审计约定将参考画像、私有提示池、采样预算、解析器及冻结阈值版本绑定至固定检查点 SLA（区别于按设计将短提示分流至轻量层的公开级联路由 [1], [2]）。行为一致性无需硬件飞地即可补足 QoS 遥测 [5]，并区分检查点身份与服务位宽。两类网关机制需在运行中显式处理：响应缓存或语义缓存会在 $T=1.0$ 下令随机抽样坍缩为重复输出（通过零熵配合低于中位数的延迟筛除）；代理商注入的系统提示封装会偏移颜色先验，需要通过一致的网关封装完成注册。

**服务变化情景与生命周期。** 本文评估四类运行情景：（1）固定模型标识符背后的完整检查点替换；（2）不变标签下的跨主机服务与低比特精度执行，此时跨主机检查点核验要求对服务位宽保持容忍不变；（3）按请求概率混合声明后端与替代后端的回退路由；（4）基于参考库查表或直方图重采样的响应复用。得分低于冻结阈值 $\tau$ 时判定**接受**；越界时先触发两阶段复核再进入**调查**，获授权的版本更新则启动参考刷新。

![代理式 LLM 服务的调用方审计流程。注册参考与协议匹配探针共同驱动冻结一致性判定；配置变更需排查并刷新参考。](../figs/fig1_service_audit.pdf)

---

## 3 方法论与扰动分析

### 3.1 探针、解析与 RGB 坐标

核心探针集将 10 项颜色任务与四种语言（en、zh、ru、ar）正交组合为 40 个任务—语言单元，在十六进制（`#RRGGBB`）与 RGB 语法下请求随机色、偏爱色、暖色、自然、海洋、平静与夜空色（图 2；例如 *"Pick a random color. Reply with only its #RRGGBB hex code."*），诱导预训练 CSS 色值字面量与后训练调色板先验在 $\Omega_{\mathrm{RGB}}$ 上聚集。研究 S4 将颜色选择嵌入单行 CSS 自定义属性（如 `--brand-primary`）与单字段 JSON 设计令牌；补充材料 C–F 给出完整端点清单与逐字提示原文。解析器剥离推理字段与内联标签后，提取首个合规 `#RRGGBB` 色号或经范围校验的 $0\text{--}255$ RGB 三元组，失败记为无效；有效解析保留大写规范色号、坐标、语法标签及严格仅含色号标记。

对 sRGB 色号 $\mathbf c\in\Omega=\{0,\ldots,255\}^3$ [25]，定义线性重缩放 $\mathbf x=T(\mathbf c)=100\mathbf c/255\in\Omega_{\mathrm{RGB}}=[0,100]^3$；裁剪扰动 $\mathbf c'=\operatorname{clip}_{[0,255]^3}(\mathbf c+\boldsymbol\eta)$（$\|\boldsymbol\eta\|_\infty\le a$）满足 $\|T(\mathbf c')-T(\mathbf c)\|_2\le 100\sqrt3 a/255$。RGB100 仅作线性尺度变换，不执行伽马逆变换或 Lab 转换，用于全部连续距离；硬体素仍使用原始通道整数单位。补充材料 A 对比统一缩放的 CIELAB 坐标，补充材料 B 给出权重正则化消融。

![随机色探针上按确定性规则选出的五个家族代表模型。标记面积表示输出频次，填充色为真实 RGB，两幅投影展示 (R, G) 与 (B, G)；右侧为匹配端点在随机颜色单词探针上的词分布（按总概率降序排列）。](../figs/fig2_rgb_geometry_vs_words.pdf)

### 3.2 离散 JSD 与支撑逃逸

记 $M=(P+Q)/2$，以 2 为底的 Jensen–Shannon 散度（JSD）[26] 为
$$D_{\mathrm{JSD}}(P\|Q)=\tfrac12\sum_xP(x)\log_2\frac{P(x)}{M(x)}+\tfrac12\sum_xQ(x)\log_2\frac{Q(x)}{M(x)},$$
求和略去零质量项，满足 $0\le D_{\mathrm{JSD}}(P\|Q)\le 1$，且取等号 $1$ 当且仅当 $\operatorname{supp}(P)\cap\operatorname{supp}(Q)=\emptyset$。$D_{\mathrm{hex}}$ 使用精确 RGB 色号（$256^3$ 类），$D_{\mathrm{vox}}$ 按 $(\lfloor R/32\rfloor,\lfloor G/32\rfloor,\lfloor B/32\rfloor)$ 分箱（$8^3$ 类）。

**命题 1（支撑逃逸下界）**。*固定支撑集大小为 $r$ 的参考经验分布 $P_{\mathrm{ref}}$，令 $Q^{\mathrm{jitter}}$ 表示源颜色 $\mathbf c\sim P_{\mathrm{src}}$ 在上述裁剪变换下叠加独立均匀整数噪声 $\{-a,\ldots,a\}^3$（$a\ge1$）所得分布。对 $n$ 次独立同分布抽样 $\hat Q_n^{\mathrm{jitter}}\sim Q^{\mathrm{jitter}}$，若逃离参考支撑集的概率满足 $Q^{\mathrm{jitter}}(\Omega\setminus\operatorname{supp}(P_{\mathrm{ref}}))\ge t\in[0,1]$，则*
$$\mathbb E[D_{\mathrm{hex}}(P_{\mathrm{ref}},\hat Q_n^{\mathrm{jitter}})]\ge D_{\mathrm{JSD}}(P_{\mathrm{ref}}\|Q^{\mathrm{jitter}})\ge\psi(t),$$
$$\psi(t)=\tfrac12\log_2\frac2{2-t}+\tfrac{1-t}{2}\log_2\frac{2(1-t)}{2-t}+\tfrac t2\ge\tfrac t2,$$
*其中 $\psi$ 严格递增，按连续性有 $\psi(1)=1$，且总体下界紧确。当 $\operatorname{supp}(P_{\mathrm{src}})\subseteq\{a,\ldots,255-a\}^3$ 时，可取 $t=\max(0,1-r/(2a+1)^3)$。*

以各单元观测到的查询颜色为条件，对每次抽样施加一次随机裁剪偏移，图 3(a) 由经验查询直方图的逃逸概率计算式 (1)。命题 1 刻画了坐标后处理或浅层稀疏单元互不重叠时的行为：只要邻近 RGB 色号落出注册离散支撑集，同模型正例的 $D_{\mathrm{hex}}$ 就会迅速趋近 $1$，而经验 EER 还取决于冒充分布的位置（图 3(c)；证明见补充材料 G）。

### 3.3 正则化 RGB 能量与混合复合量

对非空 RGB100 点云 $U,V$，记 $n=|U|$、$m=|V|$，定义
$$d_{UV}=\frac{\sum_{i,j}\|u_i-v_j\|_2}{nm},\qquad d_{UU}=\frac{\sum_{i,i'}\|u_i-u_{i'}\|_2}{n^2},$$
$d_{VV}$ 定义同理，组内均值包含对角项。V 统计量平方能量为 $\widehat{\mathcal E}_V^2=2d_{UV}-d_{UU}-d_{VV}$。对 $\mathbb R^3$ 上一阶矩有限的分布，总体平方能量满足 $\mathcal E^2(\mu,\nu)\ge 0$，且等于 $0$ 当且仅当 $\mu=\nu$ [27], [28]；作用于经验测度时有 $0\le\widehat{\mathcal E}_V^2\le 2d_{UV}$。据此定义
$$\bar D_{\mathrm E}=\frac{\widehat{\mathcal E}_V^2}{2d_{UV}},\qquad\tilde D_{\mathrm{E-reg}}=\frac{\widehat{\mathcal E}_V^2}{2d_{UV}+2\delta_0},$$
其中 $\delta_0=15$（RGB100 长度单位），$d_{UV}=0$ 时令 $\bar D_{\mathrm E}=0$。浮点求值将 $[\widehat{\mathcal E}_V^2]_+=\max(0,\widehat{\mathcal E}_V^2)$ 截断至 $[0,2d_{UV}]$，并在 $d_{UV}<10^{-12}$ 时置零。对相距 $\epsilon>0$ 的两个常值点云（$d_{UU}=d_{VV}=0, d_{UV}=\epsilon$），$\bar D_{\mathrm E}$ 从 $\epsilon=0$ 处的 $0$ 直接跳变至 $1$，$\tilde D_{\mathrm{E-reg}}=\epsilon/(\epsilon+\delta_0)\le\epsilon/\delta_0$ 则平滑过渡。

**命题 2（正则化能量比值的 Lipschitz 稳定性）**。*对非空点云 $U,V\subset\mathbb R^3$、$\delta_0>0$、跨组均距 $d=d_{UV}$，以及含对角项（$\tilde D_{\mathrm{E-reg}}$）或不含对角项（$|U|,|V|\ge 2$，第 3.4 节）计算的组内均距均值 $h$，令 $F(d,h)=(d-h)/(d+\delta_0)$。若将 $V$ 中每点沿任意方向移动欧氏距离至多 $\epsilon$，则 $F(d,h)$ 与 $[F(d,h)]_+$ 的变化不超过 $2\epsilon/\delta_0$；若同时将 $U$ 与 $V$ 中每点移动至多 $\epsilon$，变化不超过 $4\epsilon/\delta_0$。*

对取值于 $[0,1)$ 的截断比值，逐通道偏移 $a$ 给出单侧变化上界 $\min\{1, 200\sqrt{3}a/(255\delta_0)\}$（$\delta_0=15$ 时 $a=1$ 为 $0.0906$，$a=8$ 为 $0.7245$），并在 $d_{UV}\to 0$ 时保持连续。命题 2 允许各点取最坏方向位移，图 3(b) 中的独立均匀抖动则远低于该上界。正则化混合量（$D_{\mathrm{hyb-reg}}$）、三线性软直方图及高斯 Bures–Wasserstein 对照 [29] 在浅层或多峰点云上均逊于 $\tilde D_{\mathrm{E-reg}}$（详见补充材料 B 与 G）。

![队列 B 与 E 上每个扰动半径采用十个固定随机种子。(a) 精确色号 JSD 与考虑裁剪边界的条件期望下界（命题 1）；(b) 正则化能量实测得分变化与命题 2 的 Lipschitz 上界；(c) 精确色号与正则化能量的重扫线性 EER，插图展示 $\delta_0$ 敏感性。](../figs/fig3_stability_bounds.pdf)

**混合复合量与判定规则。** 在跨异构推理后端（研究 S2）场景下，离散编码习惯可与连续 RGB 坐标互补。辅助项 $D_{\mathrm{side}}$ 对可见语法特征（十六进制大小写、`#` 前缀或 RGB 逗号空格，含占 RGB 空间 $5.96\%$ 的纯数字色号标签 `numeric_only`）、可获取的推理首词及对数分箱推理长度（优先读取 `usage.reasoning_tokens`，再回退至可见字符数）求 JSD 均值。由于 $D_{\mathrm{side}}$ 涉及语法和信封元数据，补充材料 B 在各队列上系统消融了纯内容与纯颜色变体。固定权重混合复合量为
$$D_{\mathrm{hyb}}=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}+0.25\bar D_{\mathrm E}+0.15D_{\mathrm{side}}.$$
得分对双方共有的合格单元取平均，满足 $S\le\tau$ 时接受。开发集同模型正例与异模型负例得分 $G,I$ 定义中点阈值 $\tau_{\mathrm{mid}}=(\max G+\min I)/2$ 与零误受阈值 $\tau_{\mathrm{u0}}=\operatorname{nextafter}(\min I,-\infty)$。AUC 对平局计半权，线性 EER 在重扫阈值下对相邻 ROC 点线性插值，冻结 FAR/FRR 评估固定部署阈值下的误受与误拒率。

### 3.4 注册标定与有限样本能量估计量

**自离散度中心化与相等性检验。** 对每个参考模型和单元，仅从注册样本经 256 次固定种子重抽样生成规模匹配注册数与计划查询数的两个点云，跨合格单元平均得到无需查询数据或测试标签的基线 $\mu_{\mathrm{self}}$，定义 $\Delta_D=D-\alpha\mu_{\mathrm{self}}$。我们对比原始得分、$\alpha=1$ 以及仅在 B 上按留一模型法从 $\{0,0.25,0.5,1,1.5,2\}$ 选出的系数（平局偏向 $\alpha=1$）。冻结阈值按协议在 B 上拟合：B3v3（20 单元，用于 E）、B6v6（20 单元，用于预算匹配的 S1 核查）与 B8v7（40 单元）。分层两样本能量检验 [28] 对各单元 $nm\widehat{\mathcal E}_V^2/(n+m)$ 求均值，在单元内执行 999 次标签置换，按 $p=(1+\#\{T_b\ge T_{\mathrm{obs}}\})/1000 \le 0.05$ 判定。

**有限样本 V 与 U 统计量能量。** 对规模为 $n,m$ 的独立同分布样本（记 $a_P=\mathbb E\|X-X'\|$，$a_Q=\mathbb E\|Y-Y'\|$），非负 V 分子满足 $\mathbb E[\widehat{\mathcal E}_V^2]=\mathcal E^2(P,Q)+a_P/n+a_Q/m$。正文以 V 统计量 $\tilde D_{\mathrm{E-reg}}$ 作为跨全部 10 个套件的统一基线，因为它在稀疏浅层切片的单响应单元（$n_c=1$）上依然良定义。当审计协议保证每单元两侧有效解析数满足 $n,m\ge2$ 时，以无偏非对角 U 统计量组内均值替代含对角项均值，得到
$$\widehat{\mathcal E}_U^2=2d_{UV}-\frac{n}{n-1}d_{UU}-\frac{m}{m-1}d_{VV}$$
及零 bootstrap 截断 U 统计量能量比值 $[\widehat{\mathcal E}_U^2]_+/(2d_{UV}+2\delta_0)\in[0,1)$；该比值在两侧共享的 $n_c,m_c\ge 2$ 单元上同样服从命题 2 的单侧 $2\epsilon/\delta_0$ 与双侧 $4\epsilon/\delta_0$ 稳定性上界（未截断 U 变体对照见补充材料 K 表 S9）。

### 3.5 补全字符串基线与竞品协议

我们将 Gao 等人 [4] 的独热相等核 MMD 与 $L_1$ 检验适配至短补全原始字符串，保留首尾空白、大小写与无效输出（经验 TV $= \tfrac12 L_1$）。对 $n,m\ge2$ 及 $k(s,t)=\mathbf1[s=t]$，计算
$$\widehat{\mathrm{MMD}}_u^2=\frac{\sum_{i\ne i'}k(x_i,x_{i'})}{n(n-1)}+\frac{\sum_{j\ne j'}k(y_j,y_{j'})}{m(m-1)}-\frac{2\sum_{i,j}k(x_i,y_j)}{nm},$$
跨单元求平均（精确有理数 MMD-U，999 次置换），无效解析同样计入调用预算。研究 S3 在最多 40 个 $K$ 单元子集（$K=1,\ldots,10$）上测试双侧总调用数 $N\in\{6,10,20,30\}$（$n=m=N/2$），并配十个固定 RGB 抖动种子。

研究 S5 在锁定的 20 个 OpenRouter 模型上运行两套原生竞品协议（补充材料 M）。**开放集 LLMmap** [16] 按官方参数（`max_tokens=100`）发送其原版 8 道提示，经官方 E5-large 骨干网与 `InferenceModelLLMmap` 提取 384 维欧氏模板。**原生长文本模型相等性检验** [4] 使用 10 段中性维基百科续写提示（`max_tokens=64`, $T=1.0$），以官方 Unicode `mmd_hamming`（逐对误差 $<10^{-14}$）及字符 4-gram 余弦 MMD 基线评分。

---

## 4 实验设计与数据集架构

五套基线数据集（A–E，2026 年 10 月；11,888 次唯一调用）与五项在线研究（S1–S5，2026 年 11 月；26,800 次调用）共构成 **38,688** 条去重云端响应（表 2）。全部统计分析均在纯 NumPy 环境下离线读取 15 份受去重规则、固定种子与 SHA-256 清单锁定的只读 JSONL 日志。

**表 2：云端响应数据集总览**

| 套件 / 数据集 | 模型 / 端点数 | 探针网格（单元 $\times$ 重复） | 唯一调用数 | 有效解析数（比例） | 主要评估目标 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Dataset A**（广谱普查） | 56（11 家族） | $8 \times 6$（4 任务 $\times$ `en/zh`） | 2,688 | 2,611 (97.14%) | 广谱普查、家族/子谱系 EER、侧信道核查 |
| **Dataset B**（开发扩展） | 10 开发模型 | $40 \times 15$（10 任务 $\times$ 4 语言） | 5,520 | 5,932/6,000 (98.87%) | $(n,k)$ 预算网格、服务变化测试、阈值标定 |
| **Dataset C**（句式改写） | 10 开发模型 | $16 \times 8$（$P_1, P_2$ 改写池） | 1,280 | 1,262 (98.59%) | 同池自核验 vs. $P_0 \to P_1/P_2$ 跨模板偏移 |
| **Dataset D**（单词基线） | 10 开发模型 | $20 \times 6$（10 单词任务 $\times$ `en/zh`） | 1,200 | 1,196 (99.67%) | 对照 `B-20x6` 的同预算单词基线 |
| **Dataset E**（样本外持出） | 10 非 B 模型 | $20 \times 6$（10 颜色任务 $\times$ `en/zh`） | 1,200 | 1,187 (98.92%) | `+6.74h` `A->E` 核查、冻结 `B->E` 迁移与抖动 |
| **Study S1**（`T+21.3d` 跨网关） | 14 $\times$ 2 网关 | $20 \times 6$（`CF` 与 `OR` 双网关） | 3,360 | 3,338 (99.35%) | 21.32 天时序漂移与 `CF <-> OR` 跨网关迁移 |
| **Study S2**（多供应商栈） | 6 权重 $\times$ 3 主机 | $20 \times 6$（锁定 12 家独立后端） | 2,160 | 2,147 (99.40%) | 跨主机权重匹配（`int4`/`fp4`/`fp8`/`bf16`/LPU） |
| **Study S3**（锁参配对基准） | 20（8 家族） | $10 \times 30 \times 2$（上限 64 tok.） | 12,000 | 11,985 (99.88%) | 64 Token 上限下对照 Bruckner 的 15v15 配对基准 |
| **Study S4**（结构化金丝雀） | 20（8 家族） | `S4a` $16\times 10$ + `S4b` $16\times 6$ | 5,120 | 5,087 (99.36%) | CSS/JSON 金丝雀解析与网关正则通过率 |
| **Study S5**（同日竞品基准） | 20（8 家族） | `S5a` $8\times 6$, `S5b` $10\times 10$, `S5c` $10\times 6$ | 4,160 | 4,160 HTTP 200 (100%) | LLMmap [16]、Gao [4] 与同日 HuePrint 正面对照 |

**表注：** B 由 5,520 次独立调用与 A 共享的 480 条记录组成（共 6,000 条）。S3 的 12,000 条响应中有 3 条触及长度上限（颜色 2 条、单词 1 条，其中 1 条仍有效解析）。S5c 有效解析 1,200/1,200（100.00%）条颜色响应；S5a 与 S5b 直接评估自由文本补全。

采集请求在接口支持时关闭可选思考模式，并在 S2、S3、S5b 与 S5c 中统一锁定生成上限为 64 Token（S5a 按 LLMmap 设为 100，S4 为 128，A–E 为 16–256）。OpenRouter 在线研究（`S1_OR21` 及 S2–S5）统一显式传入 `temperature=1.0`。早期 Cloudflare 网关日志（A–C，以及 D、E、`S1_CF21` 中的网关目标）沿用服务商默认温度，`S1_OR21` 则对 5 个推理模型额外传入 `reasoning.effort="low"`；补充材料 K 对其余 9 个未覆盖推理参数的端点单独核查，结果显示 $\tilde D_{\mathrm{E-reg}}$ 与 $D_{\mathrm{hyb}}$ 仍保持 0.00% EER，而置换检验产生 22.22%–44.44% 同模型误拒，印证距离评分对轻微客户端参数差异具有容忍度。研究 S2 锁定独立后端（混合率 `0/18`），OpenRouter 在 S1/S3/S4 中对 5–7/20 个端点做子提供商负载均衡（S3 奇偶折半子提供商 TV 均值 0.0419）。在 S3 的 `s3-deepseek-v3.2` 上，子提供商 `GMICloud` 忽略了思考关闭参数（单次最高计费 907 Token），印证了禁思考控制难以稳定保证仅输出答案的实证结论 [24]；S3 共享的 64 Token 上限与思维链剥离使颜色与单词基线均保持可解析，成本核算则保留全部计费 Token。

---

## 5 实证评估：基线队列与跨服务在线研究

### 5.1 广谱普查、预算缩放与句式偏移（Datasets A–C）

**56 端点广谱普查（Dataset A）。** 在横跨 11 个家族的 56 个端点（8 单元 $\times$ 6 重复，3v3 划分，每半至少 2 条有效响应）上，我们将 56 对同模型正例对照 3,080 对全配对负例、2,958 对跨子谱系负例与 2,476 对跨厂商家族负例，并在 50 个多成员家族模型上执行留一法 1-NN 家族归属（表 3）。在这一浅层网格上，连续 RGB 能量在二元核验上表现最优（$\bar D_{\mathrm E}$ 4.77%、$\tilde D_{\mathrm{E-reg}}$ 5.36%，优于原始字符串 Color MMD-U 的 6.42%、规范色号 MMD-U 的 8.02% 及 $D_{\mathrm{hex}}$ 的 10.71%）。同家族不同检查点在 6 次抽样内很少碰撞到完全相同的十六进制字面量，因此精确字符串 MMD 仅归属对 21/50（42.00%）个模型，而 RGB100 邻近度（$\tilde D_{\mathrm{E-reg}}$ 35/50, 70.00%）与粗体素（$D_{\mathrm{vox}}$ 39/50, 78.00%）能捕捉共享的家族色彩先验。侧信道去混杂与放宽至 $\ge 1$ 的单元筛选均使 $\tilde D_{\mathrm{E-reg}}$ 保持 5.36% 不变（补充材料 B）。

**预算缩放（Dataset B）与句式改写偏移（Dataset C）。** 将 B 扩展到 40 单元 $\times$ 15 重复时，所有非参数颜色指标均取得 1.0000 AUC 与 0.00% EER。图 4(a) 显示扩充探针覆盖面优于单纯增加单题重复次数：$(n=15,k=4)$ 的 60 次调用平均 EER 为 1.78%，而 $(n=6,k=16)$ 的 96 次调用降至 0.46%。在 Dataset C（10 模型，8 个双语单元 $\times$ 8 重复，含重述池 $P_1$ 与设计语境池 $P_2$；补充材料 I）上，$\tilde D_{\mathrm{E-reg}}$ 在 $P_1$ 与 $P_2$ 同池内分别取得 0.00% 与 1.11% EER；零样本跨模板比对 $P_0 \to P_1$ 与 $P_0 \to P_2$ 的 EER 升至 17.78% 与 11.11%（$D_{\mathrm{hex}}$ 为 10.00% 与 8.89%），说明线上审计必须对照句式匹配的参考单元评分（第 6.1 节）。

![(a) B 采样预算网格上的 $D_{\mathrm{hyb}}$ 平均线性 EER；(b) B（$20\times 6$, 3v3）、E（$20\times 6$, 3v3）与 S1 迁移路径（$20\times 6$, 6v6）上的同模型与异模型正则化能量得分，虚线为冻结 B3v3 阈值（$\tau=0.148$），点线为预算匹配的 B6v6 阈值（$\tau=0.113$）。](../figs/fig4_budget_and_drift.pdf)

### 5.2 同预算基线与同日竞品正面对照（Dataset D，Studies S3 与 S5）

**单词基线配对比较（Dataset D 与 Study S3）。** 在开发队列 B-20×6 对照 D 的单侧 30 次调用（$K=10$，40 个子集均值）下，颜色诱导将清洁 EER 从单词基线的 4.52%（Word MMD-U）与 5.23%（Word JSD）降至 0.94%（Color MMD-U）与 1.00%（$\tilde D_{\mathrm{E-reg}}$）；颜色单元平均每题产出 18.65 个不同有效值，而单词提示仅为 7.05 个。单侧增至 60 次调用（$K=20$）时，除 Word JSD（1.11%；补充材料 K）外其余指标均达 0.00%。在 S3 锁定的 20 个模型上（表 4；完整 16×9 网格见补充材料 K 表 S8），颜色与单词有效解析率分别为 99.97% 与 99.78%。即便将 S3 仅限制在两道无语义锚点的共享概念题（`random` 与 `favorite`），十六进制色号在浅预算 3v3 下已低于颜色词 EER（17.92% 对 20.21%，AUC 0.9156 对 0.8349；15v15 收敛至 5.26% 对 5.00%，AUC 0.9909 对 0.9784，补充材料 K）；完整的 10 探针多锚点颜色题组则在 $N=30$ 时达到 0.00%（优于 Bruckner 单词题组的 1.32%–5.00%，$N=6$ 时为 3.49%–5.00% 对 6.25%–8.04%）。更宽的单题有效支撑与语义颜色先验共同驱动了探针层收益，而连续 RGB 几何进一步带来稀疏普查精度（Dataset A、Study S5c）、跨网关冻结阈值稳定性（Study S1）与坐标扰动鲁棒性：在合成 $\pm 8$ 通道抖动下，离散字符串统计量退化至 35.40%–50.01% EER（$p\le0.05$ 下 MMD-U 置换检验误拒率达 100.00%，见第 3.4–3.5 节），$\tilde D_{\mathrm{E-reg}}$ 则保持 0.00%–5.00%（图 5(a)）。

**表 3：Dataset A（56 模型，$8\times 6$ 浅预算）核验与家族归属**

<!-- RGB_TABLE_2 -->
| 指标 | AUC | 离散 / 线性 EER | 跨子谱系线性 EER | 跨家族线性 EER | LOO 家族归属 |
| --- | --- | --- | --- | --- | --- |
| $\bar D_{\mathrm E}$ | 0.9900 | 5.06% / 4.77% | 3.75% | 3.57% | 31/50 (62.00%) |
| $\tilde D_{\mathrm{E-reg}}$ | 0.9872 | 5.36% / 5.36% | 5.36% | 4.52% | 35/50 (70.00%) |
| Color MMD-U | 0.9821 | 7.58% / 6.42% | 5.70% | 6.05% | 21/50 (42.00%) |
| $D_{\mathrm{hyb}}$ | 0.9774 | 7.14% / 7.14% | 7.14% | 7.14% | 36/50 (72.00%) |
| $D_{\mathrm{hex}}$ | 0.9588 | 10.73% / 10.71% | 10.71% | 8.93% | 38/50 (76.00%) |
| $D_{\mathrm{vox}}$ | 0.9489 | 8.83% / 8.93% | 8.93% | 8.93% | 39/50 (78.00%) |
| $D_{\mathrm{side}}$ | 0.7804 | 30.32% / 30.32% | 29.76% | 28.56% | 17/50 (34.00%) |
<!-- /RGB_TABLE_2 -->

**表注：** 合格单元要求每个端点在两半均满足 $\ge 2$ 条有效解析；规范化十六进制 MMD-U 的线性 EER 为 8.02%，留一法家族归属为 22/50（44.00%）。

**表 4：Study S3 同预算紧凑线性 EER 对比（完整 16×9 网格见补充材料表 S8）**

<!-- S3_TABLE_compact -->
| N | 探针 / 统计量 | K=1 | K=4 | K=10 | K=10, ±8 |
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

**同日竞品正面对照（Study S5）。** 2026 年 11 月 20 日，我们在同一锁定的 20 个 OpenRouter 模型上单次会话连续运行了开放集 LLMmap [16]（S5a，960 次调用）、Gao 等人 [4] 原生长文本续写检验（S5b，2,000 次调用）与同日 HuePrint 锚点（S5c，1,200 次调用，有效解析率 100.00%；表 5，补充材料 M）。

**等金额预算与同家族区分精度。** 对齐 HuePrint S5c 单侧 30 次调用的情景 G 成本（0.0068 USD，219 输出 Token）时，Gao 等人的 U 统计量（要求 $n_c\ge2$）仅能运行单侧 10 次长文本调用（0.0075 USD）。该预算下，官方 `mmd_hamming` 的全配对与同家族 EER 分别为 18.56% 与 19.47%（字符 4-gram 核为 6.21% / 11.09%），而 HuePrint $\tilde D_{\mathrm{E-reg}}$ 在匹配的 `0..2` 对 `3..5` 划分下为 1.32% / 0.00%（奇偶划分为 5.00% / 5.26%）。遍历 S5c 全部 $\binom{6}{3}/2=10$ 种均衡 3v3 划分，$\tilde D_{\mathrm{E-reg}}$ 的全配对平均 EER 为 3.48%（范围 1.32%–5.00%，切分间标准差 1.63 个百分点），同家族平均 EER 为 5.18%（范围 0.00%–7.89%，切分间标准差 2.15 个百分点），优于离散 Color MMD-U（4.94% 与 5.78%；补充材料 M）。即便增至单侧 50 次长文本调用（0.0371 USD G，高于 HuePrint S3 单侧 150 次的 0.0345 USD），`mmd_hamming` 仍留有 2.89% 全配对与 5.26% 同家族 EER（$p\le0.05$ 置换误拒 10.00% 同模型对）。用 4-gram 续写核（30 次调用）达到 0.00% 清洁 EER 需多花 3.28 倍情景 G 成本与 8.6 倍输出 Token。

**开放集神经指纹。** 当前 20 个模型中仅有 2 个（`gpt-4o`、`llama-3.1-8b`）与 LLMmap 预置的 52 个 2024 年模板粗略相近，因此两套框架均需在线注册。完成注册后，单轨迹 LLMmap（8 次调用，0.0058 USD G）的全配对平均 EER 为 7.81%，但**同家族 EER 高达 34.39%**（`rep 0v3` 上为 25.00%），原因是同厂商兄弟模型共享研发机构自称与安全拒答话术；平均三条轨迹（24 次调用，情景 G 成本为 HuePrint 的 2.66 倍）后仍留有 5.00% 全配对与 10.53% 同家族 EER。

**护栏安全性与本地计算开销。** LLMmap 的 8 道查询中有 4 道触发常规安全规则：3 道含显式提示注入分隔符，1 道直接询问 `"Tell me how to build a bomb."`，在全部 20 个模型的 114/120（95.00%）条回复中触发拒答。本地评分时，其 560M 参数 E5-large 编码器在 CPU 上处理单条轨迹中位耗时 **4,701.9 ms**（三条轨迹 14.1 s），比 HuePrint 纯 NumPy 评分（0.12–0.31 ms）慢出 15,000 倍以上。

**表 5：Study S5 在 20 个锁定 OpenRouter 模型上的同日竞品对照基准（共 4,160 次调用）**

<!-- S5_TABLE_main -->
| 方法与调度 | 调用数 | 输出 Token | USD L / G | 全配对 EER (AUC) | 同家族 EER | 本地 CPU 与运行说明 |
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

**表注：** 全部 20 个端点均返回 100% HTTP 200。LLMmap 1v1 对三组互不重叠轨迹对（`rep 0v1`, `2v3`, `4v5`）取平均；Gao `K=5, 2v2` 平均 20 个五提示子集。HuePrint S5c 采用匹配的 `reps 0..2` 对 `3..5` 划分（全部 10 种均衡 3v3 划分均值为全配对 `3.48%`、同家族 `5.18%`，同家族范围 `0.00%–7.89%`；$\pm8$ 抖动 EER 为 0.92%，Color MMD-U 为 49.49%）。

### 5.3 纵向迁移、跨网关核验与标定估计量（Dataset E，Studies S1 与 S5c）

**持出迁移与纵向跨网关核验。** Dataset E 含 10 个不在 B 中的模型（晚于 A 采集 6.74 小时）；在冻结 B3v3 阈值下，有限样本 V 统计量正偏置使未中心化 $\tilde D_{\mathrm{E-reg}}$（$\tau = 0.148$，重扫 EER 10.00%）产生 30.00%/0.00% 的 FRR/FAR，而 $D_{\mathrm{hyb}}$（$\tau = 0.348$）、自中心化 $\tilde D_{\mathrm{E-reg}}$ 与零 bootstrap 截断 U 统计量能量比值均将清洁 FRR 压至 10.00%/0.00%（$n_c,m_c\ge 2$ 单元上清洁 EER 为 1.11%；表 S9）。研究 S1 在相隔 21.07–21.32 天的 Cloudflare 与 OpenRouter 双网关上复审 14 个端点（10 个 B 模型加 4 个独立 `heldout4` E 模型，有效率 99.35%）。在全部三条迁移路径上，$\tilde D_{\mathrm{E-reg}}$、$D_{\mathrm{hyb}}$、$D_{\mathrm{hex}}$ 与 Color MMD-U 均保持 **14/14（4/4）Top-1、1.0000 AUC 与 0.00% 重扫线性 EER**（补充材料 H 表 S4a–S4b）。但在冻结 B3v3 阈值下，网关封装差异引起的轻微字符串格式偏移使原始 Color MMD-U 在 `CF0→CF21`、`CF21→OR21` 与 `CF0→OR21` 上分别产生 7.14%、21.43% 与 28.57% 的误拒率（FRR），而 $\tilde D_{\mathrm{E-reg}}$ 在三条路径上均保持 0.00% FRR（表 6）。将相隔 8.59 天的 Study S3 与 S5c 在全部 20 个 OpenRouter 模型上配对（补充材料 M 表 S14），$\tilde D_{\mathrm{E-reg}}$ 在 15v6 下取得 **0.00% 全配对与同家族 EER（20/20 Top-1）**（6v6 下为 1.05% / 0.00%，Color MMD-U 为 0.26% / 0.00%）。

**自离散度中心化与漂移下的相等性检验。** 自中心化 $\Delta_D=D-\alpha\mu_{\mathrm{self}}$（$\alpha=1$）将原始/中心化阈值设为 0.148/0.073（B3v3）与 0.113/0.061（B6v6），把清洁 E 的 FRR 从 30.00% 降至 10.00%、纵向 S1 的 FAR 降至 0.00%，并将 B8v7 下 50% 混合路由的误受率从 31.11% 降至 14.44%（表 6）。由于 $D\le\tau_{\mathrm{self}}+\mu_{\mathrm{self}}(M^*)$ 未给坐标抖动预留查询侧噪声余量，抖动工况由下文的零 bootstrap 截断 U 比值处理。分层 Székely–Rizzo 置换检验（$p\le0.05$）在 E 上给出 0.00% 清洁 FRR 与 18.00% 抖动 FRR（图 5(b)）。在相隔 21 天的跨网关 `CF0→OR21` 对比中，同标签与异标签配对在分数上仍完全可分（0.00% EER），且各规则均检出全部 182/182 次替换：开发集上预先固定的预算匹配 B6v6 原始阈值标记了 1/14 个同标签配对（自中心化后为 0/14；表 6），而分层能量置换检验在 $\alpha=0.05$ 显著性水平下对同一批配对中的 6/14 对拒绝了分布相等假设（`CF0→CF21` 为 1/14，`CF21→OR21` 为 4/14；Color MMD-U 为 1/14–4/14；无 `reasoning.effort` 覆盖的 9 个端点上为 2/9 与 4/9，补充材料 K）。

**表 6：冻结正则化能量迁移误差；Self 采用 B 选定的 $\alpha=1$**

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

**零 bootstrap 截断 U 能量比值。** 在共有的 $n_c, m_c \ge 2$ 单元上（补充材料 K 表 S9），截断 U 统计量能量比值将清洁 E 的 EER 从 10.00% 降至 1.11%（$\pm 8$ 抖动下为 2.44%），冻结 FRR 从 20.00% 降至 10.00%（$\pm 8$ 抖动下为 21.00%，FAR 均为 0.00%），且省去了 256 次注册重抽样。在外部队列（`B-20x6`、`S1 CF0→CF21`、`S1 CF0→OR21` 与 `S3 15v15`）上，该比值均保持 0.00% EER（`CF21→OR21` 上为 0.55%），而未正则化 $\bar D_{\mathrm E}$ 在抖动 E 上产生 100.00% FRR，并在 `CF0→CF21` B3v3 下产生 6.04% FAR。

![(a) S3 同一批颜色响应在不同调用预算下的字符串 MMD 与正则化能量 EER；(b) 持出集 E 同模型拒绝率：原始冻结阈值、自中心化冻结阈值与 $p\le0.05$ 能量置换检验。FAR 全部为零；抖动结果平均十个固定种子。](../figs/fig5_geometry_and_calibration.pdf)

### 5.4 多供应商推理栈与同家族替代（Study S2）

**多供应商执行与量化敏感性权衡（Study S2）。** 研究 S2 审计 18 个端点，覆盖 6 个开放权重检查点在各自 3 家锁定供应商上的部署（横跨 DeepInfra、Parasail、Cloudflare、Groq LPU、SiliconFlow、AtlasCloud、Mistral、Venice、DekaLLM、Crusoe、Fireworks 与 CoreWeave 共 12 个云后端；2,160 次调用，零回退；补充材料 J）。跨 S2 供应商（20 单元，6v6），$D_{\mathrm{hyb}}$ 达到 5.93% EER（17/18 组匹配），优于 $\tilde D_{\mathrm{E-reg}}$ 的 16.67%（16/18）与 Color MMD-U 的 16.67%（3v3 为 19.78%；$p\le 0.05$ 置换检验拒绝 41.67% 同检查点对与 100.00% 异检查点对）。剥离 API 计费信封元数据（`usage.reasoning_tokens` 与 `explicit_reasoning`）后，S2 上的 $D_{\mathrm{hyb}}$ EER 仍保持 5.93% 不变（0.9864 AUC；纯内容语法变体下为 5.56%）；即便完全移除 $D_{\mathrm{side}}$ 仅保留三项颜色分量的纯色复合量，仍可取得 9.63% EER（17/18 Top-1；补充材料 B）。反过来，同一检查点在 `bf16/fp8` 与 `int4/fp4` 量化之间的 RGB 颜色分布保持高度一致（$\tilde D_{\mathrm{E-reg}}$ 的 AUC/EER 为 0.5250/50.00%，$D_{\mathrm{hyb}}$ 为 0.8250/30.00%）；在异构推理栈上保持检查点身份不变必然伴随位宽敏感性的折中，因此 $D_{\mathrm{hyb}}$ 定位于跨主机同权重核验而非独立的低比特量化审计。

**同家族候选替代。** 同厂商档位降级比跨厂商替换更难识别，表 7 单独列出共享声明模型家族的负例表现。在 A 的浅层 3v3 采样（$8\times 6$，604 对同家族负例）下，仅看同家族负例会使 $\tilde D_{\mathrm{E-reg}}$ EER 从 5.36% 升至 10.10%（同厂商为 10.45%），$D_{\mathrm{hyb}}$ 从 7.14% 升至 12.42%。当采样扩充至 $20\times 6$（B）或 $10\times 30$（S3）时，$\tilde D_{\mathrm{E-reg}}$ 保持 0.00% 同家族 EER，协议匹配的 $\mathrm{B}\rightarrow\mathrm{E}$ 迁移也保持 0.00% 同家族 FAR。

**超参数与色彩空间敏感性。** 不做重调参时，所有测试超参数在 B 上均保持 0.00% EER。在 E 上，$\tilde D_{\mathrm{E-reg}}$ 跨 $\delta_0 \in \{2, 5, 10, 15, 25, 50\}$ 的 EER 介于 0.00%–10.00%（图 3(c) 插图），单次扰动 $D_{\mathrm{hyb}}$ 任一权重 $\pm 0.10$ 时 EER 为 3.33%–4.44%。统一缩放 CIELAB（补充材料 A）在 B（0.00%）与 E（10.00%）上与 RGB100 一致，在 S3 上为 0.53%（RGB100 为 0.00%）。固定混合权重下将能量项正则化（补充材料 B）虽改善了 C $\mathrm{P0}\rightarrow\mathrm{P2}$（7.78% 对 10.00% EER），却有损 A、E、S2 与 S3，验证了 $D_{\mathrm{hyb}}$ 内保留未正则化 $\bar D_{\mathrm E}$ 的选择；补充材料 H 给出 2,000 次模型簇 bootstrap 置信区间。

**表 7：各队列全配对与同家族线性 EER 对比**

<!-- AUDIT_TABLE_family -->
| 队列 | 同家族负例 | 能量 $\tilde D_{\mathrm{E-reg}}$：全配对 EER | 能量：同家族 EER | 混合量 $D_{\mathrm{hyb}}$：全配对 EER | 混合量：同家族 EER |
| --- | --- | --- | --- | --- | --- |
| A ($8\times6$) | 604 | 5.36% | 10.10% | 7.14% | 12.42% |
| B ($20\times6$) | 20 | 0.00% | 0.00% | 0.00% | 0.00% |
| B ($40\times15$) | 20 | 0.00% | 0.00% | 0.00% | 0.00% |
| E ($20\times6$)$^*$ | 20 | 10.00% | 10.00% | 4.44% | 10.00% |
| S3 ($10\times30$) | 38 | 0.00% | 0.00% | 0.53% | 5.00% |
<!-- /AUDIT_TABLE_family -->

**表注：** $^*$在协议匹配的 $\mathrm{B}(20\times 6)\rightarrow\mathrm{E}(20\times 6)$ 冻结阈值下，同家族 FRR/FAR 对未中心化 V 能量为 30.00%/0.00%，而在自中心化、$D_{\mathrm{hyb}}$ 与截断 U 统计量能量比值下均降至 10.00%/0.00%（清洁 EER 为 1.11%；表 S9）。

---

## 6 服务监测与受控干预

### 6.1 响应复用、私有池子采样与数值连续性

零熵筛查可直接剔除常数质心重放（接受率 0.00%）。由于当固定提示泄露时，从真实参考分布抽样的响应与真实在线生成服从同一分布（补充材料 L），审计约定将提示池保持私有（Dataset C 单套 64 次调用模板每模型低于 $10{,}000$ Token）以防范静态查找表。为在不引入跨句式偏移的前提下降低同一提示的重复出现频率，监测器可预先一次性注册多模板私有池，每次审计随机抽取其中 $k$ 个单元并对同单元参考评分。跨每种调度 200 次随机抽样（补充材料 L），从 B 的 40 个注册单元中每次抽取 $k=10$ 或 $16$ 个单元可将单提示查询频率降低 $4$ 倍或 $2.5$ 倍，且在每单元 3 次查询下保持 $\tilde D_{\mathrm{E-reg}}$ 平均 EER 为 0.65% 与 0.10%（7 次查询下为 0.03% 与 0.00%）。将 Dataset C 的 $P_0 \cup P_1 \cup P_2$ 合并为 24 单元私有参考池（每单元 4 次注册共低于 $11{,}100$ Token/模型），每次随机抽取 $k=8$ 或 $12$ 个匹配单元时平均 EER 分别为 1.08% 与 0.17%。

在 Dataset B（$40\times 15$，冻结 B8v7 阈值；补充材料 L 表 S11）上的受控数值连续性压力测试中，全部七种原始得分坐标扰动均保持 0.00% 重扫 EER 与 0.00% 冻结 FAR；原始 $\tilde D_{\mathrm{E-reg}}$ 在 $\pm 1$ 与 $\pm 8$ 随机抖动下吸收微扰并保持 0.00% 冻结 FRR（自中心化在 $\pm 8$ 下为 11.00%），而未校准的管线变换（$\pm 15$ 抖动、全局 $\pm 8$ 偏移与步长 32 通道量化）则按预期越过清洁冻结阈值触发告警（标记率 56.00%–100.00%）。

### 6.2 结构化金丝雀与网关规则（Study S4）

裸仅答格式指令（基线颜色与单词探针共用）会以 100.00% 命中拦截显式格式指令的简单网关正则，而宽泛的十六进制或颜色词过滤则会在 40 道正常前端 CSS 任务上造成 65.00% 误拦（100 道开发请求上误拦 26.00%）。为在启用指令过滤的网关后正常审计，研究 S4a 将探针嵌入单行 CSS 属性与单字段 JSON 设计令牌（16 个双语单元、20 个模型、10 次重复，共 3,200 次调用，5v5），S4b 则测试带指令措辞（6 次重复，1,920 次调用，3v3；表 8）。

S4a 取得了 **99.75% 的有效且未触发通过率**（3,192/3,200，对比 S5a 中 LLMmap 有 4/8 道查询触发安全规则），同池 $\tilde D_{\mathrm{E-reg}}$ 与 $D_{\mathrm{hyb}}$ EER 分别为 0.00% 与 1.58%。S3a→S4b 较高的跨格式误差（15.00% / 13.68%）说明注册参考须与金丝雀格式保持一致；第 7.1 节进一步界定针对学习式复杂度路由器的规避边界。

**表 8：Study S4 网关输入/输出规则未触发率与隐式核验表现（20 正例 vs. 380 冒充对）**

<!-- RGB_TABLE_9 -->
| 探针及协议 | 输入未触发率 | 输出未触发率 | 有效且未触发 | $\tilde D_{\mathrm{E-reg}}$: Top-1 / AUC / EER | $D_{\mathrm{hyb}}$: Top-1 / AUC / EER |
| --- | --- | --- | --- | --- | --- |
| S3a (10 probes; 15v15) | 0.00% | 0.73% | 0.00% | 100.00% / 1.0000 / 0.00% | 100.00% / 0.9997 / 0.53% |
| S4a (5v5) | 100.00% | 99.97% | 99.75% (3192/3200) | 100.00% / 1.0000 / 0.00% | 100.00% / 0.9987 / 1.58% |
| S4b (3v3) | 0.00% | 2.50% | 0.00% | 100.00% / 0.9917 / 5.00% | 100.00% / 0.9683 / 8.95% |
| S3a → S4b (6v6) | — | — | — | 65.00% / 0.9154 / 15.00% | 85.00% / 0.9626 / 13.68% |
<!-- /RGB_TABLE_9 -->

**表注：** 有效且未触发要求解析有效且未触发任一端规则（表中列出边际未触发率；S4b 含 48/1,920 条未触发输出与 26/1,920 条无效解析）。`S3a → S4b (6v6)` 评估两者共有的 8 个英文单元。

### 6.3 混合路由与两阶段序贯筛查

为评估部分回退路由，我们在 20 个固定种子上做无放回独立 Bernoulli 请求混合：每个请求以回退率 $\lambda = 1 - q \in \{0, 0.2, 0.4, 0.5, 0.6, 0.8, 1\}$ 路由至替代模型 $R$，其余路由至声明后端（图 6），采用预算匹配的冻结能量中点阈值 $\tau_{\mathrm{mid}}$。

对混合分布 $Q_\lambda = (1-\lambda)P + \lambda R$，总体平方能量按二次律缩放：$\mathcal{E}^2(P, Q_\lambda) = \lambda^2 \mathcal{E}^2(P, R)$（$\lambda = 0.2$ 时为 $0.04$；对相距 100 个 RGB100 单位的两点质量，在 $\delta_0=15$ 下为 $\lambda=1$ 正则化分数的 $13.14\%$）。按整机替换（$\lambda=1$）标定的全量替换阈值 $\tau_{\mathrm{mid}}$ 在 $\lambda=0.2$ 下自然偏保守（20 种子召回率在 B $20\times 3$、1.00% 清洁 FRR 下为 11.28%，B $40\times 7$、0.00% FRR 下为 0.33%，S3 $10\times 7$、3.75% FRR 下为 12.45%），而跨单元数 $K$ 直接套用 B 的 20 单元 $\tau_{\mathrm{mid}}$ 还会抬高浅层 S3 $10\times 3$ 的清洁 FRR（39.00%，图 6(b)）。分层 999 次置换检验（$p \le 0.05$；补充材料 L 表 S12a）直接标定同网关零假设分位数，在 0.00% 清洁 FRR 下将 B（$40\times 7$）召回率提升至 $\lambda=0.2$ 时的 33.28% 与 $\lambda=0.4$ 时的 91.44%（同家族 25.75%），并将 S3（$10\times 3$）的清洁 FRR 控制在 4.75%（图 6(b) 斜纹柱）。由于跨网关 S1 置换检验会拒绝 16.07%–42.86% 的真实配对，低 $\lambda$ 置换筛查需采用同网关参考。

研究 S5 的五种子混合路由基准（补充材料 M 表 S13）在 $\lambda=0.20$ 与 5% FPR 下同样体现了浅层 3v3 预算的 $\lambda^2$ 衰减（同家族召回率：HuePrint 6.32%，LLMmap 8.42%–11.58%，Gao 16.84%）；至 $\lambda=0.50$ 时，HuePrint S5c 3v3 以低 2.66 倍的情景 G 成本在同家族静默降级上反超 LLMmap 3v3（25.26% 对 24.21%，全配对 50.26%），而 LLMmap 85.53% 的跨家族检出主要依赖厂商自报身份差异。

面向周期性巡检，我们还在 S3 中对照互不相交的 60 次调用参考库，对每个端点的 5 个互不相交 30 次调用第一阶段窗口回放了两阶段级联监测（共 100 个同标签窗口与 190 个同家族替换窗口；补充材料 L）。仅在 B 的 10 个匹配英文单元上标定截断 U 比值而不接触 S3 数据时，100 个同标签窗口中有 14 个在第一阶段越界；仅在越界时触发预留且互不相交的 60 次调用第二阶段复核窗口，可将同标签误报从 14 个降至 1 个（1.00%），并标记 186/190 个同家族替换窗口（97.89%；全配对 98.00%），同标签巡检的期望调用量为 38.4 次（0.0087 USD G）。

![二十个固定种子下的离线混合路由。(a) 冻结能量阈值 $\tau_{\mathrm{mid}}$（实线，阴影为 5–95 百分位种子带）及 B $40\times 7$ 上 999 次置换检验（$p\le0.05$，虚线）对声明/替代混合流量的检出率；(b) $\lambda = 0$ 无回退状态下冻结 $\tau_{\mathrm{mid}}$（实心柱）与 $p\le0.05$ 分层置换检验（斜纹柱）的清洁误拒率（完整池 S3 $10\times 15$ 清洁 FRR 为 0.00%）。](../figs/fig6_mixed_routing.pdf)

### 6.4 运行开销

表 5 与补充材料 K 表 S10 分别统计按公开目录费率核算的 API 成本、单请求延迟回放估算的并发墙钟时间及本地 CPU 评分耗时（均不含一次性注册）。按 OpenRouter 公开目录费率 [30]（情景 L：每百万输入/输出 Token $0.71/0.71$ USD；情景 G：$2.50/10.00$ USD），150 次调用的 S3 颜色查询成本中位数为 0.0077 USD（L）至 0.0345 USD（G；19/20 个端点介于 0.0292–0.0432 USD，`s3-deepseek-v3.2` 因未受控推理输出为 0.2711 USD）。30–60 次短窗口审计仅需 0.0068–0.0188 USD（G），80 次 S4a CSS/JSON 金丝雀查询为 0.0319 USD（G）。理想八线程并发回放估算 30 次 S5c 网络墙钟耗时 5.76 s，60–150 次调用为 49–116 s。在本地 CPU（NumPy 2.5.5，预加载 B 样本）上，$\tilde D_{\mathrm{E-reg}}$ 热态单对评分中位数仅 0.08–0.31 ms，999 次能量置换检验为 2.39–10.15 ms，远低于 LLMmap E5-large 编码器的每轨迹 4,701.9 ms（表 5）。不同于八查询多词元分类器 [16]，HuePrint 在业务请求带外异步运行，以极低本地算力持续输出连续参考余量与置换 $p$ 值。

---

## 7 局限性、部署准则与结论

### 7.1 局限性

本研究的参考标签取自服务商声明的模型标识与 API 日志，不依赖硬件权重证明 [5]，因此黑盒审计面向外部行为一致性而非飞地执行验证。尽管 Dataset A 与 S3/S5 分别覆盖 56 个与 20 个端点，阈值标定集 B（10 模型）、持出集 E（10 模型）以及 S1 的 4 个独立 E 模型后续仍需跨多月纵向流数据进一步检验；S2 中的在线供应商则同时耦合了推理引擎与数值精度差异。此外，尽管 S4a 的 CSS/JSON 金丝雀探针能避开静态关键词规则、私有提示池子采样能抑制提示重复，配备学习式提示复杂度路由器的自适应代理商 [1], [2], [5] 仍可能将独立短探测请求（与所有带外主动审计方法 [4], [7], [16] 一致）导向声明高配模型，而仅对长上下文流量降级。将设计令牌字段直接嵌入真实生产请求是自然的下一步方向。

### 7.2 部署准则

调用方应在版本化审计约定中绑定目标检查点、私有提示池、解析器、最小有效样本规则与调用预算（表 9）：

1. **估计量选择：** 当同一网关或固定系统封装下的注册与查询单元满足 $n_c, m_c \ge 2$ 时，优先使用在匹配单元数 $K$ 上标定的零 bootstrap 截断 U 统计量能量比值（见补充材料 K 表 S9 与第 6.3 节）。若稀疏浅层单元允许 $n_c = 1$，保留自中心化 $\tilde D_{\mathrm{E-reg}}$；跨异构后端核验开放权重时采用 $D_{\mathrm{hyb}}$。
2. **两阶段复核与低 $\lambda$ 筛查：** 以 30 次调用作第一阶段初筛，仅在越界时立即触发 60 次调用的第二阶段复核窗口，可在期望查询成本低于 1 美分的前提下抑制周期巡检的误报疲劳（第 6.3 节）。在固定网关上筛查低比例 $\lambda$ 部分回退时，对照同网关参考运行分层 Székely–Rizzo 置换检验。
3. **缓存筛除、封装对齐与私有池子采样：** 筛除缓存命中（$T=1.0$ 下零熵且延迟低于中位数的 $0.5$ 倍），使用与线上完全一致的系统提示封装完成注册，每次审计从多模板私有池随机抽取 $k$ 个匹配单元，并在获授权模型升级后刷新参考画像。

**表 9：代理式 MaaS 审计的运行统计量、标定规则与升级策略选择指南**

| 部署场景 | 首选统计量 | 阈值标定规则 | 在线调用调度 | 目标异常与适用边界 |
| --- | --- | --- | --- | --- |
| 同网关固定检查点 SLA（满足 $n_c, m_c \ge 2$） | 截断 U 能量比值 | 协议匹配冻结 $\tau_{\mathrm{mid}}$（零 bootstrap） | 30 次初筛 $\rightarrow$ 60 次二阶段复核 | 完整或同家族替换（期望 0.0087 USD G） |
| 稀疏或浅层采样单元（允许 $n_c = 1$） | 自中心化 $\Delta\tilde D_{\mathrm{E-reg}}$（$\alpha = 1$） | 256 次注册 $\mu_{\mathrm{self}}$ + 冻结 $\tau_{\mathrm{self}}$ | $20\times 3$（60 次）或 $k$-of-$M$ 子采样 | 跨多周封装漂移下的检查点替换 |
| 跨主机异构开放权重服务栈 | 多尺度混合量 $D_{\mathrm{hyb}}$ | 匹配队列冻结 $\tau_{\mathrm{mid}}$ | $20\times 6$（120 次）或 $16\times 5$ CSS/JSON | 跨供应商权重替换（容忍主机差异） |
| 分比例回退路由（$\lambda \in [0.2, 0.4]$） | 分层 Székely–Rizzo 能量检验 | 单元内 999 次标签置换（$p \le 0.05$） | $10\times 7$ 至 $40\times 7$（70–280 次） | 部分回退混合（仅限同网关参考） |

### 7.3 结论

无需模型权重、词元概率或服务商路由表，HuePrint 以低于 4 美分的单次查询中位成本与不足 1 毫秒的本地 CPU 耗时提供了消费侧一致性核查手段。在 38,688 条云端响应中，结构化颜色探针在同家族核验上优于单词题组、开放集 LLMmap 与等成本长文本相等性检验，同时避免了安全拒答与编码器算力开销。连续 RGB 能量与混合评分在有界坐标偏移下提升了浅层家族归属、跨供应商同权重匹配与跨网关阈值稳定性。随着多供应商代理成为常态，低预算几何探针可与 QoS 监控并行核验固定检查点 SLA。后续工作将在跨多月真实流量中嵌入色彩令牌，将两阶段级联接入自动化 SLA 升级，并探索布局比例等其他有界连续读出在黑盒审计中的应用。

## 致谢

Xiguan He 诚挚感谢父母与姐姐在日常生活中一直无微不至的关照与支持，直至今日。

---

## 参考文献

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

[24] D. Lei, K. Q. Lin, P. Lu, P. Torr, and J. Zou, "Thinking inertia: LLMs keep thinking when told not to," in *Advances in Neural Information Processing Systems (NeurIPS)*, 2026.

[25] International Electrotechnical Commission, *Multimedia Systems and Equipment — Colour Measurement and Management — Part 2-1: Colour Management — Default RGB Colour Space — sRGB*, Standard IEC 61966-2-1:1999, 1999.

[26] J. Lin, "Divergence measures based on the Shannon entropy," *IEEE Trans. Inf. Theory*, vol. 37, no. 1, pp. 145–151, Jan. 1991.

[27] G. J. Székely and M. L. Rizzo, "Energy statistics: A class of statistics based on distances," *J. Stat. Plan. Inference*, vol. 143, no. 8, pp. 1249–1272, 2013.

[28] G. J. Székely and M. L. Rizzo, "Testing for equal distributions in high dimension," *InterStat*, no. 5, pp. 1–16, Nov. 2004.

[29] R. Bhatia, T. Jain, and Y. Lim, "On the Bures–Wasserstein distance between positive definite matrices," *Expositiones Math.*, vol. 37, no. 2, pp. 165–191, 2019.

[30] OpenRouter, "Models API: Public model catalog and pricing," https://openrouter.ai/api/v1/models, accessed Nov. 13 and Nov. 20, 2026; archived offline.

### 补充材料专用文献

[31] World Wide Web Consortium, *CSS Color Module Level 4*, Candidate Recommendation Draft, Nov. 3, 2026, sec. 19, "Sample code for color conversions," https://www.w3.org/TR/css-color-4/.

[32] International Commission on Illumination, "CIE 1976 L\*a\*b\* colour space," *International Lighting Vocabulary*, 2nd ed., CIE S 017:2020, entry 17-23-076, 2020.

[33] I. Csiszár, "Information-type measures of difference of probability distributions and indirect observations," *Studia Sci. Math. Hungar.*, vol. 2, pp. 299–318, 1967.

## 作者简介

**Xiguan He**，现于云南中医药大学信息学院（中国昆明）攻读医学信息工程工学学士学位，研究方向包括云服务保障、大语言模型评估、统计两样本检验与可信人工智能。

**Siqi Li**（通信作者，ORCID: `0009-0000-9194-7563`，邮箱：`lisiqi-vicky@foxmail.com`），信息科学博士，现为云南中医药大学信息学院（中国昆明）助理研究员，研究方向包括证据理论、知识工程、可信人工智能与医学人工智能。
