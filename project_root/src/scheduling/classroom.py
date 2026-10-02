class Classroom:

    def __init__(self, name: str, capacity: int, room_type: str,
                 description: str = "", campus: str = ""):
        self.name = name
        self.capacity = capacity
        self.room_type = room_type          # "LAB" or "REGULAR"
        self.description = description
        self.campus = campus

        # occupancy[day_index] = list of (start_min, end_min) intervals
        self.occupancy: dict[int, list[tuple[int, int]]] = {}

        # Courses allowed in this classroom (None = no restriction)
        self.allowed_courses: set[str] | None = None

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def is_available(self, day: int, start_min: int, end_min: int) -> bool:
        """Return True if no existing interval overlaps [start_min, end_min)."""
        for s, e in self.occupancy.get(day, []):
            if start_min < e and end_min > s:
                return False
        return True

    def occupy(self, day: int, start_min: int, end_min: int) -> None:
        self.occupancy.setdefault(day, []).append((start_min, end_min))

    def release(self, day: int, start_min: int, end_min: int) -> None:
        intervals = self.occupancy.get(day, [])
        try:
            intervals.remove((start_min, end_min))
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Restrictions
    # ------------------------------------------------------------------

    def set_allowed_courses(self, course_codes: set[str]) -> None:
        """Restrict this classroom to only the given course codes."""
        self.allowed_courses = set(course_codes)

    def allows_course(self, course_code: str | None) -> bool:
        """Return True if the course is allowed in this classroom."""
        if self.allowed_courses is None:
            return True
        return course_code in self.allowed_courses
