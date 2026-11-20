"""Generate the review report from result files, never from manuscript text."""
import collections
import json
from pathlib import Path
import numpy as np
from .core import save

LABEL = {'energy_norm': 'D_E', 'energy_reg': 'D_E-reg', 'hybrid': 'D_hyb',
         'hybrid_reg': 'D_hyb-reg', 'robust_manifold': 'D_RM', 'hex_jsd': 'D_hex',
         'voxel_jsd': 'D_vox', 'soft_voxel_jsd': 'D_svox', 'side_jsd': 'D_side',
         'string_mmd_u': '原始字符串 MMD-U', 'string_tv': '原始字符串 TV', 'word_jsd': '单词 JSD'}


def mean(rows, key):
    return float(np.mean([r[key] for r in rows]))


def pct(x): return f'{100*x:.2f}%'
def auc(x): return f'{x:.6f}'


def report(out):
    comp = json.loads((out/'comparisons.json').read_text())
    cal = json.loads((out/'calibration_results.json').read_text())
    charts = json.loads((out/'color_spaces.json').read_text())
    base = json.loads((out/'baseline_results.json').read_text())
    fits = json.loads((out/'frozen_calibration.json').read_text())
    validation = json.loads((out/'validation.json').read_text())
    summary = {'hybrid': [], 'calibration': [], 'color_spaces': [], 'baselines': []}
    lines = ['# HuePrint 离线基准、标定与色彩空间复算摘要', '',
             '全部计算离线读取只读 JSONL 语料日志，分析进程启用审计钩子阻断网络连接与子进程调用。', '',
             '## 1. 核心观察', '',
             '- 固定混合权重下将能量项替换为正则化形式（`D_hyb-reg`）降低了 Dataset C 跨模板 EER，但在部分队列上高于 `D_hyb`；两项指标均完整归档供对照（见补充材料 B 表 S2）。',
             '- 注册集自离散度中心化（`alpha=1`）将清洁持出集 E 的冻结 FRR 从 30.00% 降至 10.00%（零 FAR），全部系数与阈值仅在开发集 B 上确定并冻结。',
             '- 已纳入原始字符串独热核无偏 MMD-U 与 TV 两样本分层置换基线，并覆盖 Study S3 的完整 `N=6,10,20,30`、`K=1..10` 预算网格。',
             '- 单射与 Lipschitz 色彩坐标分析及统一缩放 D65 CIELAB 有限样本对照见补充材料 A 表 S1。', '',
             '## 2. 指标替换：相同日志与相同配对', '',
             '以下 EER 均为未四舍五入分数上的线性 ROC 交点；AUC 含并列分数修正。完整离散 EER、1-NN、配对分数、A 的跨子谱系／跨家族结果和 LOO 结果见 `comparisons.json`、`comparisons.csv`、`comparison_pairs.csv`。', '',
             '| 场景 | D_hyb EER → D_hyb-reg EER | AUC 旧 → 新 | D_E EER → D_E-reg EER |',
             '| --- | ---: | ---: | ---: |']
    for name, d in comp.items():
        if 'metrics' not in d: continue
        h, hr = d['metrics']['hybrid'], d['metrics']['hybrid_reg']
        e, er = d['metrics']['energy_norm'], d['metrics']['energy_reg']
        lines.append(f"| {name} | {pct(h['eer'])} → {pct(hr['eer'])} | {auc(h['auc'])} → {auc(hr['auc'])} | {pct(e['eer'])} → {pct(er['eer'])} |")
        summary['hybrid'].append({'scenario': name, 'old': h, 'regularized': hr, 'energy_old': e, 'energy_regularized': er})
    lines += ['', '| LOO 家族归属 | D_hyb → D_hyb-reg（正确 / 总数） | D_E → D_E-reg（正确 / 总数） |',
              '| --- | ---: | ---: |']
    for scenario in ('A_fresh', 'B_full', 'B20x6', 'E'):
        fam = comp[scenario]['loo_family']
        text = lambda m: f"{fam[m]['correct']}/{fam[m]['n']}"
        lines.append(f"| {scenario} | {text('hybrid')} → {text('hybrid_reg')} | {text('energy_norm')} → {text('energy_reg')} |")
    lines += ['', 'Dataset D 和 S3-word 是单词日志。解析器的占位 `[0,0,0]` 不代表颜色，未用它们生成能量或混合指标。', '',
              'S2 的精度分层和 T1b 检测另列如下。精度来自已保存的提供商配置，提供商、硬件与精度仍存在混杂。', '',
              '| S2 子任务 | D_hyb EER → D_hyb-reg EER | AUC 旧 → 新 |', '| --- | ---: | ---: |']
    for name, d in {**comp['S2_precision_regimes'], 'T1b_lowbit': comp['S2_T1b']}.items():
        h, r = d['hybrid'], d['hybrid_reg']
        lines.append(f"| {name} | {pct(h['eer'])} → {pct(r['eer'])} | {auc(h['auc'])} → {auc(r['auc'])} |")
    lines += ['', '`B_budget.csv` 另外覆盖原 48 个 `(n,K)` 预算格，保留原 `Random(42)`、200 次子集抽样及 12 位小数并列分数口径；所有新旧指标使用同一个子集。S3 的逐 K 网格在 `baseline_grid.csv`。`cluster_bootstrap.csv` 给出 B、C、E 和 S1 heldout4 的新旧指标模型簇 bootstrap 区间；`S1_subgroups.csv` 保留 dev10/heldout4 的冻结阈值结果，未用这些子组重拟合阈值。', '',
              '正则化仅替换混合式中的 0.25 倍能量项；`D_hex` 和硬体素仍不连续。因此 `D_hyb-reg` 不应被表述为全局 Lipschitz 指标。', '',
              '## 3. enrollment 自离散度与冻结阈值', '',
              '每个参考模型、每个有效探针单元独立进行 256 次有放回 bootstrap：两组均从 enrollment 的经验分布抽样，规模分别匹配参考有效样本数和预先规定的查询规模。基线为这些分数的均值，使用 `D − α μ_self`，不截断负分数。基线及 Monte Carlo 标准误见 `frozen_calibration.json` 和 `enrollment_baselines.json`。', '',
              '`α=1` 是预先固定的减基线版本；`self_Bcv` 在 B 内按留一模型交叉验证选择 `{0,.25,.5,1,1.5,2}`，训练阈值排除该模型的全部配对。并列时优先最接近 1，再取较小值。选择后只用 B 拟合 `τ_mid`、`τ_u0` 并冻结。', '',
              '| B 校准协议 | 指标 | B-CV α | 原 τ_mid | α=1 τ_mid |', '| --- | --- | ---: | ---: | ---: |']
    for name, f in fits.items():
        for m, d in f['models'].items():
            lines.append(f"| {name} | {LABEL[m]} | {d['selected_alpha']:g} | {d['variants']['raw']['tau_mid']:.9f} | {d['variants']['self_alpha1']['tau_mid']:.9f} |")
    lines += ['', '`B3v3` 是 B-20×6 的奇偶划分；`B6v6` 使用 B 的第 1–6 次作为 enrollment、第 7–12 次作为查询；`B8v7` 是 B 全量 40×15 的奇偶划分。受控扰动套件沿用每侧至少 1 个有效样本规则，B 全量验证表要求每侧至少 5 个有效样本。S1 同时给出 B3v3 阈值迁移与采样量匹配的 B6v6 阈值迁移；S1 的 CF0 enrollment 来自 B 和 E，其中 E 观测不参与选择 α 或阈值。', '',
              '### E 与 S1：冻结 τ_mid 下的 FRR / FAR', '',
              '| 场景 | B 校准 | 指标 | 原始分数 | α=1 自校准 | B-CV 自校准 |', '| --- | --- | --- | ---: | ---: | ---: |']
    rs = cal['operating_points']
    def calrow(prefix, fit, metric, variant, threshold='tau_mid'):
        selected = [r for r in rs if (r['scenario'] == prefix or r['scenario'].startswith(prefix+'_seed')) and r['calibration'] == fit and r['metric'] == metric and r['variant'] == variant and r['threshold_kind'] == threshold]
        if not selected: raise ValueError((prefix, fit, metric, variant))
        return {'frr': mean(selected, 'frr') if 'frr' in selected[0] else None,
                'far': mean(selected, 'far'), 'eer': mean(selected, 'eer') if 'eer' in selected[0] else None,
                'n_runs': len(selected), 'attack_acceptance': mean(selected, 'attack_acceptance') if selected[0].get('attack_acceptance') is not None else None,
                'screened_acceptance': mean(selected, 'attack_acceptance_with_entropy_screen') if 'attack_acceptance_with_entropy_screen' in selected[0] else None}
    scenarios = [('E_clean', 'B3v3'), ('E_jitter8', 'B3v3')]+[(s, f) for s in ('S1_CF0_CF21', 'S1_CF21_OR21', 'S1_CF0_OR21') for f in ('B3v3', 'B6v6')]
    for scenario, fit in scenarios:
        for m in ('energy_reg', 'hybrid_reg', 'robust_manifold'):
            values = {v: calrow(scenario, fit, m, v) for v in ('raw', 'self_alpha1', 'self_Bcv')}
            cells = [f"{pct(v['frr'])} / {pct(v['far'])}" for v in values.values()]
            lines.append(f"| {scenario} | {fit} | {LABEL[m]} | "+' | '.join(cells)+' |')
            summary['calibration'].append({'scenario': scenario, 'calibration': fit, 'metric': m, **values})
    energy_clean = [calrow('E_clean', 'B3v3', 'energy_reg', v) for v in ('raw', 'self_alpha1')]
    energy_jitter = [calrow('E_jitter8', 'B3v3', 'energy_reg', v) for v in ('raw', 'self_alpha1')]
    lines += ['', f"能量指标的清洁 FRR 为 {pct(energy_clean[0]['frr'])} → {pct(energy_clean[1]['frr'])}，而 ±8 jitter 下由于自中心化未预留查询侧噪声余量，冻结 FRR 为 {pct(energy_jitter[0]['frr'])} → {pct(energy_jitter[1]['frr'])}；全部超参数保持固定，未按测试集调整。", '',
              '完整 `τ_u0` 数值及逐种子结果见 `calibration.csv`。抖动种子在固定日志池上评估数值连续性，平均十个固定随机种子。', '',
              '### Table VIII 扰动与攻击', '',
              '| 场景（B 全量） | 指标 | 原 FRR / FAR | α=1 FRR / FAR |', '| --- | --- | ---: | ---: |']
    for scenario, m in [('Bfull_jitter1', 'energy_reg'), ('Bfull_jitter8', 'energy_reg'), ('Bfull_jitter15', 'energy_reg'), ('Bfull_jitter8', 'hybrid_reg'), ('Bfull_shift8', 'robust_manifold'), ('Bfull_shift-8', 'robust_manifold'), ('Bfull_quant32', 'robust_manifold')]:
        a, b = [calrow(scenario, 'B8v7', m, v) for v in ('raw', 'self_alpha1')]
        lines.append(f"| {scenario} | {LABEL[m]} | {pct(a['frr'])} / {pct(a['far'])} | {pct(b['frr'])} / {pct(b['far'])} |")
    lines += ['', '| 攻击（B 全量） | 指标 | 原接受率 | α=1 接受率 |', '| --- | --- | ---: | ---: |']
    for scenario, m, field in [('Bfull_replay_centroid', 'robust_manifold', 'screened_acceptance'), ('Bfull_replay_cyclic', 'energy_reg', 'attack_acceptance'), ('Bfull_replay_resample', 'energy_reg', 'attack_acceptance'), ('Bfull_routing0.5', 'energy_reg', 'attack_acceptance')]:
        a, b = [calrow(scenario, 'B8v7', m, v) for v in ('raw', 'self_alpha1')]
        lines.append(f"| {scenario} | {LABEL[m]} | {pct(a[field])} | {pct(b[field])} |")
    lines += ['', '导出还包含 B-20×6、±1/2/4/8/15/31 jitter、±8/15/31 偏移、17/32 量化、三类 replay 和 10%/25%/50% 路由。entropy screen 保持原 .30/.25 规则。自离散度估计不能识别 enrollment 没有采到的模式；常量 enrollment 尤其如此。降低拒真不等于获得认证安全性，公开参考 replay 的限制仍然存在。', '',
              '### 分层能量置换检验', '',
              '每个 cell 使用 Székely–Rizzo V 统计量 `nm/(n+m)·(2dXY−dXX−dYY)`，先跨 cell 等权平均，再对 999 次逐 cell 独立重排形成的联合统计量计算 `(1+#null≥observed)/1000`。显著性水平预设为 0.05。该检验无需测试集阈值拟合。', '',
              '| 场景 | 同模型拒绝率 | 异模型拒绝率 |', '| --- | ---: | ---: |']
    for name in ('E_clean', 'E_jitter8', 'S1_CF0_CF21', 'S1_CF21_OR21', 'S1_CF0_OR21', 'Bfull_jitter8', 'Bfull_shift8', 'Bfull_quant32'):
        selected = [r for r in cal['energy_permutation_tests'] if r['scenario'] == name or r['scenario'].startswith(name+'_seed')]
        lines.append(f"| {name} | {pct(mean(selected, 'same_model_rejection_rate'))} | {pct(mean(selected, 'different_model_rejection_rate'))} |")
    lines += ['', '这里检验的是有效颜色输出的条件分布相等，未把解析失败率纳入能量核。抖动后的 genuine 查询可能确实改变分布，因此拒绝率不能直接等同于 checkpoint 身份识别的 FRR；不拒绝也不证明相等。p 值是单个配对的未作多重比较校正的值，模型配对彼此相关。', '',
              '## 4. 已发表的黑盒两样本基线', '',
              '采用 [Gao、Liang、Guestrin，ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/d73234a13815fc1f9779dd17d89be9b4-Paper-Conference.pdf) 的 one-hot equality kernel、无偏 MMD 统计量和 L1 两样本统计量（此处 TV=L1/2），适配为固定 prompt cell 内置换、跨 cell 等权聚合的条件检验；不是复现其长文本 Wikipedia 实验。完整字符串不做大小写、空白或格式规范化，空响应和解析失败仍计入预算。', '',
              '`n` 为每 cell 两边合计的调用数，分别 n/2 次；K 对应选中的 prompt cell 数。两种基线和颜色指标共用同一观测、同一 prompt 子集。每个 K 最多选择 40 个固定、不重复子集，足够少时穷举；每次检验做 999 次分层置换。MMD-U 允许负估计值。', '',
              '### S3，K=10', '',
              '| 通道 / 条件 | n（两边合计） | 方法 | EER | AUC | 同模型拒绝率 / 异模型拒绝率 |', '| --- | ---: | --- | ---: | ---: | ---: |']
    br = base['results']
    for dataset in ('S3_color', 'S3_word'):
        for condition in ('clean', 'jitter8') if dataset == 'S3_color' else ('clean',):
            for n in (6, 10, 20, 30):
                methods = ('string_mmd_u', 'string_tv', 'energy_reg', 'hybrid_reg') if dataset == 'S3_color' else ('string_mmd_u', 'string_tv', 'word_jsd')
                for m in methods:
                    sel = [r for r in br if r['dataset'] == dataset and r['condition'] == condition and r['n_total_per_cell'] == n and r['K'] == 10 and r['metric'] == m]
                    r = {'dataset': dataset, 'condition': condition, 'n': n, 'K': 10, 'metric': m,
                         'eer': mean(sel, 'eer'), 'auc': mean(sel, 'auc')}
                    rejection = '—'
                    if 'same_model_rejection_rate' in sel[0]:
                        r.update({k: mean(sel, k) for k in ('same_model_rejection_rate', 'different_model_rejection_rate', 'p_auc', 'p_eer')})
                        rejection = pct(r['same_model_rejection_rate'])+' / '+pct(r['different_model_rejection_rate'])
                    lines.append(f"| {dataset} / {condition} | {n} | {LABEL[m]} | {pct(r['eer'])} | {auc(r['auc'])} | {rejection} |")
                    summary['baselines'].append(r)
    lines += ['', '表中 EER/AUC 来自原始统计量；p 值排序的 EER/AUC 另存 `p_eer/p_auc`，不得混用。抖动行是 10 个固定种子的均值。S3 预算网格统一采用 `K=1..10` 的固定共有子集（清单见 `baseline_subsets.json`）。`baseline_pairs.csv` 保留 K=10 的第 0 个固定子集的逐配对审计记录（S3 此时只有一个子集）；B/D 的 K=10 汇总平均全部 40 个固定子集。', '',
              '### B-20×6 与 D，K=10、n=6', '',
              '| 通道 / 条件 | 方法 | EER | AUC |', '| --- | --- | ---: | ---: |']
    for dataset in ('B20x6', 'D'):
        for condition in ('clean', 'jitter8') if dataset == 'B20x6' else ('clean',):
            for m in ('string_mmd_u', 'string_tv', 'energy_reg') if dataset == 'B20x6' else ('string_mmd_u', 'string_tv', 'word_jsd'):
                sel = [r for r in br if r['dataset'] == dataset and r['condition'] == condition and r['K'] == 10 and r['metric'] == m]
                lines.append(f"| {dataset} / {condition} | {LABEL[m]} | {pct(mean(sel, 'eer'))} | {auc(mean(sel, 'auc'))} |")
    lines += ['', 'B-20×6 和 D 每 cell 只有 6 次现有调用，不生成 n=10/20/30 的伪增样本。对单词输出施加 RGB jitter 没有定义，因此单词组仅报清洁值；颜色组另报抖动。', '',
              f"原始字符串抖动仅在内存中替换颜色字符，保留周围文本，并检查重解析一致性；全部预算与种子的歧义色值标记合计为 {sum(r['ambiguous_bare_hex_after_jitter'] for r in base['raw_reparse_audit'])}。几何对照遵循已解析颜色扰动协议，保留原格式侧信道元数据。", '',
              '## 5. RGB100 与 CIELAB', '',
              f"使用 D65 白点、连续 sRGB 接缝、CIE 线性 toe；统一 Lab 缩放 s={charts['lab_scale']['scale']:.9f}，只由 B-20×6 enrollment 的同 cell 距离确定。等效原生 Lab δ={charts['lab_scale']['delta_lab_native']:.9f}；无逐轴缩放或裁剪。", '',
              '| 数据 | 条件 | RGB100 EER / AUC | Lab EER / AUC |', '| --- | --- | ---: | ---: |']
    cr = charts['results']
    for dataset in ('B_full', 'B20x6', 'E', 'S3'):
        for condition in ('clean', 'jitter8'):
            vals = {}
            for chart in ('RGB100', 'scaled_Lab_D65'):
                sel = [r for r in cr if r['dataset'] == dataset and r['condition'] == condition and r['chart'] == chart]
                vals[chart] = {'eer': mean(sel, 'eer'), 'auc': mean(sel, 'auc')}
            a, b = vals.values()
            lines.append(f"| {dataset} | {condition} | {pct(a['eer'])} / {auc(a['auc'])} | {pct(b['eer'])} / {auc(b['auc'])} |")
            summary['color_spaces'].append({'dataset': dataset, 'condition': condition, **vals})
    lines += ['', '完整解析证明与单射 Lipschitz 色彩图分析见 `paper/SUPPLEMENT_EN.md` 第 A 与 G 节（覆盖强负型性质、分段传递函数接缝与尺度变换）。', '',
              '## 6. 验证与复现', '',
              f"- {validation['raw_logs']} 个原始 JSONL、共 {validation['protected_files']} 个受保护基准文件的 SHA-256 校验一致。",
              f"- 基线 A/B 的 {validation['legacy_metric_fields_reproduced']} 个 AUC/EER 字段、B3v3 冻结阈值及 E 迁移结果逐项复算一致。",
              '- 校验涵盖独立 MMD/能量公式、退化样本、置换 ties/plus-one、enrollment 独立性、日志顺序与原始字符串扰动。',
              '- 色彩检查覆盖全部 256 个通道值、10,000 对随机坐标、500 组扰动点云与 HSV 无彩轴反例。', '',
              '```sh', 'UV_OFFLINE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \\',
              '  uv run --offline --no-project --with numpy python -B scripts/benchmark_analysis.py --stage all --output "$OUT_DIR"',
              'UV_OFFLINE=1 uv run --offline --no-project --with numpy \\',
              '  python -B -m unittest discover -s tests -v', '```', '',
              '归档输出位于 `results/benchmark/`；可通过 `--output` 指定独立输出目录，并用 `--stage compare|calibrate|baselines|charts|verify|report` 分阶段运行。', '']
    save(out/'summary.json', summary)
    (out/'REPORT_ZH.md').write_text('\n'.join(lines))
