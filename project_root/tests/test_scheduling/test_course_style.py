"""Category identity does not depend on a schedule, locale or Python hash seed."""
import json
import os
import subprocess
import sys

from src.scheduling.course_style import (
    COURSE_COLORS, COURSE_STYLES, CourseStyle, course_color, course_style,
)


def test_palette_and_markers_scale_without_allocating_per_visible_course():
    codes = [f'COURSE-{number}' for number in range(1000)]
    forward = {code: course_style(code) for code in codes}
    reverse = {code: course_style(code) for code in reversed(codes)}
    assert forward == reverse
    assert {style.fill for style in forward.values()} == set(COURSE_COLORS)
    assert {style.marker for style in forward.values()} == set(range(4))
    assert len(set(forward.values())) == len(COURSE_STYLES) * 4
    for code in codes[::41]:
        assert course_style(code) == forward[code]
        assert course_color(code) == forward[code].fill


def test_known_identity_and_independent_marker_for_repeated_fill():
    assert course_style('BIO') == CourseStyle('D5ECE4', '2F7566', 3)
    assert course_style('QUI').fill == course_style('GEN').fill
    assert course_style('QUI').marker != course_style('GEN').marker


def test_process_restart_and_hash_seed_do_not_reassign_course_styles():
    code = (
        'import json; from dataclasses import asdict; '
        'from src.scheduling.course_style import course_style; '
        'print(json.dumps([asdict(course_style(c)) for c in ["BIO", "ÁLGEBRA", "BIO-GEO"]]))'
    )
    results = [subprocess.check_output([sys.executable, '-c', code],
               env={**os.environ, 'PYTHONHASHSEED': seed}, text=True)
               for seed in ('1', '527')]
    assert json.loads(results[0]) == json.loads(results[1])
