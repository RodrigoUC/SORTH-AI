"""Deterministic Qt consultation benchmark; synthetic data only, no timing assertions."""
import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
from PyQt6.QtWidgets import QApplication
from src.gui.schedule_viewer_widget import ScheduleViewerWidget
from src.scheduling.group import Group
from src.scheduling.time_model import TimeModel


def fixture(size):
    groups, assignments = [], {}
    for i in range(size):
        gid = f'BIO{i:05d}-G1'
        groups.append(Group(gid, 60, 'REGULAR', course_name=f'Biología marina {i % 10}', course_code=f'BIO{i:05d}'))
        if i % 5:
            assignments[gid] = (f'A{i % 20:02d}', i % 5 + 1, 480 + (i % 8) * 60, 540 + (i % 8) * 60)
    return groups, assignments


def summary(samples):
    return {'median_ms': round(statistics.median(samples), 3),
            'p95_ms': round(sorted(samples)[math.ceil(len(samples) * .95) - 1], 3),
            'samples': len(samples)}


def run(size, repeats, app):
    viewer = ScheduleViewerWidget()
    viewer.resize(1200, 800)
    groups, assignments = fixture(size)
    start = time.perf_counter()
    viewer.display_schedule(assignments, TimeModel.default(), groups)
    viewer.show()
    app.processEvents()
    load = (time.perf_counter() - start) * 1000
    output = {'groups': size, 'assigned': len(assignments), 'load_ms': round(load, 3)}
    for tab, name in [(0, 'list'), (1, 'grid'), (2, 'classroom')]:
        viewer.tabs.setCurrentIndex(tab)
        app.processEvents()
        samples, event_samples = [], []
        # Alternating broad/narrow/no-match queries, including accents and multiple words.
        queries = ('', 'biologia', 'marina 3', 'A02', 'no-match', 'BIO000')
        for iteration in range(repeats + 2):
            for query in queries:
                start = time.perf_counter()
                viewer._list_search.setText(query)
                filtered = time.perf_counter()
                app.processEvents()
                end = time.perf_counter()
                if iteration >= 2:
                    samples.append((end - start) * 1000)
                    event_samples.append((end - filtered) * 1000)
        output[name] = {'filter_through_events': summary(samples), 'events_only': summary(event_samples)}
    try:
        import resource
        output['process_peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except ImportError:
        output['process_peak_rss_kib'] = None
    viewer.close()
    viewer.deleteLater()
    app.processEvents()
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sizes', nargs='+', type=int, default=[100, 1000, 5000])
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    report = {'environment': {'python': platform.python_version(), 'platform': platform.platform(),
              'pyqt': PYQT_VERSION_STR, 'qt': QT_VERSION_STR, 'qpa': os.environ['QT_QPA_PLATFORM'],
              'style': app.style().objectName()}, 'results': []}
    for size in args.sizes:
        report['results'].append(run(size, args.repeats, app))
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
