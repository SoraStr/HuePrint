#!/usr/bin/env python3
"""Vector service architecture and offline routing figures from frozen evidence."""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'figs'
AUDIT = ROOT / 'results/diagnostics'
SOURCE = ROOT / 'results/service_audit/routing.json'
PERM_SOURCE = ROOT / 'results/protocol_audit/routing_permutation.json'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8,
                     'axes.titlesize': 9, 'axes.labelsize': 8,
                     'xtick.labelsize': 8, 'ytick.labelsize': 8,
                     'pdf.fonttype': 42, 'ps.fonttype': 42,
                     'svg.fonttype': 'none', 'svg.hashsalt': 'hueprint-service-20261113',
                     'axes.spines.top': False, 'axes.spines.right': False})
OUT.mkdir(exist_ok=True)
AUDIT.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_figure(fig, name):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    texts = []
    for obj in fig.findobj(match=matplotlib.text.Text):
        if not obj.get_visible() or not obj.get_text():
            continue
        bbox = obj.get_window_extent(renderer)
        # Matplotlib keeps unused tick labels at zero size; skip only empty extents.
        if bbox.width == 0 or bbox.height == 0:
            continue
        assert obj.get_fontsize() >= 8, (name, obj.get_text(), obj.get_fontsize())
        assert bounds.x0 - .5 <= bbox.x0 and bbox.x1 <= bounds.x1 + .5, (name, obj.get_text(), 'horizontal clipping')
        assert bounds.y0 - .5 <= bbox.y0 and bbox.y1 <= bounds.y1 + .5, (name, obj.get_text(), 'vertical clipping')
        texts.append({'text': obj.get_text(), 'font_size': obj.get_fontsize(),
                      'pixel_bounds': [float(v) for v in bbox.extents]})
    pdf = OUT / (name + '.pdf')
    svg = OUT / (name + '.svg')
    fig.savefig(pdf, metadata={'Creator': 'HuePrint offline service audit', 'CreationDate': None, 'ModDate': None})
    fig.savefig(svg, metadata={'Date': None})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    info = {'size_inches': list(map(float, fig.get_size_inches())), 'minimum_font_pt': min(t['font_size'] for t in texts),
            'all_text_inside_canvas': True, 'texts': texts,
            'outputs': {str(p.relative_to(ROOT)): sha(p) for p in (pdf, svg)}}
    plt.close(fig)
    return info


