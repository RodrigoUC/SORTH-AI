"""Compare one changed scheduler against a trusted baseline with equal fixtures.

Other scheduling modules must be byte-identical because both scheduler classes
run in the same process. Full-checkout comparisons use benchmark_scheduler_matrix.
Setup, gc.collect, independent validation, quality and traced-memory runs are
outside the reported wall-time samples. This measures no GUI operations.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.benchmark_scheduler_matrix import Scheduler, run


def load_baseline(root):
    candidate = ROOT / 'src' / 'scheduling'
    baseline = root / 'project_root' / 'src' / 'scheduling'
    candidate_files = {p.name for p in candidate.glob('*.py')}
    if {p.name for p in baseline.glob('*.py')} != candidate_files:
        raise ValueError('Baseline scheduling modules differ; use separate matrix runs')
    for name in candidate_files - {'scheduler.py'}:
        if (candidate / name).read_bytes() != (baseline / name).read_bytes():
            raise ValueError(f'Baseline dependency {name} differs; use separate matrix runs')
    spec = importlib.util.spec_from_file_location('src.scheduling._benchmark_baseline_scheduler',
                                                 baseline / 'scheduler.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Scheduler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root', type=Path, required=True,
                        help='Trusted, reviewed source checkout; its scheduler will be executed')
    parser.add_argument('--out', type=Path, default=Path('build/reports/scheduler-paired.json'))
    parser.add_argument('--repeats', type=int, default=10)
    parser.add_argument('--cases', nargs='+', default=['small', 'medium', 'large',
        'course_constraints', 'resources', 'pins_calendar', 'split_groups', 'saturated'])
    options = parser.parse_args(argv)
    if options.repeats < 2 or options.repeats % 2:
        parser.error('--repeats must be a positive even number of at least 2')
    baseline = load_baseline(options.baseline_root)
    options.out.parent.mkdir(parents=True, exist_ok=True)
    report = dict(python=sys.version, platform=platform.platform(), seed=42,
                  repeats=options.repeats, order='alternating baseline/candidate',
                  gc='collect before each run, outside timing; collector remains enabled', results=[])
    types = {'baseline': baseline, 'candidate': Scheduler}
    for name in options.cases:
        samples = {kind: [] for kind in types}
        expected = None
        for iteration in range(options.repeats):
            order = tuple(types) if iteration % 2 == 0 else tuple(reversed(types))
            for kind in order:
                result = run(name, scheduler_type=types[kind])
                signature = (result['assignment_sha256'], result['assignment_order_sha256'],
                             result['assigned'], result['quality'])
                if expected is not None and signature != expected:
                    raise AssertionError(f'Baseline/candidate result mismatch: {name}')
                expected = signature
                samples[kind].append(result['schedule_seconds'])
        memory = {}
        for kind, scheduler in types.items():
            measured = run(name, memory=True, scheduler_type=scheduler)
            signature = (measured['assignment_sha256'], measured['assignment_order_sha256'],
                         measured['assigned'], measured['quality'])
            if signature != expected:
                raise AssertionError(f'Memory-run result mismatch: {name}')
            memory[kind] = measured['peak_traced_bytes']
        median = {kind: statistics.median(values) for kind, values in samples.items()}
        item = dict(case=name, groups=result['groups'], assigned=result['assigned'], samples=samples,
                    median=median, speedup=median['baseline'] / median['candidate'],
                    peak_traced_bytes=memory, assignment_sha256=expected[0],
                    assignment_order_sha256=expected[1], exact_results_verified=True,
                    hard_constraints_verified=True)
        report['results'].append(item)
        options.out.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(item), flush=True)


if __name__ == '__main__':
    main()
