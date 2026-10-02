"""Lossless presentation layout shared by the schedule viewer and Excel export.

This module does not place or change assignments. It adds exact session boundaries
to the usual half-hour ticks so even short, adjacent sessions remain visible.
"""

from dataclasses import dataclass
from zlib import crc32
from typing import Iterable


COURSE_COLORS = (
    "E2EFDA", "DDEBF7", "FCE4D6", "E4DFEC", "F4CCCC",
    "DDEFEA", "F4DCE8", "E0E5F5", "FCE6DC", "E9E0F2",
)
GRID_TEXT_COLOR = "182536"


def course_color(code: str) -> str:
    """A stable color shared by every view, even after filtering/removal."""
    return COURSE_COLORS[crc32(code.encode("utf-8")) % len(COURSE_COLORS)]


GridEntry = tuple[str, int, int, int]


@dataclass(frozen=True)
class GridBlock:
    day: int
    row: int
    span: int
    entries: tuple[GridEntry, ...]


@dataclass(frozen=True)
class ScheduleGrid:
    boundaries: tuple[int, ...]
    blocks: tuple[GridBlock, ...]


def build_schedule_grid(
    entries: Iterable[GridEntry], day_start: int, day_end: int, step: int = 30,
) -> ScheduleGrid:
    """Build exact, half-open time intervals and non-overlapping visual blocks.

    Consecutive intervals with the same active sessions form one block. A block
    with multiple entries is a conflict and must show all its sessions. The
    range expands to include sessions outside the configured operating hours;
    malformed intervals raise an error instead of disappearing from the view.
    """
    if step <= 0 or day_end <= day_start:
        raise ValueError("La cuadrícula requiere un rango horario y un paso positivos.")
    entries = tuple(sorted(entries, key=lambda e: (e[1], e[2], e[3], e[0])))
    for gid, day, start, end in entries:
        if day < 1 or end <= start:
            raise ValueError(f"Intervalo inválido para el grupo {gid}.")

    lower = min([day_start] + [entry[2] for entry in entries])
    upper = max([day_end] + [entry[3] for entry in entries])
    first_tick = day_start + ((lower - day_start) // step) * step
    ticks = {t for t in range(first_tick, upper + 1, step) if t >= lower}
    ticks.update((lower, upper, day_start, day_end))
    for _, _, start, end in entries:
        ticks.update((start, end))
    boundaries = tuple(sorted(ticks))

    by_day: dict[int, list[GridEntry]] = {}
    for entry in entries:
        by_day.setdefault(entry[1], []).append(entry)

    blocks = []
    for day, day_entries in sorted(by_day.items()):
        for row, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
            active = tuple(e for e in day_entries if e[2] < end and e[3] > start)
            if not active:
                continue
            if (blocks and blocks[-1].day == day
                    and blocks[-1].row + blocks[-1].span == row
                    and blocks[-1].entries == active):
                previous = blocks[-1]
                blocks[-1] = GridBlock(day, previous.row, previous.span + 1, active)
            else:
                blocks.append(GridBlock(day, row, 1, active))
    return ScheduleGrid(boundaries, tuple(blocks))
