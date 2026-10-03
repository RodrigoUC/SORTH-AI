"""Stable, Qt-free course identities shared by screen and printable schedules.

Category colors deliberately avoid the red/orange warning and conflict palette.
A finite palette can repeat, so labels and block boundaries remain authoritative;
the independent marker adds a non-color distinction when categories repeat.
"""

from dataclasses import dataclass
from zlib import crc32


@dataclass(frozen=True)
class CourseStyle:
    fill: str
    accent: str
    marker: int = 0


# Muted blue, teal, violet, sage and neutral families from the desktop identity.
# Hex values omit '#', so Qt, openpyxl and ReportLab can consume one source.
COURSE_STYLES = (
    CourseStyle("D7E6F7", "37618C"),
    CourseStyle("D5ECE4", "2F7566"),
    CourseStyle("E5D9F2", "725292"),
    CourseStyle("DCE2F3", "4E6091"),
    CourseStyle("D3EBED", "35727E"),
    CourseStyle("E4ECD2", "667A3D"),
    CourseStyle("EDDDEA", "8A5776"),
    CourseStyle("DEE5EE", "556C7E"),
    CourseStyle("CFE2EA", "386D85"),
    CourseStyle("EAE3D7", "7D6847"),
    CourseStyle("DBDEF3", "5A62A2"),
    CourseStyle("DDEBD9", "537746"),
    CourseStyle("E3DDE8", "766587"),
    CourseStyle("CDE5E1", "376C61"),
    CourseStyle("E8E5F2", "76668F"),
    CourseStyle("E1E6D6", "697858"),
)
COURSE_COLORS = tuple(style.fill for style in COURSE_STYLES)
GRID_TEXT_COLOR = "182536"


def course_style(code: str) -> CourseStyle:
    """Return a course's permanent presentation, independent of visible data.

    CRC32 is deterministic across Python processes. Higher bits choose the
    marker independently of the fill: 0 solid, 1 dashed, 2 dotted, 3 double.
    Do not allocate by position, room, display name, language or filtered set.
    """
    identity = crc32(code.encode("utf-8"))
    base = COURSE_STYLES[identity % len(COURSE_STYLES)]
    return CourseStyle(base.fill, base.accent, (identity >> 16) % 4)


def course_color(code: str) -> str:
    """Compatibility helper for consumers that need only the category fill."""
    return course_style(code).fill
