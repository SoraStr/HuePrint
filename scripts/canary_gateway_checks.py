"""Offline S4 rule pass-rate counts and cross-gateway categorical controls; no API calls."""
from pathlib import Path
import sys, json, re, csv
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from hueprint_audit.core import load, group, split, stats, permutation_p, save
from hueprint_audit.experiments import FILES, make_s1
from hueprint_audit.baselines import aggregate_exact_mmd_u, exact_mmd_stats, run_one
OUT=ROOT/'results/diagnostics';OUT.mkdir(exist_ok=True)
LITERAL=re.compile(r'#RRGGBB|R\s*,\s*G\s*,\s*B',re.I)
DIRECTIVE=re.compile(r'(respond\s+with\s+only|reply\s+with\s+only|answer\s+with\s+one\s+(word|number|letter)\s+only|no\s+words,?\s+no\s+explanation|仅回复|仅回答一个|不要包含任何(文字|解释))',re.I)
BARE=re.compile('^\\s*[`\'\\"]?(#[0-9a-fA-F]{6}|\\d{1,3}\\s*,\\s*\\d{1,3}\\s*,\\s*\\d{1,3})[`\'\\".]?\\s*$')

def filter_counts(rows, config):
    cfg=json.loads((ROOT/config).read_text());counts=dict(total=len(rows),input_bypass=0,output_bypass=0,valid_output_unflagged=0,valid_and_unflagged=0)
    for r in rows:
        t=cfg['tasks'][r['task_id']];lg=r['lang'];prompt=cfg['system_prompts'][t['format']][lg]+'\n'+t['prompts'][lg]
        inp=not (LITERAL.search(prompt) or DIRECTIVE.search(prompt));out=not BARE.match(r.get('raw_text') or '');valid=r['parsed']['status']=='valid'
        counts['input_bypass']+=int(inp);counts['output_bypass']+=int(out)
        counts['valid_output_unflagged']+=int(valid and out);counts['valid_and_unflagged']+=int(valid and inp and out)
    return {'counts':counts,'rates':{k:v/len(rows) for k,v in counts.items() if k!='total'}}

def offline_guard(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto', 'subprocess.Popen'):
        raise RuntimeError('Offline-only analysis blocked event: ' + event)

def verify_protected():
    import hashlib
    manifest = json.loads((ROOT / 'results/integrity_manifest.json').read_text())['files']
    for rel, expected in manifest.items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Protected file mutated: ' + rel)

def main():
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,default=OUT);out_dir=ap.parse_args().output.resolve();out_dir.mkdir(parents=True,exist_ok=True)
    verify_protected()
    sys.addaudithook(offline_guard)
    data={k:load(FILES[k]) for k in ['B','E','S1_CF21','S1_OR21','S2','S3_color','S4a','S4b']}
    filters={label:filter_counts(data[key],config) for label,key,config in [('S3a','S3_color','config/prompts.json'),('S4a','S4a','config/prompts.implicit_css.json'),('S4b','S4b','config/prompts.implicit_v5_exact.json')]}
    assert filters['S4b']['counts']['output_bypass']==48 and filters['S4b']['counts']['total']==1920
    save(out_dir/'s4_filter_counts.json',filters);print('S4',filters,flush=True)
    cf0,cf21,or21=make_s1(data)
    plans=[('S1_CF0_CF21_6v6',cf0,cf21),('S1_CF21_OR21_6v6',cf21,or21),('S1_CF0_OR21_6v6',cf0,or21),('S2_cross_provider_6v6',group(data['S2']),group(data['S2'])),('S2_cross_provider_3v3',*split(data['S2']))]
    meta={r['id']:r for r in json.loads((ROOT/'extensions/live_validation_20261111/configs/targets.s2_multiprovider.json').read_text())['targets']}
    results=[];pairs=[]
    for name,a,b in plans:
        ids,cells,null,geo,valid,_=run_one(a,b,999)
        pos=np.eye(len(ids),dtype=bool);neg=~pos
        if name.startswith('S2'):
            pos=np.array([[t!=u and meta[t]['weight_group']==meta[u]['weight_group'] for u in ids] for t in ids]);neg=np.array([[meta[t]['weight_group']!=meta[u]['weight_group'] for u in ids] for t in ids])
        for metric in ['string_mmd_u','string_tv']:
            if metric == 'string_mmd_u':
                obs_exact, obs_stat, p = aggregate_exact_mmd_u(null['string_mmd_u_num'], null['string_mmd_u_den'], list(range(len(cells))))
                s = exact_mmd_stats(obs_exact, obs_stat, pos, neg)
            else:
                joint = null[metric].mean(axis=2); p = permutation_p(joint); obs_stat = joint[:,:,0]; s = stats(obs_stat, pos, neg)
            s.pop('top1')
            result=dict(scenario=name,metric=metric,cells=len(cells),permutations=999,**s,same_model_rejection_rate=float((p[pos]<=.05).mean()),different_model_rejection_rate=float((p[neg]<=.05).mean()))
            results.append(result);print(result,flush=True)
            for i,t in enumerate(ids):
                for j,u in enumerate(ids):
                    if pos[i,j] or neg[i,j]:pairs.append(dict(scenario=name,metric=metric,reference=t,query=u,genuine=bool(pos[i,j]),statistic=float(obs_stat[i,j]),p_value=float(p[i,j])))
    save(out_dir/'cross_gateway_baselines.json',{'results':results,'protocol':'All 20 fixed cells; raw strings retained; independent within-cell 999 permutations; same deterministic seeds as S3. S1: 14 same-label positives and 182 directed negatives. S2: distinct providers with same declared checkpoint positive; different checkpoint negative; diagonal excluded. No threshold selection on S1/S2.'})
    for name,rows in [('cross_gateway_baselines',results),('cross_gateway_pairs',pairs)]:
        with (out_dir/(name+'.csv')).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    verify_protected()
if __name__=='__main__':main()