def service_figure():
    fig = plt.figure(figsize=(7.16, 2.38))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    boxes = {}
    texts = []
    # Subtle lane containers separating online monitoring from offline enrollment.
    ax.add_patch(FancyBboxPatch((.008, .545), .984, .420, boxstyle='round,pad=0.004,rounding_size=0.015',
                                facecolor='#f9fbfd', edgecolor='#d0dce5', linewidth=.8, linestyle='--'))
    ax.text(.020, .930, 'Online canary audit (black-box text only)', ha='left', va='center',
            fontsize=8, weight='bold', color='#1f4e79')
    ax.add_patch(FancyBboxPatch((.008, .155), .515, .345, boxstyle='round,pad=0.004,rounding_size=0.015',
                                facecolor='#f4f8fb', edgecolor='#b7d0e2', linewidth=.8, linestyle='--'))
    ax.text(.020, .465, 'Offline enrollment & contract', ha='left', va='center',
            fontsize=8, weight='bold', color='#005a8d')

    def box(key, x, y, w, h, label, color='#edf4f8', edge='#0072B2', lw=.9):
        patch = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.008,rounding_size=0.012',
                              facecolor=color, edgecolor=edge, linewidth=lw)
        ax.add_patch(patch)
        text = ax.text(x+w/2, y+h/2, label, ha='center', va='center', fontsize=8)
        boxes[key] = (x, y, w, h)
        texts.append((patch, text))

    def arrow(start, end, color='#4C5966', **kw):
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>', mutation_scale=9,
                                    color=color, linewidth=.95, **kw))

    # Top row: online canary path -> parsing -> geometric score -> decision.
    box('monitor',   .020, .605, .158, .250, 'Caller monitor\nRGB / CSS probes', '#f4f5f6', '#617183')
    box('broker',    .206, .605, .156, .250, 'Cloud broker\nRouting / caching', '#f4f5f6', '#617183')
    box('parser',    .390, .605, .168, .250, 'Parse & scale\n#RRGGBB → RGB', '#edf7f4', '#009E73')
    box('score',     .588, .605, .182, .250, 'Distribution score\nEnergy / hybrid vs. τ', '#e6f0f8', '#0072B2', lw=1.2)
    box('decision',  .800, .605, .180, .250, 'Accept / investigate\n2-stage check & log', '#eef5ec', '#35774C')
    for start, end in [((.186, .730), (.198, .730)), ((.370, .730), (.382, .730)),
                       ((.566, .730), (.580, .730)), ((.778, .730), (.792, .730))]:
        arrow(start, end)
    # Tiny RGB color dots inside parser box corner as a visual anchor for HuePrint.
    for dx, rgb_c in [(.016, '#E63946'), (.030, '#2A9D8F'), (.044, '#3A86FF')]:
        ax.plot(.390 + dx, .825, 'o', markersize=3.2, color=rgb_c, markeredgecolor='none')

    # Bottom row: offline reference enrollment -> converges up into score; authorized refresh closes loop.
    box('reference', .020, .200, .205, .210, 'Trusted reference\nPinned checkpoint M*', '#edf4f8', '#0072B2')
    box('profile',   .272, .200, .235, .210, 'Enrolled profile\nRGB clouds & frozen τ', '#edf4f8', '#0072B2')
    arrow((.233, .305), (.264, .305))
    # Reference branch feeds upward into distribution comparison.
    ax.plot([.515, .679], [.305, .305], color='#0072B2', linewidth=.95)
    arrow((.679, .305), (.679, .596), color='#0072B2')
    ax.text(.612, .352, 'reference', fontsize=8, ha='center', va='center', color='#005a8d')

    # Authorized change & closed-loop refresh path.
    box('refresh',   .790, .200, .190, .210, 'Authorized change?\nRefresh reference', '#fff8e8', '#A97B27')
    arrow((.890, .596), (.890, .418), color='#A97B27', linestyle='--')
    ax.text(.934, .505, 'crossing', fontsize=8, ha='center', va='center', color='#8a641c')
    # Closed-loop return line along the bottom back to Trusted reference.
    ax.plot([.885, .885, .122], [.192, .072, .072], color='#A97B27', linewidth=.95, linestyle='--')
    arrow((.122, .072), (.122, .192), color='#A97B27', linestyle='--')
    ax.text(.505, .105, 'Refresh loop: authorize update  →  re-enroll reference  →  resume audit',
            ha='center', va='center', fontsize=8, color='#8a641c')

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for patch, text in texts:
        pb = patch.get_window_extent(renderer)
        tb = text.get_window_extent(renderer)
        assert pb.contains(tb.x0, tb.y0) and pb.contains(tb.x1, tb.y1), text.get_text()
    result = write_figure(fig, 'fig1_service_audit')
    result.update({'architecture_boxes': boxes, 'box_text_containment': True,
                   'dual_branch_convergence': True, 'closed_refresh_loop': True,
                   'removed_output_perturbation_attack_arrow': True})
    return result


