"""Versioned project calendar. Dates and personal availability are out of scope."""
from dataclasses import dataclass

DEFAULT_DAYS = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado')
DAYS = (*DEFAULT_DAYS, 'Domingo')


@dataclass(frozen=True)
class ProjectCalendar:
    days: tuple[str, ...] = DEFAULT_DAYS
    day_start: int = 420
    day_end: int = 1320
    breaks: tuple[tuple[int, int], ...] = ((720, 780),)

    def __post_init__(self):
        if (not isinstance(self.days, (tuple, list)) or not self.days
                or any(not isinstance(d, str) or d not in DAYS for d in self.days)
                or len(set(self.days)) != len(self.days)):
            raise ValueError('Calendar requires unique supported teaching days')
        if (type(self.day_start) is not int or type(self.day_end) is not int
                or not 0 <= self.day_start < self.day_end <= 1440):
            raise ValueError('Calendar hours must be increasing integer minutes in 00:00–24:00')
        if not isinstance(self.breaks, (tuple, list)):
            raise ValueError('Calendar breaks must be intervals')
        intervals = []
        for item in self.breaks:
            if (not isinstance(item, (tuple, list)) or len(item) != 2
                    or any(type(value) is not int for value in item)
                    or not self.day_start <= item[0] < item[1] <= self.day_end):
                raise ValueError('Breaks must be within opening hours')
            intervals.append(tuple(item))
        intervals.sort()
        if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
            raise ValueError('Calendar breaks must not overlap')
        if sum(end - start for start, end in intervals) >= self.day_end - self.day_start:
            raise ValueError('Calendar must leave teaching time available')
        object.__setattr__(self, 'days', tuple(d for d in DAYS if d in self.days))
        object.__setattr__(self, 'breaks', tuple(intervals))

    def to_dict(self):
        return dict(version=1, days=list(self.days), day_start=self.day_start,
                    day_end=self.day_end, breaks=[list(interval) for interval in self.breaks])

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict) or set(value) != {'version', 'days', 'day_start', 'day_end', 'breaks'}
                or type(value['version']) is not int or value['version'] != 1):
            raise ValueError('Unsupported project calendar')
        return cls(value['days'], value['day_start'], value['day_end'], value['breaks'])
