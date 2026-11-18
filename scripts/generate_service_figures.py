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
    fig = plt.figure(figsize=(7.16, 2.2))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    boxes = {}
    texts = []
    def box(key, x, y, w, h, label, color='#edf4f8', edge='#0072B2'):
        patch = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.008,rounding_size=0.012',
                              facecolor=color, edgecolor=edge, linewidth=.9)
        ax.add_patch(patch)
        text = ax.text(x+w/2, y+h/2, label, ha='center', va='center', fontsize=8)
        boxes[key] = (x, y, w, h)
        texts.append((patch, text))
    def arrow(start, end, **kw):
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>', mutation_scale=9,
                                    color='#4C5966', linewidth=.9, **kw))
    box('reference', .026, .62, .212, .255, 'Trusted reference\nAllowed configuration')
    box('parser', .290, .62, .191, .255, 'Short RGB output\nParse and scale')
    box('score', .533, .62, .191, .255, 'Behavior score\nFrozen threshold')
    box('decision', .776, .62, .198, .255, 'Accept / investigate\nRecord audit result', '#eef5ec', '#35774C')
    for start, end in [((.246, .748), (.281, .748)), ((.489, .748), (.524, .748)), ((.732, .748), (.767, .748))]:
        arrow(start, end)
    box('monitor', .026, .29, .191, .20, 'Caller monitor\nCanary requests', '#f4f5f6', '#617183')
    box('broker', .290, .29, .191, .20, 'Cloud service broker\nRouting / caching', '#f4f5f6', '#617183')
    box('providers', .533, .29, .191, .20, 'Declared providers\nModel / precision', '#f4f5f6', '#617183')
    for start, end in [((.225, .39), (.281, .39)), ((.489, .39), (.524, .39))]:
        arrow(start, end)
    ax.plot([.630, .630, .386], [.50, .55, .55], color='#4C5966', linewidth=.9)
    arrow((.386, .55), (.386, .61))
    ax.text(.510, .580, 'responses', fontsize=8, ha='center', va='center', color='#4C5966')
    box('refresh', .776, .29, .198, .20, 'Allowed change?\nRefresh reference', '#fff8e8', '#A97B27')
    arrow((.875, .61), (.875, .50), linestyle='--')
    ax.text(.50, .118, 'Lifecycle: authorize configuration changes  →  refresh reference  →  resume monitoring',
            ha='center', va='center', fontsize=8, color='#4C5966')
    ax.text(.026, .96, 'Enrollment and verification', ha='left', va='center', fontsize=8, weight='bold')
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for patch, text in texts:
        pb = patch.get_window_extent(renderer)
        tb = text.get_window_extent(renderer)
        assert pb.contains(tb.x0, tb.y0) and pb.contains(tb.x1, tb.y1), text.get_text()
    result = write_figure(fig, 'fig1_service_audit')
    result.update({'architecture_boxes': boxes, 'box_text_containment': True,
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
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.85), gridspec_kw={'width_ratios': [3.4, 1.45]})
    fig.subplots_adjust(left=.083, right=.985, top=.74, bottom=.165, wspace=.45)
    left, right = axes
    saved = {'curves': [], 'clean_frr': []}
    for index, (protocol, color, marker, legend, short) in enumerate(style):
        subset = sorted([r for r in rows if r['protocol'] == protocol and r['subgroup'] == 'all_distinct_labels'], key=lambda r: r['p_honest'])
        assert [r['p_honest'] for r in subset] == [0., .2, .4, .5, .6, .8, 1.]
        mixed = subset[:-1]
        xs = np.array([r['p_honest'] for r in mixed])
        ys = 100 * np.array([r['rejection_mean'] for r in mixed])
        lower = 100 * np.array([r['rejection_seed_p05'] for r in mixed])
        upper = 100 * np.array([r['rejection_seed_p95'] for r in mixed])
        line, = left.plot(xs, ys, color=color, marker=marker, markersize=4, linewidth=1.3, label=legend)
        left.fill_between(xs, lower, upper, color=color, alpha=.13, linewidth=0)
        np.testing.assert_array_equal(line.get_xdata(), xs)
        np.testing.assert_array_equal(line.get_ydata(), ys)
        assert np.all(lower <= upper) and xs.max() < 1
        saved['curves'].append({'protocol': protocol, 'p_honest': xs.tolist(), 'detection_pct': ys.tolist(),
                                 'seed_p05_pct': lower.tolist(), 'seed_p95_pct': upper.tolist()})
        clean = subset[-1]
        value = 100 * clean['genuine_frr_mean']
        right.barh(index, value, height=.58, color=color, edgecolor='white')
        right.text(value + 1, index, f'{value:.2f}%', ha='left', va='center', fontsize=8)
        saved['clean_frr'].append({'protocol': protocol, 'frr_pct': value})
    # Overlay B 40x7 stratified 999-permutation test (p <= 0.05) to visualize null-quantile recovery.
    p_sub = sorted([r for r in perm_rows if r['protocol'] == 'B40_q7' and r['subgroup'] == 'all_distinct_labels'],
                   key=lambda r: r['p_honest'])[:-1]
    px = np.array([r['p_honest'] for r in p_sub])
    py = 100 * np.array([r['perm_rejection_mean'] for r in p_sub])
    left.plot(px, py, color='#D55E00', linestyle='--', marker='s', markerfacecolor='white',
              markersize=4, linewidth=1.3, label='B: 40 × 7 (perm., p ≤ 0.05)')
    saved['curves'].append({'protocol': 'B40_q7_perm005', 'p_honest': px.tolist(), 'detection_pct': py.tolist()})
    left.set(xlim=(-.025, .825), ylim=(-3, 104), xticks=[0, .2, .4, .6, .8], yticks=[0, 25, 50, 75, 100],
             xlabel='Declared-route probability, q < 1', ylabel='Mixture detection (%)', title='(a) Offline mixed routing')
    left.grid(alpha=.20)
    right.set(yticks=range(4), yticklabels=[s[4] for s in style], xlim=(0, 52),
              xticks=[0, 20, 40], xlabel='Clean FRR (%) at q = 1', title='(b) No fallback')
    right.invert_yaxis()
    right.grid(axis='x', alpha=.20)
    right.set_axisbelow(True)
    handles, labels = left.get_legend_handles_labels()
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
