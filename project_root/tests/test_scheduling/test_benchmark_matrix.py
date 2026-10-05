"""Synthetic benchmark inputs and explicit hard-constraint checks."""
import pytest

from tools.benchmark_scheduler_matrix import check, fixture, parse_args, run


def test_synthetic_benchmark_rejects_invalid_repeats():
    with pytest.raises(SystemExit):
        parse_args(['--repeats', '0'])


def test_synthetic_small_case_is_deterministic_and_uses_fresh_objects():
    first = run('small')
    second = run('small')
    assert first['assigned'] == first['groups'] == 24
    assert first['assignment_sha256'] == second['assignment_sha256']
    assert first['hard_constraints_verified'] and second['hard_constraints_verified']
    assert first['quality'] == second['quality']


def test_synthetic_fixture_contains_exact_off_grid_split_pin_and_calendar():
    state, groups, pins = fixture('pins_calendar')
    assert len(pins) == 2
    assert pins['C000-G1-P1'] == ('R00', 2, 467, 587)
    assert state.time_model.day_start == 457
    assert state.time_model.breaks == ((697, 752), (952, 967))
    assert check(state, groups, pins)
    with pytest.raises(AssertionError, match='Moved pin'):
        check(state, groups, {'C000-G1-P1': ('R00', 2, 477, 597)})


def test_paired_benchmark_rejects_odd_sample_count():
    from tools.benchmark_scheduler_pair import main
    with pytest.raises(SystemExit):
        main(['--baseline-root', '.', '--repeats', '3'])


def test_paired_benchmark_rejects_changed_shared_dependencies(tmp_path):
    from tools.benchmark_scheduler_pair import ROOT, load_baseline
    folder = tmp_path / 'project_root' / 'src' / 'scheduling'
    folder.mkdir(parents=True)
    for source in (ROOT / 'src' / 'scheduling').glob('*.py'):
        (folder / source.name).write_bytes(source.read_bytes())
    (folder / 'time_model.py').write_bytes((folder / 'time_model.py').read_bytes() + b'\n')
    with pytest.raises(ValueError, match='Baseline dependency time_model.py differs'):
        load_baseline(tmp_path)
