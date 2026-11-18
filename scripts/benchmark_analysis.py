#!/usr/bin/env python3
"""Reproduce offline benchmark and calibration analyses without model/API access.

Run: UV_OFFLINE=1 uv run --offline --no-project --with numpy python -B scripts/benchmark_analysis.py --stage all
Existing logs, frozen reports and all paper/figure files are checksum protected.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def network_guard(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto', 'subprocess.Popen'):
        raise RuntimeError('Offline analysis forbids network access and child processes: '+event)


def csv_write(path, rows):
    if not rows: return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys); writer.writeheader()
        for r in rows:
            writer.writerow({k: json.dumps(v, sort_keys=True, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in r.items()})


def check_inputs(out):
    manifest = json.loads((ROOT/'results/integrity_manifest.json').read_text())
    mismatches = [p for p, expected in manifest['files'].items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != expected]
    if mismatches:
        raise AssertionError('Protected inputs changed: '+str(mismatches))
    return {'protected_files': len(manifest['files']), 'raw_logs': sum(p.endswith('.jsonl') for p in manifest['files']),
            'all_hashes_unchanged': True, 'manuscript_prose_unchanged': True, 'live_api_calls': 0,
            'network_guard': 'Python audit hook blocks socket connect/DNS/sendto and subprocesses'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['all', 'compare', 'calibrate', 'baselines', 'charts', 'verify', 'report'], default='all')
    parser.add_argument('--output', type=Path, default=ROOT/'results/benchmark')
    parser.add_argument('--permutations', type=int, default=999)
    parser.add_argument('--bootstrap-repeats', type=int, default=256)
    args = parser.parse_args(); out = args.output.resolve()
    if args.stage != 'verify' and out == (ROOT/'results/benchmark').resolve() and (out/'comparisons.json').exists():
        parser.error('Refusing to overwrite protected results/benchmark; pass --stage verify or a fresh --output directory')
    if args.permutations < 19 or args.bootstrap_repeats < 2:
        parser.error('At least 19 permutations and 2 bootstrap repeats required')
    # All computational stages inherit an enforced zero-network/no-collector guard.
    sys.addaudithook(network_guard)
    from hueprint_audit.core import save, load
    from hueprint_audit.experiments import FILES, comparisons, calibration, color_spaces, b_budget
    from hueprint_audit.baselines import baselines
    check_inputs(out)
    if args.stage not in ('verify', 'report'):
        import numpy as np
        sources = [ROOT/'analyze.py', ROOT/'scripts/benchmark_analysis.py',
                   *sorted((ROOT/'scripts/hueprint_audit').glob('*.py'))]
        save(out/'analysis_protocol.json', {
            'version': 'benchmark_offline_v1_20261112', 'python_version': sys.version,
            'numpy_version': np.__version__, 'seed': 20261112,
            'jitter_seeds': list(range(20261021, 20261031)),
            'permutations': args.permutations, 'bootstrap_repeats': args.bootstrap_repeats,
            'raw_sources': FILES,
            'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'calibration': 'B-only thresholds and alpha CV; own enrollment-only bootstrap; no test-driven refit',
            'manuscript_changes': False, 'live_api_calls': 0})
    data = {} if args.stage in ('verify', 'report') else {name: load(path) for name, path in FILES.items()}
    if args.stage in ('all', 'compare'):
        result, pairs = comparisons(data, out)
        csv_write(out/'comparison_pairs.csv', pairs)
        flat = []
        for scenario, d in result.items():
            for m, s in d.get('metrics', {}).items(): flat.append({'scenario': scenario, 'metric': m, **s})
        csv_write(out/'comparisons.csv', flat)
        csv_write(out/'B_budget.csv', b_budget(data, out))
    if args.stage in ('all', 'charts'):
        rows, scale = color_spaces(data, out); csv_write(out/'color_spaces.csv', rows)
    if args.stage in ('all', 'calibrate'):
        rows, ps = calibration(data, out, args.permutations, args.bootstrap_repeats)
        csv_write(out/'calibration.csv', rows); csv_write(out/'energy_permutation.csv', ps)
    if args.stage in ('all', 'baselines'):
        rows, pairs = baselines(data, out, args.permutations)
        csv_write(out/'baseline_grid.csv', rows); csv_write(out/'baseline_pairs.csv', pairs)
    if args.stage in ('all', 'verify'):
        from hueprint_audit.validation import validate
        from hueprint_audit.table_checks import table_checks
        tables = table_checks(out)
        csv_write(out/'cluster_bootstrap.csv', [
            {'scenario': scenario, 'metric': metric, **values}
            for scenario, metrics in tables['cluster_bootstrap'].items()
            for metric, values in metrics.items()])
        csv_write(out/'S1_subgroups.csv', [
            {'scenario': scenario, 'metric_variant': metric, **values}
            for scenario, metrics in tables['S1_subgroups'].items()
            for metric, values in metrics.items()])
        save(out/'validation.json', {**check_inputs(out), **validate(out)})
    if args.stage in ('all', 'report'):
        from hueprint_audit.reporting import report
        report(out)
    check_inputs(out)
    print('completed', args.stage, flush=True)

if __name__ == '__main__': main()
