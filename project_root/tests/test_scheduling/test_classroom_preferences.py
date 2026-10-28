"""Room suggestion mappings are derived once from canonical accepted courses."""
from src.scheduling.classroom_preferences import classroom_course_map
from src.scheduling.course import Course


def test_mapping_preserves_explicit_row_choices_and_ignores_unknown_rooms():
    course = Course('BIO', 3, 60, 'REGULAR', suggested_classroom='DEFAULT',
                    group_suggestions=[{'aula': 'R'}, {'aula': None}, {'aula': 'UNKNOWN'}])
    other = Course('QUI', 1, 60, 'REGULAR', suggested_classroom='R')
    assert classroom_course_map([course, other], {'R', 'DEFAULT'}) == {'R': ['BIO', 'QUI']}
    assert course.group_suggestions == [{'aula': 'R'}, {'aula': None}, {'aula': 'UNKNOWN'}]
