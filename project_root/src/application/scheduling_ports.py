"""Small input contracts owned by the scheduling use case, not by Excel."""
from collections.abc import Callable
from typing import Protocol

from ..scheduling.classroom import Classroom
from ..scheduling.course import Course


class ValidatedSchedulingInput(Protocol):
    """Only the imported data needed by generation; notices belong to the UI."""

    classrooms: dict[str, Classroom]
    courses: list[Course]


class SchedulingInputReader(Protocol):
    def load_validated(self) -> ValidatedSchedulingInput: ...

    def load_classrooms(self) -> dict[str, Classroom]: ...

    def load_courses(self) -> list[Course]: ...


SchedulingReaderFactory = Callable[[str | None], SchedulingInputReader]
