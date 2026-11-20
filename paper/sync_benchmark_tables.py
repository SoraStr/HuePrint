"""Render the manuscript's benchmark and calibration tables from immutable result JSON."""
from pathlib import Path
import json
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT / 'results' / 'benchmark' / (name + '.json')).read_text())
def mean(rows, key):
    assert rows, key
    return statistics.mean(r[key] for r in rows)
def pct(value):
    return f'{100 * value:.2f}%'
def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] + ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows])
E = r'$\tilde D_{\mathrm{E-reg}}$'
H = r'$D_{\mathrm{hyb}}$'
HR = r'$D_{\mathrm{hyb-reg}}$'
RM = r'$D_{\mathrm{RM}}$'

def render_tables(zh=False):
    base = read('baseline_results')['results']
    exact_mmd = json.loads((ROOT / 'results' / 'diagnostics' / 'exact_mmd_baselines.json').read_text())['results']
    comp = read('comparisons')
    cal = read('calibration_results')['operating_points']
    charts = read('color_spaces')['results']
    result = {}
    def select(dataset, n, metric, k, condition):
        source = exact_mmd if metric == 'string_mmd_u' else base
        return [r for r in source if (r['dataset'], r['n_total_per_cell'], r['metric'], r['K'], r['condition']) == (dataset, n, metric, k, condition)]
    rows = []
    HEX = r'$D_{\mathrm{hex}}$'
    for n in [6, 10, 20, 30]:
        for metric, label in [('string_mmd_u', 'Color MMD-U'), ('energy_reg', 'Color ' + E)]:
            vals = [pct(mean(select('S3_color', n, metric, k, 'clean'), 'eer')) for k in [1, 2, 4, 6, 8, 10]]
            rows.append([n, label, *vals, pct(mean(select('S3_color', n, metric, 10, 'jitter8'), 'eer'))])
        if n == 6:
            for dataset, metric, label in [('S3_color', 'hex_jsd', 'Color ' + HEX), ('S3_word', 'string_mmd_u', 'Word MMD-U'), ('S3_word', 'word_jsd', 'Word JSD')]:
                vals = [pct(mean(select(dataset, 6, metric, k, 'clean'), 'eer')) for k in [1, 2, 4, 6, 8, 10]]
                jitter = pct(mean(select(dataset, 6, metric, 10, 'jitter8'), 'eer')) if dataset == 'S3_color' else '—'
                rows.append([6, label, *vals, jitter])
    for dataset, metric, label in [('S3_color', 'hex_jsd', 'Color ' + HEX), ('S3_color', 'string_tv', 'Color TV'), ('S3_word', 'string_mmd_u', 'Word MMD-U'), ('S3_word', 'word_jsd', 'Word JSD')]:
        vals = [pct(mean(select(dataset, 30, metric, k, 'clean'), 'eer')) for k in [1, 2, 4, 6, 8, 10]]
        jitter = pct(mean(select(dataset, 30, metric, 10, 'jitter8'), 'eer')) if dataset == 'S3_color' else '—'
        rows.append([30, label, *vals, jitter])
    result['baseline'] = table(['N', '探针 / 统计量' if zh else 'Probe / statistic', 'K=1', 'K=2', 'K=4', 'K=6', 'K=8', 'K=10', 'K=10, ±8'], rows)
    scenarios = [('A_fresh', 'A'), ('B20x6', 'B 20×6'), ('B_full', 'B 40×15'), ('C_p1_within', 'C P1 within'), ('C_p2_within', 'C P2 within'), ('C_P0_to_P1', 'C P0 → P1'), ('C_P0_to_P2', 'C P0 → P2'), ('C_P0_to_P1_P2', 'C pooled'), ('E', 'E'), ('S1_CF0_CF21_6v6', 'S1 CF0 → CF21'), ('S1_CF21_OR21_6v6', 'S1 CF21 → OR21'), ('S1_CF0_OR21_6v6', 'S1 CF0 → OR21'), ('S1_CF21_within', 'S1 CF21 within'), ('S1_OR21_within', 'S1 OR21 within'), ('S2_cross_provider_6v6', 'S2 provider 6v6'), ('S2_cross_provider_3v3', 'S2 provider 3v3'), ('S3_color_within', 'S3 color 15v15'), ('S4a_within', 'S4a 5v5'), ('S4b_within', 'S4b 3v3'), ('S4b_explicit_to_implicit', 'S3a → S4b 6v6')]
    rows = [[label, *[pct(comp[name]['metrics'][metric]['eer']) for metric in ['energy_norm', 'energy_reg', 'hybrid', 'hybrid_reg']]] for name, label in scenarios]
    result['hybrid'] = table(['协议' if zh else 'Protocol', r'$\bar D_{\mathrm E}$', E, H, HR], rows)
    def ops(prefix, fit, metric, variant):
        return [r for r in cal if (r['scenario'] == prefix or r['scenario'].startswith(prefix + '_seed')) and r['calibration'] == fit and r['metric'] == metric and r['variant'] == variant and r['threshold_kind'] == 'tau_mid']
    def rates(rows):
        return pct(mean(rows, 'frr')) + ' / ' + pct(mean(rows, 'far'))
    rows = []
    for scenario, fit, label in [('E_clean', 'B3v3', 'E clean'), ('E_jitter8', 'B3v3', 'E ±8'), ('S1_CF0_CF21', 'B3v3', 'CF0 → CF21'), ('S1_CF21_OR21', 'B3v3', 'CF21 → OR21'), ('S1_CF0_OR21', 'B3v3', 'CF0 → OR21'), ('S1_CF0_CF21', 'B6v6', 'CF0 → CF21'), ('S1_CF21_OR21', 'B6v6', 'CF21 → OR21'), ('S1_CF0_OR21', 'B6v6', 'CF0 → OR21')]:
        rows.append([label, fit, rates(ops(scenario, fit, 'energy_reg', 'raw')), rates(ops(scenario, fit, 'energy_reg', 'self_Bcv'))])
    result['calibration'] = table(['条件' if zh else 'Condition', 'B calibration', 'Raw FRR / FAR', 'Self FRR / FAR'], rows)
    rows = []
    for dataset in ['B_full', 'B20x6', 'E', 'S3']:
        for cond in ['clean', 'jitter8']:
            vals = []
            for chart in ['RGB100', 'scaled_Lab_D65']:
                rs = [r for r in charts if (r['dataset'], r['condition'], r['chart']) == (dataset, cond, chart)]
                vals.append(pct(mean(rs, 'eer')) + f" / {mean(rs, 'auc'):.4f}")
            rows.append([dataset, 'clean' if cond == 'clean' else '±8', *vals])
    result['charts'] = table(['数据' if zh else 'Dataset', '条件' if zh else 'Condition', 'RGB100 EER / AUC', 'CIELAB EER / AUC'], rows)
    rows = []
    for scenario, metric, label in [('Bfull_jitter1', 'energy_reg', 'B jitter ±1'), ('Bfull_jitter8', 'energy_reg', 'B jitter ±8'), ('Bfull_jitter8', 'hybrid_reg', 'B jitter ±8'), ('Bfull_jitter15', 'energy_reg', 'B jitter ±15'), ('Bfull_shift8', 'energy_reg', 'Shift +8'), ('Bfull_shift-8', 'energy_reg', 'Shift -8'), ('Bfull_quant32', 'energy_reg', 'Quantization (step 32)')]:
        a = ops(scenario, 'B8v7', metric, 'raw'); b = ops(scenario, 'B8v7', metric, 'self_Bcv')
        rows.append([label, {'energy_reg': E, 'hybrid_reg': HR, 'robust_manifold': RM}[metric], pct(mean(a, 'eer')), rates(a), rates(b)])
    result['perturbation'] = table(['条件' if zh else 'Condition', '指标' if zh else 'Metric', 'Raw EER', 'Raw FRR / FAR', 'Self FRR / FAR'], rows)
    return result


