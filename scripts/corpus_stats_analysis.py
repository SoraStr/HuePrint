"""Offline corpus summary, precision-regime, and cluster-bootstrap statistics."""
from pathlib import Path
import sys,json,hashlib,collections,math,itertools
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import analyze as an
from reproduce_all import load_jsonl_clean,perturb_row_rgb
from extensions.live_validation_20261111.lv_analyze import build_cell_map
from matplotlib.colors import CSS4_COLORS
OUT=ROOT/'results/corpus_stats';SEED=20261111
MET=['hex_jsd','voxel_jsd','soft_voxel_jsd','energy_norm','energy_reg','hybrid','robust_manifold']

def load(p):return load_jsonl_clean(p)[0]
def split(rows):return (build_cell_map(rows,rep_filter=lambda n:n%2==1),build_cell_map(rows,rep_filter=lambda n:n%2==0))
def roc(g,i):
 r=an.compute_roc_eer(list(g),list(i));return {'auc':r['auc_raw'],'eer':r['eer_linear_raw']}
def pair(a,b,delta=15):
 d=an.compute_cell_distance(a,b);return {k:d[k] for k in MET}
def matrices(a,b):
 ids=sorted(set(a)&set(b));out={k:np.zeros((len(ids),len(ids))) for k in MET}
 for i,t in enumerate(ids):
  for j,u in enumerate(ids):
   common=sorted(set(a[t])&set(b[u])); ds=[pair(a[t][c],b[u][c]) for c in common]
   if not ds:raise ValueError('No shared probe cells')
   for m in MET:out[m][i,j]=np.mean([d[m] for d in ds])
 return ids,out

def summarize_matrix(mat):return roc(np.diag(mat),mat[~np.eye(len(mat),dtype=bool)])
def weighted_roc(g,i,wg,wi):
 maskg=wg>0;maski=wi>0;g=g[maskg];i=i[maski];wg=wg[maskg];wi=wi[maski]
 wprod=wg[:,None]*wi[None,:]
 auc=np.sum(((g[:,None]<i[None,:])+.5*(g[:,None]==i[None,:]))*wprod)/wprod.sum()
 thresholds=np.unique(np.r_[g,i]);frr=np.r_[1.,(wg[:,None]*(g[:,None]>thresholds)).sum(0)/wg.sum()];far=np.r_[0.,(wi[:,None]*(i[:,None]<=thresholds)).sum(0)/wi.sum()]
 diff=far-frr;k=np.flatnonzero(diff>=0)[0];w=-diff[k-1]/(diff[k]-diff[k-1]);eer=far[k-1]+w*(far[k]-far[k-1])
 return float(auc),float(eer)
def bootstrap(mat,B=2000):
 n=len(mat);off=~np.eye(n,dtype=bool);g=np.diag(mat);i=mat[off];rng=np.random.default_rng(SEED);draw=[];degenerate=0
 for _ in range(B):
  w=rng.multinomial(n,[1/n]*n);wi=(w[:,None]*w[None,:])[off]
  if wi.sum()==0:degenerate+=1;continue
  draw.append(weighted_roc(g,i,w,wi))
 ar=np.array(draw);return {'point':summarize_matrix(mat),'auc_ci95':np.quantile(ar[:,0],[.025,.975]).tolist(),'eer_ci95':np.quantile(ar[:,1],[.025,.975]).tolist(),'requested_resamples':B,'valid_resamples':len(draw),'degenerate_resamples':degenerate,'n_model_clusters':n}
