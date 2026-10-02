class TimeModel:

    DAY_ORDER = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]

    # Default operating hours in minutes from midnight
    DEFAULT_DAY_START = 7 * 60    # 07:00 = 420
    DEFAULT_DAY_END   = 22 * 60   # 22:00 = 1320

    # Lunch block to avoid
    LUNCH_START = 12 * 60         # 12:00 = 720
    LUNCH_END   = 13 * 60         # 13:00 = 780

    # Candidate generation steps
    STEP_WITH_PREFERENCE    = 5   # minutes — when course has preferred_start_min
    STEP_WITHOUT_PREFERENCE = 30  # minutes — default to reduce domain size

    def __init__(self, days: list[str],
                 day_start: int = DEFAULT_DAY_START,
                 day_end: int = DEFAULT_DAY_END):
        self.days = self._sort_days(days)
        self.day_start = day_start  # minutes from midnight
        self.day_end = day_end      # minutes from midnight

        self.day_to_index = {d: i + 1 for i, d in enumerate(self.days)}
        self.index_to_day = {i + 1: d for i, d in enumerate(self.days)}
        self.days_count = len(self.days)

    def _sort_days(self, days: list[str]) -> list[str]:
        return sorted(set(days), key=lambda d: self.DAY_ORDER.index(d) if d in self.DAY_ORDER else 999)

    def is_valid_interval(self, day: int, start_min: int, end_min: int) -> bool:
        """Check that the interval fits within the operating hours of the given day."""
        if day < 1 or day > self.days_count:
            return False
        if start_min < self.day_start:
            return False
        if end_min > self.day_end:
            return False
        if start_min >= end_min:
            return False
        return True

    def overlaps_lunch(self, start_min: int, end_min: int) -> bool:
        """Return True if the interval overlaps with the lunch block (12:00-13:00)."""
        return start_min < self.LUNCH_END and end_min > self.LUNCH_START

    def generate_start_candidates(self, duration_min: int,
                                  preferred_start_min: int | None = None) -> list[int]:
        """
        Generate valid start times (in minutes) for a given duration.

        - If preferred_start_min is set: search ±30 min around preference with 5-min step.
        - If no preference: use 30-min step across full day.

        Returns list of start_min values where [start, start+duration] fits
        within operating hours and does not overlap lunch.
        """
        if duration_min <= 0:
            return []

        candidates = []

        if preferred_start_min is not None:
            search_start = max(self.day_start, preferred_start_min - 30)
            search_end   = min(self.day_end,   preferred_start_min + 30)
            # Keep the grid anchored to the preference even if the window is
            # clipped by opening time (for example a 07:02 preference).
            search_start += (preferred_start_min - search_start) % self.STEP_WITH_PREFERENCE
            t = search_start
            while t <= search_end:
                if t + duration_min <= self.day_end:
                    end = t + duration_min
                    if not self.overlaps_lunch(t, end):
                        candidates.append(t)
                t += self.STEP_WITH_PREFERENCE
            # Fallback: if preference window yields nothing, search full day
            if not candidates:
                t = self.day_start
                while t + duration_min <= self.day_end:
                    end = t + duration_min
                    if not self.overlaps_lunch(t, end):
                        candidates.append(t)
                    t += self.STEP_WITHOUT_PREFERENCE
        else:
            t = self.day_start
            while t + duration_min <= self.day_end:
                end = t + duration_min
                if not self.overlaps_lunch(t, end):
                    candidates.append(t)
                t += self.STEP_WITHOUT_PREFERENCE

        return candidates

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def to_day_index(self, day_name: str) -> int:
        return self.day_to_index[day_name]

    def to_day_name(self, day_index: int) -> str:
        return self.index_to_day[day_index]

    @staticmethod
    def minutes_to_hhmm(minutes: int) -> str:
        """Convert minutes-from-midnight to 'HH:MM' string."""
        h, m = divmod(minutes, 60)
        return f"{h:02d}:{m:02d}"

    @staticmethod
    def hhmm_to_minutes(hhmm: str) -> int:
        """Convert 'HH:MM' or 'HHMM' string to minutes from midnight."""
        hhmm = hhmm.strip().replace(":", "")
        h = int(hhmm[:2])
        m = int(hhmm[2:]) if len(hhmm) > 2 else 0
        return h * 60 + m

    @classmethod
    def default(cls) -> "TimeModel":
        """Create a TimeModel with all 6 days and default 07:00-22:00 hours."""
        return cls(cls.DAY_ORDER)
