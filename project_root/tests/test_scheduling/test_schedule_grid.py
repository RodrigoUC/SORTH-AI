"""The GUI and workbook must share lossless half-open session layout."""
import pytest

from src.scheduling.schedule_grid import build_schedule_grid


def covered_intervals(grid):
    return [(block.day, grid.boundaries[block.row],
             grid.boundaries[block.row + block.span], tuple(entry[0] for entry in block.entries))
            for block in grid.blocks]


def test_empty_grid_has_operating_boundaries_and_regular_ticks():
    grid = build_schedule_grid([], 420, 500)
    assert grid.boundaries == (420, 450, 480, 500)
    assert grid.blocks == ()


def test_short_adjacent_sessions_remain_separate_without_conflict():
    entries = [('A', 1, 425, 432), ('B', 1, 432, 439), ('C', 1, 439, 440)]
    grid = build_schedule_grid(entries, 420, 480)
    assert grid.boundaries == (420, 425, 432, 439, 440, 450, 480)
    assert covered_intervals(grid) == [(1, start, end, (gid,)) for gid, _, start, end in entries]


def test_conflicts_split_only_overlap_and_show_every_session():
    entries = [('A', 1, 420, 470), ('B', 1, 440, 460), ('C', 1, 450, 480)]
    grid = build_schedule_grid(entries, 420, 480)
    assert covered_intervals(grid) == [
        (1, 420, 440, ('A',)), (1, 440, 450, ('A', 'B')),
        (1, 450, 460, ('A', 'B', 'C')), (1, 460, 470, ('A', 'C')),
        (1, 470, 480, ('C',)),
    ]


def test_long_session_merges_regular_ticks_but_not_gaps_or_days():
    grid = build_schedule_grid([('A', 1, 420, 480), ('A', 2, 420, 480),
                                ('B', 1, 510, 540)], 420, 540)
    assert covered_intervals(grid) == [(1, 420, 480, ('A',)), (1, 510, 540, ('B',)),
                                      (2, 420, 480, ('A',))]
    assert [block.span for block in grid.blocks] == [2, 1, 2]


def test_grid_expands_to_exact_out_of_hours_boundaries():
    grid = build_schedule_grid([('early', 1, 407, 425), ('late', 2, 1331, 1343)], 420, 1320)
    assert grid.boundaries[0] == 407
    assert grid.boundaries[-1] == 1343
    assert 420 in grid.boundaries and 1320 in grid.boundaries
    assert covered_intervals(grid) == [(1, 407, 425, ('early',)), (2, 1331, 1343, ('late',))]


def test_deterministic_order_and_generator_input():
    entries = [('Z', 2, 420, 450), ('B', 1, 420, 450), ('A', 1, 420, 450)]
    assert build_schedule_grid(iter(entries), 420, 480) == build_schedule_grid(reversed(entries), 420, 480)
    assert covered_intervals(build_schedule_grid(entries, 420, 480)) == [
        (1, 420, 450, ('A', 'B')), (2, 420, 450, ('Z',))]


@pytest.mark.parametrize('start,end,step', [(420, 420, 30), (480, 420, 30),
                                           (420, 480, 0), (420, 480, -1)])
def test_invalid_operating_range_or_step_raises(start, end, step):
    with pytest.raises(ValueError):
        build_schedule_grid([], start, end, step)


@pytest.mark.parametrize('entry', [('bad', 0, 420, 450), ('bad', -1, 420, 450),
                                    ('bad', 1, 450, 450), ('bad', 1, 450, 420)])
def test_invalid_sessions_raise_instead_of_disappearing(entry):
    with pytest.raises(ValueError, match='bad'):
        build_schedule_grid([entry], 420, 480)


def test_each_atomic_interval_has_exactly_the_active_sessions():
    entries = [('A', 1, 419, 427), ('B', 1, 424, 450), ('C', 1, 450, 452),
               ('D', 2, 424, 480), ('E', 1, 440, 470)]
    grid = build_schedule_grid(entries, 420, 480)
    for day in (1, 2):
        for row, (start, end) in enumerate(zip(grid.boundaries, grid.boundaries[1:])):
            expected = {entry for entry in entries if entry[1] == day and entry[2] < end and entry[3] > start}
            blocks = [block for block in grid.blocks
                      if block.day == day and block.row <= row < block.row + block.span]
            assert len(blocks) == bool(expected)
            assert (set(blocks[0].entries) if blocks else set()) == expected


def test_course_colors_are_stable_palette_members_in_any_lookup_order():
    from src.scheduling.schedule_grid import COURSE_COLORS, course_color
    codes = ['BIO', 'ÁLGEBRA', 'A', 'Z', 'BIO-long-code']
    forward = {code: course_color(code) for code in codes}
    reverse = {code: course_color(code) for code in reversed(codes)}
    assert forward == reverse
    assert all(color in COURSE_COLORS for color in forward.values())
    # Lock the stable mapping rather than Python's process-randomized hash.
    assert course_color('BIO') == 'D5ECE4'
