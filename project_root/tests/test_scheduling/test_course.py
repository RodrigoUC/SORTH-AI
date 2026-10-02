from src.scheduling.course import Course, SPLIT_THRESHOLD_MIN


def test_generate_groups_correct_count():
    course = Course(
        code="BIO101",
        number_of_groups=3,
        duration_min=120,
        required_room_type="LAB",
    )
    groups = course.generate_groups()
    assert len(groups) == 3
    assert groups[0].group_id == "BIO101-G1"
    assert groups[2].group_id == "BIO101-G3"


def test_groups_inherit_course_properties():
    course = Course(
        code="MAT200",
        number_of_groups=2,
        duration_min=90,
        required_room_type="REGULAR",
        preferred_start_min=480,
        preferred_day="Lunes",
    )
    groups = course.generate_groups()
    for g in groups:
        assert g.duration_min == 90
        assert g.required_room_type == "REGULAR"
        assert g.preferred_start_min == 480
        assert g.preferred_day == "Lunes"


def test_long_course_splits_into_subgroups():
    # 360 min > SPLIT_THRESHOLD_MIN (270) → three sessions of 120 min
    course = Course(
        code="BIO300",
        number_of_groups=1,
        duration_min=360,
        required_room_type="REGULAR",
    )
    groups = course.generate_groups()
    assert len(groups) == 3
    assert groups[0].group_id == "BIO300-G1-P1"
    assert groups[1].group_id == "BIO300-G1-P2"
    assert groups[0].parent_group_id == "BIO300-G1"
    assert groups[0].duration_min == 120
    assert groups[1].duration_min == 120
    assert groups[2].duration_min == 120
    assert sum(group.duration_min for group in groups) == 360


def test_short_course_no_split():
    course = Course(
        code="BIO100",
        number_of_groups=1,
        duration_min=SPLIT_THRESHOLD_MIN,
        required_room_type="REGULAR",
    )
    groups = course.generate_groups()
    assert len(groups) == 1
    assert groups[0].parent_group_id is None



def test_force_split_override_preserves_total_duration():
    course = Course("BIO", 1, 240, "REGULAR", force_split=True)
    groups = course.generate_groups()
    assert [group.duration_min for group in groups] == [120, 120]
    assert all(group.parent_group_id == "BIO-G1" for group in groups)


def test_force_no_split_preserves_long_session():
    course = Course("BIO", 1, 360, "REGULAR", force_split=False)
    groups = course.generate_groups()
    assert len(groups) == 1
    assert groups[0].duration_min == 360
    assert groups[0].parent_group_id is None


def test_split_merges_tiny_remainder_without_losing_minutes():
    course = Course("BIO", 1, 400, "REGULAR")
    assert [group.duration_min for group in course.generate_groups()] == [120, 120, 160]
