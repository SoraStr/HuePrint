"""Render/check manuscript tables from the frozen RGB reports; no model calls."""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
M = json.loads((ROOT/'data/reproduce_all_rgb_summary.json').read_text())
L = json.loads((ROOT/'extensions/live_validation_20261111/lv_rgb_results.json').read_text())
assert M['analysis_protocol'] == L['analysis_protocol']
assert M['analysis_protocol']['version'] == 'rgb100_v1_20261111'


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |'] + ['| '+' | '.join(map(str,r))+' |' for r in rows])


def pct(x): return f'{x:.2f}%'
def auc(x): return f'{x:.4f}'
def family(x): return f"{x['correct']}/{x['total']} ({x['accuracy_pct']:.2f}%)"


def tables(zh):
    out={}
    a=M['dataset_A_56models']; legacy=a['with_legacy_reasoning_meta']; fresh=a['fresh_raw_only_no_legacy_meta']
    rows=[]
    for metric,mode in [('energy_norm',legacy),('energy_reg',legacy),('hybrid',fresh),('hex_jsd',legacy),('voxel_jsd',legacy),('side_jsd',fresh)]:
        r=mode['roc_raw'][metric]
        label=f'`{metric}`'
        rows.append([label,auc(r['auc_raw']),pct(100*r['eer_raw'])+' / '+pct(100*r['eer_linear_raw']),pct(100*mode['roc_cross_sublineage'][metric]['eer_linear_raw']) if 'roc_cross_sublineage' in mode else '—',pct(100*mode['roc_cross_family'][metric]['eer_linear_raw']) if 'roc_cross_family' in mode else '—',family(mode['loo_family'][metric])])
    out[2]=table(['指标' if zh else 'Metric','AUC','离散 / 线性 EER' if zh else 'Discrete / linear EER','跨子谱系线性 EER' if zh else 'Cross-sublineage linear EER','跨家族线性 EER' if zh else 'Cross-family linear EER','LOO 家族归属' if zh else 'LOO family attribution'],rows)
    grid=M['dataset_B_40u15r']['grid_2d_n_by_k']['grid_hybrid']
    out[3]=table(['n / k']+[str(k) for k in [1,2,4,8,16,24,32,40]],[[str(n)]+[pct(grid[str(n)][str(k)]['mean_discrete_eer_pct'])+' / '+pct(grid[str(n)][str(k)]['tie_stable_12dp_linear_eer_pct']) for k in [1,2,4,8,16,24,32,40]] for n in [4,6,8,10,12,15]])
    metrics=['energy_reg','hybrid','voxel_jsd','hex_jsd']
    c=M['dataset_C_paraphrase_matrix'];rows=[]
    for key,label in [('P1_self_odd_even','P1 odd/even'),('P2_self_odd_even','P2 odd/even'),('P1','P0 → P1'),('P2','P0 → P2'),('P1_P2_pooled','P0 → P1+P2')]:
        rows.append([label]+[pct(c[key][m]['eer_linear_pct'])+' / '+auc(c[key][m]['auc'])+(f" ({c[key][m]['top1_checkpoint']})" if 'top1_checkpoint' in c[key][m] else '') for m in metrics])
    out[4]=table(['协议；线性 EER / AUC（Top-1）' if zh else 'Protocol; linear EER / AUC (Top-1)']+metrics,rows)
    s3=L['S3_locked_hyperparameter_parity_n30'];rows=[]
    for n,ms in [(6,['bruckner','hybrid','energy_reg']),(10,['bruckner','robust_manifold','energy_reg']),(20,['bruckner','robust_manifold','energy_reg']),(30,['bruckner','hex_jsd','robust_manifold','hybrid','energy_reg'])]:
        g=s3['parity_grid_r_by_K'][f'n{n}_{n//2}v{n//2}']
        for m in ms:
            vals=[]
            for k in [1,2,4,6,8,10]:
                x=g[f'K{k}']['bruckner_jsd'] if m=='bruckner' else g[f'K{k}']['hueprint'][m]
                vals.append(f"{pct(x['eer_linear_pct'])} ({x['top1_pct']:.1f}%)"+(f" / {auc(x['auc_raw'])}" if k==10 else ''))
            jit='—'
            if n==30 and m!='bruckner':
                x=s3['jitter_pm8_on_20models_15v15']['metrics'][m];jit=f"{pct(x['eer_linear_pct'])} ({x['top1_pct']:.1f}%)"
            rows.append([str(n),'Bruckner JSD' if m=='bruckner' else f'`{m}`']+vals+[jit])
    out[5]=table(['n','方法' if zh else 'Method']+[f'K={k}' for k in [1,2,4,6,8]]+['K=10 / AUC','±8 RGB'],rows)
    s1=L['S1_longitudinal_t21d_and_cross_gateway'];rows=[]
    for key,label,ms in [('longitudinal_t0_to_t21d_cf_6v6_all14','CF0 → CF21',['robust_manifold','energy_reg','hybrid','hex_jsd']),('longitudinal_t0_to_t21d_cf_6v6_heldout4','CF0 → CF21 (heldout4)',['robust_manifold','energy_reg','hybrid']),('cross_gateway_same_day_cf21_to_or21_6v6_all14','CF21 → OR21',['robust_manifold','energy_reg','hybrid']),('cross_gateway_and_t21d_cf0_to_or21_6v6_all14','CF0 → OR21',['robust_manifold','energy_reg','hybrid','side_jsd'])]:
        for m in ms:
            x=s1[key][m]
            rows.append([label,f'`{m}`',f"{x['top1_hits']}/{x['n_models']}",auc(x['auc_raw']),pct(x['eer_linear_pct']),f"{x['genuine_mean']:.4f} / {x['impostor_mean']:.4f}",pct(x['frozen_frr_pct'])+' / '+pct(x['frozen_far_pct']) if 'frozen_frr_pct' in x else '—',pct(x['frozen_balanced_err_pct']) if 'frozen_balanced_err_pct' in x else '—'])
    out[6]=table(['注册 → 查询' if zh else 'Enrollment → query','Metric','Top-1','AUC','Linear EER','正例 / 负例均值' if zh else 'Genuine / impostor mean','冻结 FRR / FAR' if zh else 'Frozen FRR / FAR','冻结均衡错误率' if zh else 'Frozen balanced error'],rows)
    rows=[]
    for m in ['hybrid','robust_manifold','energy_reg','hex_jsd','voxel_jsd']:
        x=L['S2_multiprovider_disentanglement']['metrics'][m]
        rows.append([f'`{m}`',f"{x['tier2_same_weights_cross_provider_6v6_mean']:.4f}",f"{x['tier3_diff_weights_6v6_mean']:.4f}",x['cross_provider_1nn_weight_hits_6v6'],auc(x['cross_provider_auc_raw_6v6']),pct(x['cross_provider_eer_linear_pct_6v6'])])
    out[7]=table(['Metric','同组跨供应商均值' if zh else 'Within-label cross-provider mean','异组均值' if zh else 'Between-label mean','1-NN','AUC','Linear EER'],rows)
    rows=[]
    for cohort,amps,ms in [('B_40x15',[1,8,15],['robust_manifold','energy_reg','hybrid','hex_jsd']),('B_20x6',[8],['energy_reg','robust_manifold'])]:
        for amp in amps:
            x=M['attack_suites'][cohort]['uniform_jitter'][f'±{amp}']
            for m in ms:
                v=x[m];rows.append([f'{cohort} ±{amp}',f"{x['mean_scaled_rgb_displacement']:.2f}",f'`{m}`',pct(v['eer_linear_pct'])+' / '+auc(v['auc']),pct(v['frr_midpoint_pct'])+' / '+pct(v['far_midpoint_pct'])])
    x=M['dataset_E_heldout_confirmation']['out_of_sample_jitter_transfer']['±8']
    for m in ['energy_reg','hex_jsd']:
        v=x['metrics'][m];rows.append(['E ±8',f"{x['mean_scaled_rgb_displacement']:.2f}",f'`{m}`',pct(v['heldout_eer_linear_pct'])+' / '+auc(v['heldout_auc']),pct(v['test_frr_at_frozen_mid_pct'])+' / '+pct(v['test_far_at_frozen_mid_pct'])])
    for typ,keys in [('directional_shift',['+8','-8']),('palette_quant',['step_17','step_32'])]:
        for key in keys:
            x=M['attack_suites']['B_40x15'][typ][key];v=x['metrics']['robust_manifold']
            rows.append([f'B_40x15 {typ} {key}',f"{x['mean_scaled_rgb_displacement']:.2f}",'`robust_manifold`',pct(v['eer_linear_pct'])+' / '+auc(v['auc']),pct(v['frr_midpoint_pct'])+' / '+pct(v['far_midpoint_pct'])])
    out[8]=table(['场景' if zh else 'Scenario','平均 RGB100 位移' if zh else 'Mean RGB100 displacement','Metric','重扫线性 EER / AUC' if zh else 'Re-swept linear EER / AUC','冻结 FRR / FAR' if zh else 'Frozen FRR / FAR'],rows)
    s4=L['S4_implicit_stealth_and_filter_evasion'];rows=[]
    for label,vals,bypass in [('S3a (10 probes; 15v15)',s3['headline_n30_15v15_K10']['hueprint'],['0.00%','0.73%','0.00%']),('S4a (5v5)',s4['s4a_within_implicit_css_5v5_verification'],['100.00%','99.97%','99.75% (3192/3200)']),('S4b (3v3)',s4['s4b_within_v5_implicit_3v3_verification'],['0.00%',pct(100*48/1920),'0.00%']),('S3a → S4b (6v6)',s4['s4b_cross_phrasing_s3_explicit_to_s4b_implicit_en8_6v6'],['—']*3)]:
        rows.append([label]+bypass+[f"{v['top1_pct']:.2f}% / {auc(v['auc_raw'])} / {pct(v['eer_linear_pct'])}" for v in [vals['energy_reg'],vals['hybrid']]])
    out[9]=table(['探针及协议' if zh else 'Battery and protocol','输入绕过率' if zh else 'Input bypass','输出绕过率' if zh else 'Output bypass','有效且未触发' if zh else 'Valid and unflagged','energy_reg: Top-1 / AUC / EER','hybrid: Top-1 / AUC / EER'],rows)
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    for lang in ['ZH','EN']:
        path=ROOT/f'paper/MANUSCRIPT_{lang}.md';text=path.read_text()
        for number,body in tables(lang=='ZH').items():
            marker=f'<!-- RGB_TABLE_{number} -->';end=f'<!-- /RGB_TABLE_{number} -->'
            if marker in text:
                old=text[text.index(marker):text.index(end)+len(end)]
            else:
                blocks=list(re.finditer(r'^\|[^\n]*\n(?:\|[^\n]*(?:\n|$))+',text,re.M))
                old=blocks[number-1].group().rstrip('\n')
            new=marker+'\n'+body+'\n'+end
            if args.check:
                assert old==new,f'{path.name}: table {number} differs from report'
            else:text=text.replace(old,new,1)
        if not args.check:path.write_text(text)
    print('RGB tables verified against both reports.' if args.check else 'Updated RGB tables in both manuscripts.')

if __name__=='__main__':main()
