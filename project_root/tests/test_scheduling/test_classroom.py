from src.scheduling.classroom import Classroom


def test_classroom_occupy_and_release():
    c = Classroom("A1", capacity=30, room_type="REGULAR")

    assert c.is_available(1, 480, 600)   # 08:00-10:00 free

    c.occupy(1, 480, 600)
    assert not c.is_available(1, 480, 600)
    assert not c.is_available(1, 500, 580)  # overlap inside
    assert not c.is_available(1, 420, 500)  # overlap at start
    assert not c.is_available(1, 560, 660)  # overlap at end

    c.release(1, 480, 600)
    assert c.is_available(1, 480, 600)


def test_classroom_adjacent_slots_are_available():
    c = Classroom("A1", capacity=30, room_type="REGULAR")
    c.occupy(1, 480, 600)

    assert c.is_available(1, 600, 720)   # starts exactly when previous ends
    assert c.is_available(1, 360, 480)   # ends exactly when next starts


def test_classroom_course_restriction():
    c = Classroom("L-DEMO-1", capacity=16, room_type="LAB")
    c.set_allowed_courses({"DEM113P", "DEM114"})

    assert c.allows_course("DEM113P")
    assert c.allows_course("DEM114")
    assert not c.allows_course("DEM101")


def test_classroom_no_restriction_allows_all():
    c = Classroom("A1", capacity=30, room_type="REGULAR")
    assert c.allows_course("ANY_COURSE")
