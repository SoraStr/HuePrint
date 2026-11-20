"""Synchronize the service-audit, V/U, and overhead tables from immutable offline reports."""
from pathlib import Path
import json,re,statistics,sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'
def load(path):return json.loads((OUT/path).read_text())
def pct(x):return f'{100*x:.2f}%'
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def tables(zh=False):
 result={};data=load('service_audit/same_family.json')['results'];rows=[]
 comparisons=json.loads((ROOT/'results/benchmark/comparisons.json').read_text())
 for key,label in [('A_fresh',r'A ($8\times6$)'),('B20x6',r'B ($20\times6$)'),('B_full',r'B ($40\times15$)'),('E',r'E ($20\times6$)$^*$'),('S3_color_within',r'S3 ($10\times30$)')]:
  subset={x['metric']:x for x in data if x['scenario']==key and x['negative_group']=='same_family'}
  e,h=subset['energy_reg'],subset['hybrid'];allpairs=comparisons[key]['metrics']
  rows.append([label,e['n_directed_negative'],pct(allpairs['energy_reg']['eer']),pct(e['eer']),pct(allpairs['hybrid']['eer']),pct(h['eer'])])
 fam_headers=(['队列','同家族负例',r'能量 $\tilde D_{\mathrm{E-reg}}$：全配对 EER','能量：同家族 EER',r'混合量 $D_{\mathrm{hyb}}$：全配对 EER','混合量：同家族 EER']
              if zh else ['Cohort','Fam. negatives',r'Energy $\tilde D_{\mathrm{E-reg}}$: all-pairs EER','Energy: within-family EER',r'Hybrid $D_{\mathrm{hyb}}$: all-pairs EER','Hybrid: within-family EER'])
 result['family']=table(fam_headers,rows)
 s1=json.loads((ROOT/'extensions/live_validation_20261111/lv_rgb_results.json').read_text())['S1_longitudinal_t21d_and_cross_gateway'];rows=[]
 symbols={'robust_manifold':r'$D_{\mathrm{RM}}$','energy_reg':r'$\tilde D_{\mathrm{E-reg}}$','hybrid':r'$D_{\mathrm{hyb}}$'}
 plans=[('longitudinal_t0_to_t21d_cf_6v6_all14','CF0 → CF21',('robust_manifold','energy_reg','hybrid')),
        ('longitudinal_t0_to_t21d_cf_6v6_heldout4','CF0 → CF21 (heldout4)',('energy_reg','hybrid')),
        ('cross_gateway_same_day_cf21_to_or21_6v6_all14','CF21 → OR21',('robust_manifold','energy_reg','hybrid')),
        ('cross_gateway_and_t21d_cf0_to_or21_6v6_all14','CF0 → OR21',('robust_manifold','energy_reg','hybrid'))]
 for key,label,metrics in plans:
  for metric in metrics:
   x=s1[key][metric]
   rows.append([label,symbols[metric],f"{x['top1_hits']}/{x['n_models']}",f"{x['auc_raw']:.4f}",f"{x['eer_linear_pct']:.2f}%",f"{x['genuine_mean']:.4f} / {x['impostor_mean']:.4f}",f"{x['frozen_frr_pct']:.2f}% / {x['frozen_far_pct']:.2f}%"])
 assert len(rows)==11
 result['s1_core']=table(['注册 → 查询 (6v6)' if zh else 'Enrollment → query (6v6)','指标' if zh else 'Metric','Top-1','AUC','线性 EER' if zh else 'Linear EER','正例 / 冒充均值' if zh else 'Genuine / impostor mean','冻结 B3v3 FRR / FAR' if zh else 'Frozen B3v3 FRR / FAR'],rows)
 data=load('energy_u/results.json')['operating_points'];rows=[]
 for key,label in [('v_reg','V regularized'),('v_reg_self','V self-centered'),('u_e2','U numerator'),('u_reg_signed','U signed ratio'),('u_reg_clipped','U clipped ratio')]:
  clean=[x for x in data if x['scenario']=='E_clean' and x['calibration']=='B3v3' and x['threshold_kind']=='tau_mid' and x['metric']==key][0]
  jitter=[x for x in data if x['scenario'].startswith('E_jitter8_seed') and x['calibration']=='B3v3' and x['threshold_kind']=='tau_mid' and x['metric']==key]
  assert len(jitter)==10
  assert clean['far']==0 and all(x['far']==0 for x in jitter)
  rows.append([label,pct(clean['eer']),pct(clean['frr']),pct(statistics.mean(x['eer'] for x in jitter)),pct(statistics.mean(x['frr'] for x in jitter))])
 result['u_energy']=table(['估计量' if zh else 'Estimator','Clean EER','Clean FRR','Jitter EER','Jitter FRR'],rows)
 data=load('service_audit/overhead.json')['aggregate'];rows=[]
 for key in ['B20x6','E20x6','S1_CF21','S1_OR21','S3_color','S3_word','S4a']:
  r=next(x for x in data if x['cohort']==key and x['role']=='query')
  rows.append([key,int(r['calls_median']),f"{r['input_tokens_median']:,.1f} / {r['output_tokens_median']:,.1f}",f"{r['catalog_scenario_llama33_usd_median']:.4f} / {r['catalog_scenario_gpt4o_usd_median']:.4f}",f"{r['call_latency_p50_ms_median']/1000:.2f}",f"{r['estimated_c8_seconds_median']:.2f}"])
 result['overhead']=table(['查询集' if zh else 'Query workload','Calls','Input / output tokens','USD scenarios L / G','Call p50 (s)','Est. c=8 (s)'],rows)
 return result

def digits(rows):return [re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?',r) for r in rows]
def sync(check=False):
 for lang in ['EN','ZH']:
  paths=[ROOT/'paper'/f'{stem}_{lang}.md' for stem in ['MANUSCRIPT','SUPPLEMENT']]
  texts={p:p.read_text() for p in paths if p.exists()}
  for name,body in tables(lang=='ZH').items():
   pattern=rf'<!-- AUDIT_TABLE_{name} -->[\s\S]*?<!-- /AUDIT_TABLE_{name} -->'
   owners=[p for p,text in texts.items() if re.search(pattern,text)]
   if lang=='EN' and name in ('s1_core','family') and not owners:
    s=texts[ROOT/'paper'/'MANUSCRIPT_EN.md']
    tex_label={'s1_core':'tab:s1_transfer','family':'tab:within_family'}[name]
    m=re.search(rf'\\label\{{{tex_label}\}}[\s\S]*?\\midrule([\s\S]*?)\\bottomrule',s);assert m,(lang,name)
    tex_rows=[r for r in m[1].splitlines() if '&' in r]
    md_rows=body.splitlines()[2:]
    assert digits(tex_rows)==digits(md_rows),(lang,name)
    continue
   assert len(owners)==1,(lang,name,owners)
   owner=owners[0]
   block=f'<!-- AUDIT_TABLE_{name} -->\n{body}\n<!-- /AUDIT_TABLE_{name} -->'
   if check:assert re.search(pattern,texts[owner])[0]==block,(lang,name)
   else:texts[owner]=re.sub(pattern,lambda _:block,texts[owner])
  if not check:
   for p,text in texts.items():p.write_text(text)
 print('Service-audit tables verified.' if check else 'Service-audit tables synchronized.')
if __name__=='__main__':sync('--check' in sys.argv)
