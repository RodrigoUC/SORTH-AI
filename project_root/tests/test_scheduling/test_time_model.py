from src.scheduling.time_model import TimeModel


def test_default_time_model():
    tm = TimeModel.default()
    assert len(tm.days) == 6
    assert tm.day_start == 420   # 07:00
    assert tm.day_end == 1320    # 22:00


def test_is_valid_interval():
    tm = TimeModel.default()
    assert tm.is_valid_interval(1, 480, 600)    # 08:00-10:00 valid
    assert not tm.is_valid_interval(1, 300, 600)  # starts before 07:00
    assert tm.is_valid_interval(1, 1260, 1320)     # last evening hour
    assert not tm.is_valid_interval(1, 1260, 1321)  # ends after 22:00
    assert not tm.is_valid_interval(0, 480, 600)   # invalid day


def test_overlaps_lunch():
    tm = TimeModel.default()
    assert tm.overlaps_lunch(720, 840)    # 12:00-14:00 overlaps
    assert tm.overlaps_lunch(660, 750)    # 11:00-12:30 overlaps
    assert not tm.overlaps_lunch(480, 720)  # 08:00-12:00 does not overlap
    assert not tm.overlaps_lunch(780, 900)  # 13:00-15:00 does not overlap


def test_generate_start_candidates_no_preference():
    tm = TimeModel.default()
    candidates = tm.generate_start_candidates(120)  # 2h course, 30-min step
    # All candidates must fit within operating hours and not overlap lunch
    for s in candidates:
        assert s >= tm.day_start
        assert s + 120 <= tm.day_end
        assert not tm.overlaps_lunch(s, s + 120)


def test_generate_start_candidates_with_preference():
    tm = TimeModel.default()
    candidates = tm.generate_start_candidates(120, preferred_start_min=480)
    # With preference, step is 5 min — more candidates
    assert len(candidates) > 0
    assert 480 in candidates  # preferred start must be included


def test_minutes_to_hhmm():
    assert TimeModel.minutes_to_hhmm(480) == "08:00"
    assert TimeModel.minutes_to_hhmm(655) == "10:55"
    assert TimeModel.minutes_to_hhmm(780) == "13:00"


def test_hhmm_to_minutes():
    assert TimeModel.hhmm_to_minutes("0800") == 480
    assert TimeModel.hhmm_to_minutes("08:00") == 480
    assert TimeModel.hhmm_to_minutes("1055") == 655
    assert TimeModel.hhmm_to_minutes("13:00") == 780


def test_day_index_roundtrip():
    tm = TimeModel.default()
    for day in tm.days:
        idx = tm.to_day_index(day)
        assert tm.to_day_name(idx) == day



def test_early_off_grid_preference_is_preserved():
    tm = TimeModel.default()
    candidates = tm.generate_start_candidates(60, preferred_start_min=422)
    assert 422 in candidates
    assert all((start - 422) % 5 == 0 for start in candidates)
    assert all(tm.is_valid_interval(1, start, start + 60) for start in candidates)


def test_nonpositive_duration_has_no_candidates():
    tm = TimeModel.default()
    for duration in (0, -5):
        assert tm.generate_start_candidates(duration) == []
        assert tm.generate_start_candidates(duration, 480) == []