def save(name,obj):
 (OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def snapshot(phase,files):save('checkpoints/'+phase+'.json',{'phase':phase,'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}})

def precision_analysis(rows):
 meta={t['id']:t for t in json.load(open(ROOT/'extensions/live_validation_20261111/configs/targets.s2_multiprovider.json'))['targets']}
 ids,ms=matrices(build_cell_map(rows),build_cell_map(rows));index={t:i for i,t in enumerate(ids)}
 def regime(a,b):
  x,y=meta[a]['quant'],meta[b]['quant']
  if x not in ['fp8','bf16','int4','fp4'] or y not in ['fp8','bf16','int4','fp4']:return 'unspecified_precision'
  if x==y:return 'matched'
  if {x,y}=={'fp8','bf16'}:return 'moderate'
  if (x in ['int4','fp4'])!=(y in ['int4','fp4']):return 'aggressive'
  return 'other'
 pair_rows=[];out={}
 for i,j in itertools.combinations(range(len(ids)),2):
  a,b=ids[i],ids[j]
  if meta[a]['weight_group']==meta[b]['weight_group']:pair_rows.append({'a':a,'b':b,'regime':regime(a,b),'scores':{m:float(v[i,j]) for m,v in ms.items()}})
 for reg in ['matched','moderate','aggressive','unspecified_precision']:
  pairs=[p for p in pair_rows if p['regime']==reg];out[reg]={}
  for m,mat in ms.items():
   pos=[p['scores'][m] for p in pairs];neg=[];hits=[]
   # A regime-specific query has an eligible same-checkpoint reference. Retain
   # all other-checkpoint references, exclude same-checkpoint refs outside regime.
   for q in ids:
    same=[t for t in ids if t!=q and meta[t]['weight_group']==meta[q]['weight_group'] and regime(t,q)==reg]
    if not same:continue
    others=[t for t in ids if meta[t]['weight_group']!=meta[q]['weight_group']]
    candidates=same+others;best=min(candidates,key=lambda t:(mat[index[t],index[q]],t));hits.append(best in same)
    neg.extend(mat[index[t],index[q]] for t in others)
   out[reg][m]={'pairs':len(pos),'queries':len(hits),'mean':float(np.mean(pos)) if pos else None,'sd':float(np.std(pos,ddof=1)) if len(pos)>1 else None,'top1':float(np.mean(hits)) if hits else None,**(roc(pos,neg) if pos and neg else {})}
 # T1b: high-precision reference; compare same-checkpoint high->high controls
 # with high->low positives. All are cross-provider full-sample comparisons.
 detection={}
 for m,mat in ms.items():
  clean=[];low=[];records=[]
  for a in ids:
   if meta[a]['quant'] not in ['bf16','fp8']:continue
   for b in ids:
    if a==b or meta[a]['weight_group']!=meta[b]['weight_group']:continue
    if meta[b]['quant'] not in ['bf16','fp8','int4','fp4']:continue
    score=float(mat[index[a],index[b]]);is_low=meta[b]['quant'] in ['int4','fp4']
    (low if is_low else clean).append(score);records.append({'reference':a,'query':b,'low_bit':is_low,'score':score})
  detection[m]={'control_pairs':len(clean),'low_bit_pairs':len(low),'mean_control':float(np.mean(clean)),'mean_low_bit':float(np.mean(low)),**roc(clean,low),'pair_records':records}
 return {'metadata_source':'saved target config; provider identity in response logs; not attested precision','metadata':{k:{f:v[f] for f in ['weight_group','quant','pinned_provider']} for k,v in meta.items()},'pairs':pair_rows,'regimes':out,'T1b':detection,'limitations':'Provider/hardware/precision confounded; lpu and official do not specify numerical precision; T1b is descriptive pooled detection, not controlled causal attribution.'}

def sensitivity(rows):
 a,b=split(rows);ids=sorted(a);off=~np.eye(len(ids),dtype=bool);out=[]
 # Cache geometry components and RGB histograms independently of hyperparameters.
 cache={}
 for t in ids:
  for u in ids:
   vals=[]
   for c in sorted(set(a[t])&set(b[u])):
    x,y=a[t][c],b[u][c];X=x['rgb_arr'];Y=y['rgb_arr']
    ab=np.linalg.norm(X[:,None]-Y,axis=-1).mean();aa=np.linalg.norm(X[:,None]-X,axis=-1).mean();bb=np.linalg.norm(Y[:,None]-Y,axis=-1).mean()
    soft={}
    for w in [24,32,48,64]:
     hx={};hy={}
     for v in X/an.RGB_SCALE:an.add_soft_voxel(hx,v,bin_width=w)
     for v in Y/an.RGB_SCALE:an.add_soft_voxel(hy,v,bin_width=w)
     soft[w]=an.jsd_base2(hx,hy)
    vals.append((ab,max(0,2*ab-aa-bb),soft,pair(x,y)))
   cache[t,u]=vals
 for delta in [2,5,10,15,25,50]:
  for w in [24,32,48,64]:
   for alpha in [.4,.5,.6]:
    mat=np.array([[np.mean([alpha*v[2][w]+(1-alpha)*v[1]/(2*(v[0]+delta)) for v in cache[t,u]]) for u in ids] for t in ids])
    out.append({'delta':delta,'w':w,'soft_weight':alpha,**summarize_matrix(mat)})
 energy=[]
 for delta in [2,5,10,15,25,50]:
  mat=np.array([[np.mean([v[1]/(2*(v[0]+delta)) for v in cache[t,u]]) for u in ids] for t in ids]);energy.append({'delta':delta,**summarize_matrix(mat)})
 weights=[];base=np.array([.35,.25,.25,.15]);names=['voxel_jsd','hex_jsd','energy_norm','side_jsd']
 # side_jsd is computed separately because it is absent from MET.
 for index in range(4):
  for shift in [-.10,.10]:
   ww=base.copy();ww[index]+=shift;other=np.arange(4)!=index;ww[other]*=(1-ww[index])/(1-base[index]);mat=np.zeros((len(ids),len(ids)))
   for i,t in enumerate(ids):
    for j,u in enumerate(ids):
     ds=[an.compute_cell_distance(a[t][c],b[u][c]) for c in sorted(set(a[t])&set(b[u]))]
     mat[i,j]=np.mean([sum(ww[k]*v[n] for k,n in enumerate(names)) for v in ds])
   weights.append({'varied':names[index],'shift':shift,'weights':ww.tolist(),**summarize_matrix(mat)})
 return {'energy':energy,'robust_grid':out,'hybrid_weights':weights}

def priors(rows,fmap):
 named={v.upper() for v in CSS4_COLORS.values()};groups=collections.defaultdict(list)
 for r in rows:
  if r['parsed']['status']!='valid':continue
  family=fmap[r['target_id']];condition='unanchored' if r['condition']=='random' else ('preference' if r['condition']=='favorite' else 'semantic')
  groups[family,condition].append(r['parsed']['rgb'])
 out=[]
 for (family,condition),rgb in sorted(groups.items()):
  x=np.array(rgb);n=len(x);codes=['#%02X%02X%02X'%tuple(v) for v in rgb]
  out.append({'family':family,'probe_class':condition,'n':n,'named_count':sum(c in named for c in codes),'grayscale_count':int(np.sum(np.ptp(x,axis=1)==0)),'corner_count':int(np.sum(np.all((x==0)|(x==255),axis=1))),'nibble_count':int(np.sum(np.all(x%17==0,axis=1))),'channel_entropy_bits':[an.shannon_entropy_bits(dict(collections.Counter(x[:,d]))) for d in range(3)],'modal_fraction':max(collections.Counter(codes).values())/n})
 return out

def jitter(rows):
 a,b=split(rows);ids=sorted(a);baseids,base=matrices(a,b);out=[];eps=1e-12
 def psi(t):
  if t>=1:return 1.
  return .5*math.log2(2/(2-t))+.5*(1-t)*math.log2(2*(1-t)/(2-t))+t/2
 for radius in [0,1,2,4,8,12,15]:
  lower=[]
  for t in ids:
   for c in sorted(set(a[t])&set(b[t])):
    X=np.rint(a[t][c]['rgb_arr']/an.RGB_SCALE).astype(int);Y=np.rint(b[t][c]['rgb_arr']/an.RGB_SCALE).astype(int);support=np.unique(X,axis=0);esc=[]
    for q in Y:
     stay=0.
     for ref in support:
      ways=1
      for d in range(3):
       lo,hi=-radius,radius
       if ref[d]==0:ways*=max(0,min(hi,-q[d])-lo+1)
       elif ref[d]==255:ways*=max(0,hi-max(lo,255-q[d])+1)
       else:ways*=int(lo<=ref[d]-q[d]<=hi)
      stay+=ways/(2*radius+1)**3
     esc.append(max(0.,1-stay))
    lower.append(psi(float(np.mean(esc))))
  trials=[]
  for seed in range(SEED,SEED+10):
   rng=np.random.default_rng(seed);pert=[perturb_row_rgb(r,'uniform_jitter',radius,rng) if r['rep']%2==0 else r for r in rows];_,qb=split(pert);_,mat=matrices(a,qb)
   eg=[];soft_delta=[];self_soft=[]
   for t in ids:
    for c in sorted(set(b[t])&set(qb[t])):
     d0=pair(a[t][c],b[t][c]);d1=pair(a[t][c],qb[t][c]);eg.append(abs(d1['energy_reg']-d0['energy_reg']));soft_delta.append(abs(d1['soft_voxel_jsd']-d0['soft_voxel_jsd']));self_soft.append(an.jsd_base2(b[t][c]['soft_voxel_counts'],qb[t][c]['soft_voxel_counts']))
   trials.append({'metrics':{m:summarize_matrix(v) for m,v in mat.items()},'hex_genuine_mean':float(np.mean(np.diag(mat['hex_jsd']))),'energy_score_change':float(np.mean(eg)),'soft_score_change':float(np.mean(soft_delta)),'soft_self_jsd':float(np.mean(self_soft))})
  out.append({'a':radius,'expected_hex_lower':float(np.mean(lower)),'energy_bound':min(1,200*np.sqrt(3)*radius/(255*15)),'soft_self_bound':min(1,3*radius/48),'mean':{k:float(np.mean([t[k] for t in trials])) for k in ['hex_genuine_mean','energy_score_change','soft_score_change','soft_self_jsd']},'metrics':{m:{k:float(np.mean([t['metrics'][m][k] for t in trials])) for k in ['auc','eer']} for m in MET},'seeds':list(range(SEED,SEED+10))})
  print('jitter',len(rows),radius,flush=True)
 return out

def offline_guard(event,args):
 if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','socket.sendto','subprocess.Popen'):
  raise RuntimeError('Offline-only analysis blocked event: '+event)
def verify_protected():
 manifest=json.loads((ROOT/'results/integrity_manifest.json').read_text())['files']
 for rel,exp in manifest.items():
  if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=exp:raise RuntimeError('Protected file mutated: '+rel)

def main():
 import argparse
 global OUT
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,default=OUT);OUT=ap.parse_args().output.resolve()
 if (OUT/'analysis.json').resolve()==(ROOT/'results/corpus_stats/analysis.json').resolve() and (OUT/'analysis.json').exists():
  ap.error('Refusing to overwrite protected results/corpus_stats/analysis.json; pass a fresh --output directory')
 (OUT/'checkpoints').mkdir(parents=True,exist_ok=True)
 verify_protected()
 sys.addaudithook(offline_guard)
 B=load('data/exp_40u15r.jsonl');E=load('data/exp_heldout_confirm.jsonl');C=load('data/exp_paraphrase.jsonl');A=load('data/census_40models.jsonl')
 ext='extensions/live_validation_20261111/data/';S2=load(ext+'s2_multiprovider.jsonl');S3=load(ext+'s3a_hueprint_locked64_n30.jsonl')
 result={'protocol':an.ANALYSIS_PROTOCOL,'seed':SEED,'bootstrap_method':'Model-cluster multinomial weights, all ordered cross-identity negatives weighted by product; identical identities excluded; degenerate one-identity draws omitted and counted; percentile intervals conditional on observed model pool.','precision':precision_analysis(S2)}
 print('precision complete',flush=True)
 result['sensitivity']={k:sensitivity(v) for k,v in [('B',B),('E',E)]};print('sensitivity complete',flush=True)
 scores={}
 for name,rows in [('B',B),('E',E),('C_P1',[r for r in C if r['task_id'].startswith('p1_')]),('C_P2',[r for r in C if r['task_id'].startswith('p2_')])]:
  ids,mm=matrices(*split(rows));scores[name]={'ids':ids,'matrices':{k:v.tolist() for k,v in mm.items()}}
 cf=load(ext+'s1a_cf_t21d.jsonl');orr=load(ext+'s1b_or_crossgateway.jsonl');cfg=json.load(open(ROOT/'extensions/live_validation_20261111/configs/targets.s1_or_crossgateway.json'))['targets'];mapping={t['id']:t['paired_cf_id'] for t in cfg};ids14=sorted(set(r['target_id'] for r in cf));held=sorted(set(ids14)-set(r['target_id'] for r in B))
 enroll=[r for r in B+E if r['target_id'] in ids14 and r['lang'] in ['en','zh'] and r['rep']<=6]
 for name,rows,mp in [('S1_CF21',cf,None),('S1_OR21',orr,mapping)]:
  aa=build_cell_map(enroll,min_valid=2);bb=build_cell_map(rows,target_map=mp,min_valid=2);ids,mm=matrices(aa,bb);scores[name]={'ids':ids,'matrices':{k:v.tolist() for k,v in mm.items()}}
  idx=[ids.index(t) for t in held];scores[name+'_heldout4']={'ids':held,'matrices':{k:v[np.ix_(idx,idx)].tolist() for k,v in mm.items()}}
 result['bootstrap']={name:{m:bootstrap(np.array(d['matrices'][m])) for m in ['energy_reg','hybrid','robust_manifold']} for name,d in scores.items() if name not in ['S1_CF21','S1_OR21']}
 result['scores']=scores;print('bootstrap complete',flush=True)
 fmap={k:v['family'] for k,v in json.load(open(ROOT/'config/family_map.json'))['families'].items()}
 def s3fam(t):
  for sub,f in [('claude','Anthropic'),('gpt','OpenAI'),('gemini','Google'),('llama','Meta'),('qwen','Qwen'),('deepseek','DeepSeek'),('mistral','Mistral'),('nemotron','NVIDIA')]:
   if sub in t:return f
  raise ValueError(t)
 result['priors']={'A':priors(A,fmap),'S3':priors(S3,{r['target_id']:s3fam(r['target_id']) for r in S3}),'named_palette':{'names':len(CSS4_COLORS),'unique_rgb':len(set(CSS4_COLORS.values())),'source':'matplotlib.colors.CSS4_COLORS; includes rebeccapurple; aliases collapse to same RGB'},'tokenization':'Raw cloud logs contain output text and usage counts, not per-token segmentation. No BPE mechanism or alignment causality is inferred.'}
 result['jitter']={k:jitter(v) for k,v in [('B',B),('E',E)]}
 manifest_files=json.load(open(ROOT/'results/integrity_manifest.json'))['files']
 result['source_hashes']={p:h for p,h in manifest_files.items() if p.endswith('.jsonl')}
 save('analysis.json',result)
 save('checkpoints/phase1.json',{'phase':'phase1','sha256':{p.name if not p.is_relative_to(ROOT) else str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'analysis.json',Path(__file__).resolve()]}})
 verify_protected()
 print('phase1 complete',flush=True)
if __name__=='__main__':main()