def legacy_tables(zh=False):
    # Retained tables share their original frozen reports; presentation and
    # S4 filter denominators are regenerated instead of copying old prose.
    from sync_rgb_tables import tables as original_tables
    old=original_tables(zh)
    sym={'energy_norm':r'$\bar D_{\mathrm E}$','energy_reg':E,'hybrid':H,
         'hex_jsd':r'$D_{\mathrm{hex}}$','voxel_jsd':r'$D_{\mathrm{vox}}$',
         'robust_manifold':RM,'side_jsd':r'$D_{\mathrm{side}}$'}
    def symbols(text):
        for key,val in sym.items():
            text=text.replace('`'+key+'`',val)
            text=re.sub(r'(?<![\w{])'+key+r'(?![\w}])',lambda _:val,text)
        return text
    result={n:symbols(old[n]) for n in [2,4]}
    comp=read('comparisons')
    hybrid_eer=[pct(comp['A_fresh'][group]['hybrid']['eer'])
                for group in ['cross_sublineage','cross_family']]
    result[2]=result[2].replace('| — | — | 36/50',
                              '| '+ ' | '.join(hybrid_eer)+' | 36/50')
    side_eer=[pct(comp['A_fresh'][group]['side_jsd']['eer'])
              for group in ['cross_sublineage','cross_family']]
    side_loo=comp['A_fresh']['loo_family']['side_jsd']
    side_loo_str=f"{side_loo['correct']}/{side_loo['n']} ({100*side_loo['correct']/side_loo['n']:.2f}%)"
    result[2]=result[2].replace('| — | — | 16/50 (32.00%) |',
                              '| '+' | '.join(side_eer)+f' | {side_loo_str} |')
    diag=json.loads((ROOT/'results/diagnostics/operational_diagnostics.json').read_text())
    da_mmd=diag['dataset_a_color_mmd_u']['raw_string_mmd_u']
    mmd_row=f"| Color MMD-U | {da_mmd['auc']:.4f} | {da_mmd['eer_discrete_pct']:.2f}% / {da_mmd['eer_linear_pct']:.2f}% | {da_mmd['cross_sublineage_eer_pct']:.2f}% | {da_mmd['cross_family_eer_pct']:.2f}% | {da_mmd['loo_family_hits']} ({da_mmd['loo_family_pct']:.2f}%) |"
    t2_lines=[]
    for ln in result[2].splitlines():
        if ln.startswith(f'| {RM} |'):
            continue
        t2_lines.append(ln)
        if ln.startswith(f'| {E} |'):
            t2_lines.append(mmd_row)
    result[2]='\n'.join(t2_lines)
    s1=json.loads((ROOT/'extensions/live_validation_20261111/lv_rgb_results.json').read_text())['S1_longitudinal_t21d_and_cross_gateway']
    s1_diag=diag['study_s1_discrete_and_mmd_scores']
    s1_extra=[]
    for dkey,label in [('CF0_to_CF21','CF0 → CF21'),('CF21_to_OR21','CF21 → OR21'),('CF0_to_OR21','CF0 → OR21')]:
        hx=s1_diag[dkey]['hex_jsd_all14']
        s1_extra.append([label,sym['hex_jsd'],hx['top1_hits'],f"{hx['auc']:.4f}",f"{hx['eer_pct']:.2f}%",f"{hx['genuine_mean']:.4f} / {hx['impostor_mean']:.4f}",hx['frozen_b3v3_frr_far_pct']])
        mx=s1_diag[dkey]['color_mmd_u_raw_all14']
        s1_extra.append([label,'Color MMD-U',mx['top1_hits'],f"{mx['auc']:.4f}",f"{mx['eer_pct']:.2f}%",f"{mx['genuine_mean']:.4f} / {mx['impostor_mean']:.4f}",mx['frozen_b3v3_frr_far_pct']])
    for key,label,metric in [
        ('longitudinal_t0_to_t21d_cf_6v6_heldout4','CF0 → CF21 (heldout4)','robust_manifold'),
        ('cross_gateway_and_t21d_cf0_to_or21_6v6_all14','CF0 → OR21','side_jsd'),
    ]:
        x=s1[key][metric]
        frr_far=f"{x['frozen_frr_pct']:.2f}% / {x['frozen_far_pct']:.2f}%" if 'frozen_frr_pct' in x else '—'
        s1_extra.append([label,sym[metric],f"{x['top1_hits']}/{x['n_models']}",f"{x['auc_raw']:.4f}",f"{x['eer_linear_pct']:.2f}%",f"{x['genuine_mean']:.4f} / {x['impostor_mean']:.4f}",frr_far])
    result[6]=table(['注册 → 查询 (6v6)' if zh else 'Enrollment → query (6v6)','Metric','Top-1','AUC','Linear EER','正例 / 负例均值' if zh else 'Genuine / impostor mean','冻结 B3v3 FRR / FAR' if zh else 'Frozen B3v3 FRR / FAR'],s1_extra)
    review=json.loads((ROOT/'results/corpus_stats/analysis.json').read_text())
    rows=[]
    for reg in ['matched','moderate','aggressive','unspecified_precision']:
        for metric in ['hybrid','energy_reg']:
            x=review['precision']['regimes'][reg][metric]
            rows.append([reg.replace('_',' '),sym[metric],x['pairs'],f"{x['mean']:.4f} ± {x['sd']:.4f}",f"{pct(x['top1'])} ({x['queries']})",f"{x['auc']:.4f}",pct(x['eer'])])
    result[7]=table(['精度组' if zh else 'Precision regime','Metric','Pairs','Mean ± SD','1-NN (queries)','AUC','Linear EER'],rows)
    rows=[]
    for name in ['B','C_P1','C_P2','E','S1_CF21_heldout4','S1_OR21_heldout4']:
        x=review['bootstrap'][name]['energy_reg']
        rows.append([name.replace('_',' '),x['n_model_clusters'],f"{x['point']['auc']:.4f} [{x['auc_ci95'][0]:.4f}, {x['auc_ci95'][1]:.4f}]",f"{pct(x['point']['eer'])} [{pct(x['eer_ci95'][0])}, {pct(x['eer_ci95'][1])}]"])
    result[3]=table(['队列' if zh else 'Cohort','模型数' if zh else 'Models','AUC [95% CI]','Linear EER [95% CI]'],rows)
    comp=read('comparisons');counts=json.loads((ROOT/'results/diagnostics/s4_filter_counts.json').read_text())
    rows=[]
    for name,key,label in [('S3a','S3_color_within','S3a (10 probes; 15v15)'),('S4a','S4a_within','S4a (5v5)'),('S4b','S4b_within','S4b (3v3)'),(None,'S4b_explicit_to_implicit','S3a → S4b (6v6)')]:
        bypass=['—']*3
        if name:
            x=counts[name];n=x['counts']['total']
            bypass=[pct(x['counts'][k]/n) for k in ['input_bypass','output_bypass','valid_and_unflagged']]
            if name=='S4a':bypass[2]+=' (3192/3200)'
        vals=comp[key]['metrics']
        rows.append([label,*bypass,*[f"{pct(vals[m]['top1'])} / {vals[m]['auc']:.4f} / {pct(vals[m]['eer'])}" for m in ['energy_reg','hybrid']]])
    result[9]=table(['探针及协议' if zh else 'Battery and protocol','输入未触发率' if zh else 'Unflagged input','输出未触发率' if zh else 'Unflagged output','有效且未触发' if zh else 'Valid and unflagged',E+': Top-1 / AUC / EER',H+': Top-1 / AUC / EER'],rows)
    return result

def sync(check=False):
    for lang in ['EN', 'ZH']:
        paths=[ROOT/'paper'/f'{stem}_{lang}.md' for stem in ['MANUSCRIPT','SUPPLEMENT']]
        texts={path:path.read_text() for path in paths if path.exists()}
        blocks={f'BENCH_TABLE_{name}':content for name,content in render_tables(lang=='ZH').items()}
        blocks.update({f'RGB_TABLE_{number}':content for number,content in legacy_tables(lang=='ZH').items()})
        for marker,content in blocks.items():
            pattern=rf'<!-- {marker} -->[\s\S]*?<!-- /{marker} -->'
            owners=[path for path,text in texts.items() if re.search(pattern,text)]
            assert len(owners)==1,(lang,marker,owners)
            path=owners[0];block=f'<!-- {marker} -->\n{content}\n<!-- /{marker} -->'
            if check:assert re.search(pattern,texts[path])[0]==block,(lang,marker)
            else:texts[path]=re.sub(pattern,lambda _:block,texts[path])
        if not check:
            for path,text in texts.items():path.write_text(text)
    print('Offline result tables verified.' if check else 'Offline result tables synchronized.')

if __name__ == '__main__':
    sync('--check' in sys.argv)
