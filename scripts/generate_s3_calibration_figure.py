"""Figure 5: frozen offline evidence, vector-only PDF/SVG, no model calls."""
from pathlib import Path
import json
import statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
baseline = json.loads((ROOT/'results/benchmark/baseline_results.json').read_text())['results']
exact_mmd = json.loads((ROOT/'results/diagnostics/exact_mmd_baselines.json').read_text())['results']
calibration = json.loads((ROOT/'results/benchmark/calibration_results.json').read_text())['operating_points']
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.titlesize': 9,
                    'pdf.fonttype': 42, 'svg.fonttype': 'none', 'svg.hashsalt': 'hueprint-s3-calibration',
                    'axes.spines.top': False, 'axes.spines.right': False})
fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.9))
fig.subplots_adjust(left=.08, right=.985, top=.78, bottom=.19, wspace=.38)
data = {'baseline': [], 'calibration': []}
permutation = json.loads((ROOT/'results/benchmark/calibration_results.json').read_text())['energy_permutation_tests']
for metric, color, label in [('string_mmd_u', '#D55E00', 'String MMD'), ('energy_reg', '#0072B2', 'Energy-reg')]:
    source = exact_mmd if metric == 'string_mmd_u' else baseline
    for condition, style in [('clean', '--'), ('jitter8', '-')]:
        values = []
        for n in [6, 10, 20, 30]:
            rows = [r for r in source if r['dataset']=='S3_color' and r['K']==10 and r['n_total_per_cell']==n and r['metric']==metric and r['condition']==condition]
            values.append(100*st.mean(r['eer'] for r in rows))
        axes[0].plot([6,10,20,30], values, style, color=color, marker='o' if condition=='clean' else 's', markersize=4,
                     markerfacecolor='white' if condition=='clean' else color, label=label+(' clean' if condition=='clean' else ' ±8'), zorder=3 if condition=='clean' else 2)
        data['baseline'].append({'metric':metric,'condition':condition,'eer_pct':values})
axes[0].set(xlabel='Total responses per cell (N)', ylabel='Linear EER (%)', xticks=[6,10,20,30], ylim=(-2,55), title='(a) S3, all 10 probes')
axes[0].legend(loc='upper center', bbox_to_anchor=(.5,1.34), ncol=2, fontsize=7, frameon=False, columnspacing=.8)
for i, variant in enumerate(['raw','self_Bcv','permutation']):
    values=[]
    for condition in ['E_clean','E_jitter8']:
        rows=[r for r in calibration if (r['scenario']==condition or r['scenario'].startswith(condition+'_seed')) and r['calibration']=='B3v3' and r['metric']=='energy_reg' and r['variant']==variant and r['threshold_kind']=='tau_mid']
        if variant=='permutation':
            rows=[r for r in permutation if r['scenario']==condition or r['scenario'].startswith(condition+'_seed')]
            values.append(100*st.mean(r['same_model_rejection_rate'] for r in rows))
            assert all(r['different_model_nonrejection_rate']==0 for r in rows)
        else:values.append(100*st.mean(r['frr'] for r in rows))
    x=[j+(i-1)*.24 for j in range(2)]
    axes[1].bar(x,values,.22,color=['#0072B2','#E69F00','#009E73'][i],label=['Raw frozen','Enrollment centered','Energy permutation'][i])
    for x0,y in zip(x,values):axes[1].text(x0,y+1.5,f'{y:.2f}%',ha='center',fontsize=6.5)
    data['calibration'].append({'variant':variant,'frr_pct':values})
axes[1].set(xticks=[0,1],xticklabels=['Clean','±8 RGB jitter'],ylabel='Same-model rejection (%)',ylim=(0,82),title='(b) Held-out E: energy decisions')
axes[1].legend(loc='upper center',bbox_to_anchor=(.5,1.37),fontsize=7,frameon=False,ncol=2,columnspacing=.8)
fig.canvas.draw()
renderer=fig.canvas.get_renderer()
for ax in axes:
    assert not ax.get_legend().get_window_extent(renderer).overlaps(ax.get_window_extent(renderer))
    assert not ax.get_legend().get_window_extent(renderer).overlaps(ax.title.get_window_extent(renderer))
axes[1].text(.98,.96,'FAR = 0.00% for all six bars',transform=axes[1].transAxes,ha='right',va='top',fontsize=7)
for ax in axes:ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
out=ROOT/'figs/fig5_geometry_and_calibration'
fig.savefig(out.with_suffix('.pdf'),metadata={'Creator':'HuePrint offline analysis','CreationDate':None,'ModDate':None})
fig.savefig(out.with_suffix('.svg'),metadata={'Date':None})
out.with_suffix('.svg').write_text('\n'.join(line.rstrip() for line in out.with_suffix('.svg').read_text().splitlines())+'\n')
(ROOT/'results/diagnostics/figure5_data.json').write_text(json.dumps(data,indent=2)+'\n')
print('Wrote figure 5 PDF and SVG.')
