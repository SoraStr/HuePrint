"""Four offline review figures; vector PDF/SVG with embedded TrueType fonts."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from reproduce_all import load_jsonl_clean
R=json.load(open(ROOT/'results/corpus_stats/analysis.json'));M=json.load(open(ROOT/'data/reproduce_all_rgb_summary.json'))
OUT=ROOT/'figs';OUT.mkdir(exist_ok=True)
AUDIT=ROOT/'results/diagnostics';AUDIT.mkdir(parents=True,exist_ok=True)
SELECTED={3} if '--all' not in sys.argv else {2,3,4}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':9,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'hueprint-figures','axes.spines.top':False,'axes.spines.right':False})
colors=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00'];data={};validation={}
def save(fig,name):
 if int(name[3]) not in SELECTED:
  plt.close(fig);return
 fig.savefig(OUT/(name+'.pdf'),metadata={'Creator':'HuePrint offline figures','CreationDate':None});fig.savefig(OUT/(name+'.svg'),metadata={'Date':None});svg=OUT/(name+'.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
 plt.close(fig)
# Matched response rows. A fixed endpoint per family is selected by id order.
h=load_jsonl_clean('extensions/live_validation_20261111/data/s3a_hueprint_locked64_n30.jsonl')[0];b=load_jsonl_clean('extensions/live_validation_20261111/data/s3b_bruckner_locked64_n30.jsonl')[0]
ids=sorted(set(x['target_id'] for x in h));selected=[next(t for t in ids if sub in t) for sub in ['claude','gpt','gemini','llama','qwen']]
fig, axes = plt.subplots(1, 3, figsize=(7.16, 3.2),
                         gridspec_kw={'width_ratios': [1, 1, 1.35]})
fig.subplots_adjust(left=.09, right=.925, bottom=.33, top=.78, wspace=.58)
a, blue, c = axes
worddata = {}; rgbdata = {}
families = ['Anthropic', 'OpenAI', 'Google', 'Meta', 'Qwen']
for tid, marker, co, family in zip(selected, ['o', 's', '^', 'D', 'v'], colors, families):
    rgb = np.array([r['parsed']['rgb'] for r in h if r['target_id']==tid
                    and r['task_id']=='hex_random' and r['parsed']['status']=='valid'])
    u, counts = np.unique(rgb, axis=0, return_counts=True)
    rgbdata[tid] = {'rgb': u.tolist(), 'count': counts.tolist()}
    for ax, channel in [(a, 0), (blue, 2)]:
        ax.scatter(u[:, channel]*100/255, u[:, 1]*100/255,
                   s=14+counts*8, c=u/255, marker=marker,
                   edgecolors=co, linewidth=.7, label=family)
    words = [r['parsed']['canonical_hex'] for r in b if r['target_id']==tid
             and r['task_id']=='brk_rand_color' and r['parsed']['status']=='valid']
    worddata[tid] = {w: words.count(w)/len(words) for w in sorted(set(words))}
for ax, channel in [(a, 'R'), (blue, 'B')]:
    ax.set(xlabel=channel+' (RGB100)', xlim=(-5, 105), ylim=(-5, 105),
           xticks=[0, 50, 100], yticks=[0, 50, 100])
a.set(ylabel='G (RGB100)', title='(a) R–G projection')
blue.set(title='B–G projection')
handles, labels = a.get_legend_handles_labels()
legend = fig.legend(handles, labels, ncol=5, loc='upper center',
                    bbox_to_anchor=(.5, 1.0), fontsize=8, frameon=False,
                    handletextpad=.4, columnspacing=1.2)
words = sorted(set(w for d in worddata.values() for w in d))
arr = np.array([[worddata[t].get(w, 0) for w in words] for t in selected])
im = c.pcolormesh(np.arange(arr.shape[1]+1)-.5,
                  np.arange(arr.shape[0]+1)-.5, arr,
                  vmin=0, vmax=1, cmap='viridis', rasterized=False)
c.set(ylim=(arr.shape[0]-.5, -.5), xticks=range(len(words)), xticklabels=words,
      yticks=range(len(selected)), yticklabels=families, title='(b) Word probabilities')
c.tick_params(axis='x', labelrotation=75, labelsize=8)
c.tick_params(axis='y', labelsize=8)
plt.setp(c.get_xticklabels(), ha='right', rotation_mode='anchor')
cb = fig.colorbar(im, ax=c, shrink=.8, fraction=.04, pad=.04)
cb.solids.set_rasterized(False)
cb.set_ticks([0, .5, 1])
# The legend must remain entirely outside both scatter data rectangles.
fig.canvas.draw(); renderer=fig.canvas.get_renderer()
legend_box = legend.get_window_extent(renderer)
assert all(not legend_box.overlaps(ax.get_window_extent(renderer)) for ax in [a, blue])
data['fig2'] = {'selected': selected, 'rgb_probe': 'hex_random',
                'word_probe': 'brk_rand_color', 'rgb': rgbdata,
                'word_probability': worddata,
                'projections': [['R', 'G'], ['B', 'G']],
                'family_legend_outside_scatter': True}
save(fig, 'fig2_rgb_geometry_vs_words')
fig=plt.figure(figsize=(7.16,4.2),layout='constrained');gs=fig.add_gridspec(2,2);axs=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[1,:])];x=[v['a'] for v in R['jitter']['B']]
for cohort,style,co in [('B','-',colors[0]),('E','--',colors[1])]:
 j=R['jitter'][cohort];axs[0].plot(x,[v['mean']['hex_genuine_mean'] for v in j],style+'o',color=co,ms=2,label=cohort+' empirical');axs[0].plot(x,[v['expected_hex_lower'] for v in j],style,color=co,alpha=.5,label=cohort+' lower bound')
j=R['jitter']['B']
empirical=[]
for field,marker,co,label in [('energy_score_change','o',colors[0],'Energy score change'),
                             ('soft_self_jsd','s',colors[2],'Soft: query vs. perturbed')]:
    values=np.asarray([v['mean'][field] for v in j])
    assert len(x)==len(values) and x[0]==0 and x[-1]==15 and np.isfinite(values).all()
    line,=axs[1].plot(x,values,'-'+marker,lw=1.7,ms=3.5,mfc='white',mew=.8,
                     zorder=5,color=co,label=label)
    empirical.append({'source_field':field,'label':label,'x':line.get_xdata().tolist(),
                      'y':line.get_ydata().tolist(),'linestyle':line.get_linestyle()})
axs[1].plot(x,[v['energy_bound'] for v in j],'--',lw=1.1,color=colors[0],label='Energy upper bound')
axs[1].plot(x,[v['soft_self_bound'] for v in j],'--',lw=1.1,color=colors[2],label='Soft self upper bound')
curve_styles = []
for m, co, label in [('hex_jsd', colors[1], 'Exact'),
                      ('energy_reg', colors[0], 'Energy'),
                      ('robust_manifold', colors[2], r'$D_{\mathrm{RM}}$')]:
    for cohort in ['B', 'E']:
        # Keep the measured ordinates unchanged. Thin, offset dashes and
        # alternating open markers expose coincident curves without jittering y.
        if m == 'hex_jsd':
            style = dict(lw=1.5, ls='-' if cohort=='B' else '--')
        elif m == 'energy_reg':
            style = dict(lw=2.8, ls='-' if cohort=='B' else (0, (6, 3)),
                         marker='o' if cohort=='B' else 's', ms=4,
                         markevery=[0, 2, 4, 6], mfc='white', mew=.8)
        else:
            style = dict(lw=1.3, ls=(1, (3, 3)) if cohort=='B' else (3, (2, 4)),
                         marker='^' if cohort=='B' else 'x', ms=4,
                         markevery=[1, 3, 5], mfc='white', mew=.8)
        axs[2].plot(x, [100*v['metrics'][m]['eer'] for v in R['jitter'][cohort]],
                    color=co, label=label+' '+cohort, **style)
        curve_styles.append({'metric': m, 'cohort': cohort, 'style': style})
for ax, title, ylabel in zip(axs,
        ['(a) Support escape', '(b) Perturbation bounds', '(c) Linear EER'],
        ['Mean exact JSD', 'Mean change / bound', 'EER (%)']):
    ax.set(xlabel='Channel jitter radius a', ylabel=ylabel, title=title,
           xticks=[0, 4, 8, 12, 15])
    ax.grid(alpha=.15)
    if ax == axs[2]:
        ax.legend(fontsize=7.5, frameon=False, loc='upper center', ncol=6,
                  handlelength=1.8, columnspacing=0.9, handletextpad=0.35, borderaxespad=0.25)
    else:
        ax.legend(fontsize=8, frameon=True, framealpha=.95, edgecolor='none',
                  loc='upper left' if ax == axs[1] else 'lower right', ncol=1)
axs[1].legend(loc='upper left', ncol=1, fontsize=6.5, labelspacing=.2,
              frameon=False, handlelength=1.8, borderaxespad=.4, borderpad=.2)
axs[1].set_xlim(-.5,15.5)
axs[1].set_ylim(-.025,1.05)
assert all(len(line.get_xdata())==7 and line.get_xdata()[-1]==15 for line in axs[1].lines)
axs[2].set_ylim(-3, 58)
# Compact inset placed cleanly in the curve-free corridor y in [14, 39], x >= 10.8.
ins=axs[2].inset_axes([.72, .38, .24, .27])
for cohort, co, marker in [('B', colors[0], 'o'), ('E', colors[1], 's')]:
    ins.plot([v['delta'] for v in R['sensitivity'][cohort]['energy']],
             [100*v['eer'] for v in R['sensitivity'][cohort]['energy']],
             color=co, lw=1, marker=marker, ms=2, label=cohort)
ins.set(xlabel=r'$\delta_0$', ylabel='EER (%)', xticks=[2, 25, 50], yticks=[0, 10])
ins.xaxis.label.set_size(7); ins.yaxis.label.set_size(7)
ins.xaxis.labelpad=0; ins.yaxis.labelpad=1
ins.xaxis.set_label_coords(1.07, -.10)
ins.tick_params(labelsize=7, pad=1)
ins.legend(fontsize=7, loc='center right', ncol=2, frameon=False,
           handlelength=1, columnspacing=.7, borderaxespad=.2)
fig.canvas.draw();renderer=fig.canvas.get_renderer()
legend_bbox=axs[1].get_legend().get_window_extent(renderer)
axes_bbox=axs[1].get_window_extent(renderer)
assert axes_bbox.contains(*legend_bbox.p0) and axes_bbox.contains(*legend_bbox.p1)
title_y=[axis.title.get_window_extent(renderer).y0 for axis in axs[:2]]
assert abs(title_y[0]-title_y[1])<.01
# Check each legend label against the curves in both axs[1] and axs[2].
legend_data=legend_bbox.transformed(axs[1].transData.inverted())
label_clearances=[]
for label in axs[1].get_legend().get_texts():
    label_box=label.get_window_extent(renderer).expanded(1.02,1.08)
    for line in axs[1].lines:
        dense_x=np.linspace(min(line.get_xdata()),max(line.get_xdata()),1001)
        dense_y=np.interp(dense_x,line.get_xdata(),line.get_ydata())
        points=axs[1].transData.transform(np.column_stack((dense_x,dense_y)))
        assert not any(label_box.contains(*point) for point in points)
    label_clearances.append(label.get_text())
legend2_bbox=axs[2].get_legend().get_window_extent(renderer).expanded(1.01,1.05)
ins_bbox=ins.get_tightbbox(renderer)
for line in axs[2].lines:
    dense_x=np.linspace(min(line.get_xdata()),max(line.get_xdata()),1001)
    dense_y=np.interp(dense_x,line.get_xdata(),line.get_ydata())
    points=axs[2].transData.transform(np.column_stack((dense_x,dense_y)))
    assert not any(legend2_bbox.contains(*point) for point in points), 'Fig 3(c) legend overlaps curve!'
    assert not any(ins_bbox.contains(*point) for point in points), 'Fig 3(c) inset overlaps curve!'
validation['fig3b']={'empirical_curves':empirical,'xlim':list(axs[1].get_xlim()),
                    'ylim':list(axs[1].get_ylim()),'legend_inside_upper_left':True,
                    'legend_labels_clear_of_curves':True,'legend_bounds_data':legend_data.bounds,
                    'checked_legend_labels':label_clearances,
                    'fig3c_legend_and_inset_clear_of_curves':True,
                    'subplot_title_y_pixels':title_y,'subplot_titles_aligned':True,
                    'data_source':'results/corpus_stats/analysis.json:jitter.B',
                    'ordinates_unchanged':True}
save(fig, 'fig3_stability_bounds')
fig,axes=plt.subplots(1,2,figsize=(7.16,3.2),layout='constrained');grid=M['dataset_B_40u15r']['grid_2d_n_by_k']['grid_hybrid'];ns=list(grid);ks=list(grid[ns[0]]);vals=np.array([[grid[n][k]['tie_stable_12dp_linear_eer_pct'] for k in ks] for n in ns]);im=axes[0].pcolormesh(np.arange(vals.shape[1]+1)-.5,np.arange(vals.shape[0]+1)-.5,vals,cmap='viridis_r',rasterized=False);axes[0].set_ylim(vals.shape[0]-.5,-.5);axes[0].set(xticks=range(len(ks)),xticklabels=ks,yticks=range(len(ns)),yticklabels=ns,xlabel='Probe cells k',ylabel='Repeats n',title=r'(a) $D_{\mathrm{hyb}}$ linear EER (%)');cb=fig.colorbar(im,ax=axes[0],shrink=.8);cb.solids.set_rasterized(False)
for i in range(len(ns)):
 for j in range(len(ks)):axes[0].text(j,i,f'{vals[i,j]:.1f}',ha='center',va='center',fontsize=8,color='white' if vals[i,j]>12 else '#222')
C_COMP=json.load(open(ROOT/'results/benchmark/comparisons.json'))
C_CAL=json.load(open(ROOT/'results/benchmark/calibration_results.json'))['operating_points']
rng=np.random.default_rng(20261111)
labels=['B\n(3v3)','E\n(3v3)','CF0→CF21\n(6v6)','CF0→OR21\n(6v6)']
sets=['B20x6','E','S1_CF0_CF21_6v6','S1_CF0_OR21_6v6']
scoredata={};all_pts=[]
for k,name in enumerate(sets):
 mat=np.array(C_COMP[name]['matrices']['energy_reg']);g=mat.diagonal();imp=mat[~np.eye(len(mat),dtype=bool)]
 scoredata[name]={'genuine':g.tolist(),'impostor':imp.tolist()}
 for shift,v,co in [(-.15,g,colors[0]),(.15,imp,colors[1])]:
  axes[1].boxplot(v,positions=[k+shift],widths=.23,showfliers=False,patch_artist=True,boxprops={'facecolor':co,'alpha':.45},medianprops={'color':'black'})
  xs_jit=k+shift+rng.uniform(-.06,.06,len(v))
  axes[1].scatter(xs_jit,v,s=2,color=co,alpha=.4)
  all_pts.extend(zip(xs_jit.tolist(),v.tolist()))
tau_b3=next(r['threshold'] for r in C_CAL if r['scenario']=='B3v3_development' and r['metric']=='energy_reg' and r['variant']=='raw' and r['threshold_kind']=='tau_mid')
tau_b6=next(r['threshold'] for r in C_CAL if r['scenario']=='B6v6_development' and r['metric']=='energy_reg' and r['variant']=='raw' and r['threshold_kind']=='tau_mid')
axes[1].axhline(tau_b3,color='black',ls='--',lw=1.0,label=r'B3v3 frozen $\tau$ (0.148)')
axes[1].plot([1.58,3.42],[tau_b6,tau_b6],color='#444444',ls=':',lw=1.3,label=r'B6v6 matched $\tau$ (0.113)')
ymax=max(y for _,y in all_pts)
axes[1].set_ylim(-.02,max(.68,ymax*1.26))
axes[1].set(xticks=range(4),xticklabels=labels,ylabel='Regularized energy',title='(b) Genuine (blue) / impostor (orange)')
axes[1].tick_params(axis='x',labelsize=7.5)
leg4=axes[1].legend(fontsize=6.9,loc='upper left',ncol=2,frameon=False,columnspacing=.5,handlelength=1.4,handletextpad=.35,borderaxespad=.2)
fig.canvas.draw();renderer4=fig.canvas.get_renderer()
leg4_bbox=leg4.get_window_extent(renderer4)
ax4_bbox=axes[1].get_window_extent(renderer4)
pts4_px=axes[1].transData.transform(np.array(all_pts))
assert ax4_bbox.x0<=leg4_bbox.x0 and leg4_bbox.x1<=ax4_bbox.x1+4,'Fig 4(b) legend overflows axes!'
assert not any(leg4_bbox.contains(*pt) for pt in pts4_px),'Fig 4(b) legend overlaps scatter points!'
data['fig4']={'grid':vals.tolist(),'scores':scoredata,'threshold_b3v3':tau_b3,'threshold_b6v6':tau_b6,'grid_metric':'hybrid','cohorts':sets}
save(fig,'fig4_budget_and_drift')
data['fig3']={'curve_styles':curve_styles,'sensitivity_inset':{'x_label':'delta_0','y_label':'EER (%)','cohorts':['B','E']},'jitter':R['jitter'],'sensitivity':{d:R['sensitivity'][d]['energy'] for d in ['B','E']}}
(AUDIT/'figures_2_4_data.json').write_text(json.dumps(data,indent=2)+'\n')
for n in sorted(SELECTED & {3}):
 name={3:'fig3_stability_bounds'}[n]
 validation['fig'+str(n)+'_files']={suffix:hashlib.sha256((OUT/(name+suffix)).read_bytes()).hexdigest() for suffix in ('.pdf','.svg')}
(AUDIT/'figure_validation.json').write_text(json.dumps(validation,indent=2)+'\n')
print('Selected vector figures generated:', sorted(SELECTED))