def routing_figure():
    source = json.loads(SOURCE.read_text())
    rows = source['results']
    perm_rows = json.loads(PERM_SOURCE.read_text())['results']
    style = [('B20_q3', '#0072B2', 'o', 'B: 20 × 3 (60 calls)', 'B 20×3'),
             ('B40_q7', '#D55E00', 's', 'B: 40 × 7 (280 calls)', 'B 40×7'),
             ('S3_10_q3', '#009E73', '^', 'S3: 10 × 3 (30 calls)', 'S3 10×3'),
             ('S3_10_q7', '#CC79A7', 'D', 'S3: 10 × 7 (70 calls)', 'S3 10×7')]
    perm_clean_map = {
        r['protocol']: 100.0 * r['perm_genuine_frr_mean']
        for r in perm_rows
        if r['subgroup'] == 'all_distinct_labels' and r['p_honest'] == 1.0
    }
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.82), gridspec_kw={'width_ratios': [3.35, 1.55]})
    fig.subplots_adjust(left=.083, right=.985, top=.73, bottom=.165, wspace=.44)
    left, right = axes
    saved = {'curves': [], 'clean_frr': []}
    for index, (protocol, color, marker, legend, short) in enumerate(style):
        subset = sorted([r for r in rows if r['protocol'] == protocol and r['subgroup'] == 'all_distinct_labels'], key=lambda r: r['p_honest'])
        assert [r['p_honest'] for r in subset] == [0., .2, .4, .5, .6, .8, 1.]
        # Order by ascending fallback rate lambda = 1 - q (0.2 -> 1.0) so detection rises left-to-right.
        mixed = sorted(subset[:-1], key=lambda r: round(1.0 - r['p_honest'], 6))
        xs = np.array([round(1.0 - r['p_honest'], 6) for r in mixed])
        ys = 100 * np.array([r['rejection_mean'] for r in mixed])
        lower = 100 * np.array([r['rejection_seed_p05'] for r in mixed])
        upper = 100 * np.array([r['rejection_seed_p95'] for r in mixed])
        line, = left.plot(xs, ys, color=color, marker=marker, markersize=4, linewidth=1.3, label=legend)
        left.fill_between(xs, lower, upper, color=color, alpha=.13, linewidth=0)
        np.testing.assert_array_equal(line.get_xdata(), xs)
        np.testing.assert_array_equal(line.get_ydata(), ys)
        assert np.all(lower <= upper) and xs.min() > 0
        saved['curves'].append({'protocol': protocol, 'fallback_lambda': xs.tolist(), 'detection_pct': ys.tolist(),
                                 'seed_p05_pct': lower.tolist(), 'seed_p95_pct': upper.tolist()})
        clean = subset[-1]
        value = 100 * clean['genuine_frr_mean']
        p_val = perm_clean_map[protocol]
        right.barh(index - .18, value, height=.32, color=color, edgecolor='none')
        right.barh(index + .18, p_val, height=.32, facecolor='white', edgecolor=color, hatch='///', linewidth=.9)
        right.text(value + 1.0, index - .18, f'{value:.2f}%', ha='left', va='center', fontsize=8)
        right.text(p_val + 1.0, index + .18, f'{p_val:.2f}%', ha='left', va='center', fontsize=8, color='#333333')
        saved['clean_frr'].append({'protocol': protocol, 'frr_pct': value, 'perm_frr_pct': p_val})
    # Overlay B 40x7 and S3 10x3 stratified 999-permutation tests (p <= 0.05) to visualize null-quantile recovery.
    p_sub = sorted([r for r in perm_rows if r['protocol'] == 'B40_q7' and r['subgroup'] == 'all_distinct_labels' and r['p_honest'] < 1.0],
                   key=lambda r: round(1.0 - r['p_honest'], 6))
    px = np.array([round(1.0 - r['p_honest'], 6) for r in p_sub])
    py = 100 * np.array([r['perm_rejection_mean'] for r in p_sub])
    left.plot(px, py, color='#D55E00', linestyle='--', marker='s', markerfacecolor='white',
              markersize=4, linewidth=1.3, label='B: 40 × 7 (perm., p ≤ 0.05)')
    saved['curves'].append({'protocol': 'B40_q7_perm005', 'fallback_lambda': px.tolist(), 'detection_pct': py.tolist()})
    left.set(xlim=(.175, 1.025), ylim=(-3, 104), xticks=[.2, .4, .6, .8, 1.0], yticks=[0, 25, 50, 75, 100],
             xlabel='Fallback rate, λ = 1 − q', ylabel='Mixture detection (%)', title='(a) Offline mixed routing')
    left.grid(alpha=.20)
    right.set(yticks=range(4), yticklabels=[s[4] for s in style], xlim=(0, 56),
              xticks=[0, 20, 40], xlabel='Clean FRR (%) at λ = 0', title='(b) No fallback')
    right.invert_yaxis()
    right.grid(axis='x', alpha=.20)
    right.set_axisbelow(True)
    handles, labels = left.get_legend_handles_labels()
    from matplotlib.patches import Patch
    handles.append(Patch(facecolor='white', edgecolor='#4C5966', hatch='///', linewidth=.9))
    labels.append('Hatched (b): perm. (p ≤ 0.05)')
    legend = fig.legend(handles, labels, ncol=3, frameon=False, loc='upper center',
                        bbox_to_anchor=(.50, 1.0), fontsize=8, columnspacing=1.1, handlelength=1.9)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    lb = legend.get_window_extent(renderer)
    for ax in axes:
        assert not lb.overlaps(ax.title.get_window_extent(renderer)), 'legend overlaps title'
        assert not lb.overlaps(ax.get_window_extent(renderer)), 'legend overlaps data'
    info = write_figure(fig, 'fig6_mixed_routing')
    info.update({'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': sha(SOURCE),
                 'perm_source': str(PERM_SOURCE.relative_to(ROOT)), 'perm_source_sha256': sha(PERM_SOURCE),
                 'data': saved, 'no_p1_in_detection_curves': True,
                 'clean_frr_in_separate_panel': True, 'curve_data_exactly_match_source': True,
                 'removed_duplicate_embedded_caption': True,
                 'legend_does_not_overlap_titles_or_data': True})
    return info


def main():
    results = {'source_sha256': {str(Path(__file__).relative_to(ROOT)): sha(__file__),
                                str(SOURCE.relative_to(ROOT)): sha(SOURCE)},
               'fig1': service_figure(), 'fig6': routing_figure()}
    path = AUDIT / 'service_figures_manifest.json'
    path.write_text(json.dumps(results, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'manifest': str(path.relative_to(ROOT)), 'figures': ['fig1_service_audit', 'fig6_mixed_routing'],
                      'source_sha256': results['source_sha256'], 'bounds_checked': True}))


if __name__ == '__main__':
    main()
