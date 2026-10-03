# src/application/scheduling_service.py

from copy import deepcopy
from .scheduling_ports import SchedulingInputReader, SchedulingReaderFactory
from ..scheduling.cancellation import checkpoint

from ..scheduling.time_model import TimeModel
from ..scheduling.schedule_state import ScheduleState
from ..scheduling.scheduler import Scheduler
from ..scheduling.course import Course
from ..scheduling.validation import validate_schedule


class SchedulingService:
    """Generate from supplied domain data or an explicitly selected input reader.

    ``reader_factory`` receives ``excel_path`` only when input is missing. The
    optional historical fallback preserves ``SchedulingService(path).run()``;
    new GUI/CLI compositions provide the factory themselves.
    """

    def __init__(self, excel_path: str | None, seed: int | None = 42, *,
                 reader_factory: SchedulingReaderFactory | None = None):
        self.excel_path = excel_path
        self.seed = seed
        self._reader_factory = reader_factory

    def _input_reader(self) -> SchedulingInputReader:
        factory = self._reader_factory
        if factory is None:
            # Named compatibility bridge for SchedulingService(path).run().
            # New entrypoints inject their adapter from the composition root;
            # supplied-data callers never import or invoke this fallback.
            from ..bootstrap.scheduling import create_excel_reader
            factory = create_excel_reader
        return factory(self.excel_path)

    def run(self, courses: list[Course] | None = None,
            classroom_restrictions: dict[str, set[str]] | None = None,
            classrooms: dict | None = None,
            pinned_assignments: dict | None = None, lab_overrides=(), resources=None, calendar=None, cancelled=None):
        """
        Run the scheduling algorithm.

        Args:
            courses: List of Course objects. If None, loads through the input reader.
            classroom_restrictions: {classroom_name: {course_codes}} to apply
                                    restricted classrooms. If None, no restrictions.
            classrooms: Pre-built classrooms dict. If None, loads through the input reader.

        Returns:
            (assignments, groups), including partial or empty schedules.
            Invalid input/results and cancellation raise without accepting state.
        """
        checkpoint(cancelled)
        # Resolve I/O only when inputs are missing. Fully supplied requests
        # (including MCP previews) depend solely on domain/application code.
        if classrooms is None or courses is None:
            reader = self._input_reader()
            if classrooms is None and courses is None:
                imported = reader.load_validated()
                classrooms = imported.classrooms
                courses = imported.courses
            else:
                if classrooms is None:
                    classrooms = reader.load_classrooms()
                if courses is None:
                    courses = reader.load_courses()

        # 1. Isolate occupancy/restrictions from both caller and reader state.
        classrooms = deepcopy(classrooms)

        # Reset occupancy AND restrictions so re-runs start from a clean state
        for cls in classrooms.values():
            cls.occupancy.clear()
            cls.allowed_courses = None

        # 2. Apply classroom restrictions if provided
        if classroom_restrictions:
            for classroom_name, allowed_codes in classroom_restrictions.items():
                if classroom_name in classrooms:
                    classrooms[classroom_name].set_allowed_courses(allowed_codes)

        # 3. Build TimeModel (default 07:00-22:00, all 6 days)
        time_model = TimeModel.default() if calendar is None else TimeModel.from_calendar(calendar)

        # 4. Build ScheduleState
        state = ScheduleState(
            time_model=time_model,
            classrooms=list(classrooms.values()),
            resources=deepcopy(resources),
        )

        # 5. Generate groups from courses
        groups = []
        for course in courses:
            checkpoint(cancelled)
            groups.extend(course.generate_groups())

        # Validate the complete pin set before reserving anything. These copies
        # isolate failures from the last accepted UI/persisted schedule.
        pinned_assignments = dict(pinned_assignments or {})
        checkpoint(cancelled)
        errors = validate_schedule(pinned_assignments, groups, classrooms, time_model, lab_overrides, resources)
        if errors:
            raise ValueError("; ".join(map(str, errors)))
        by_id = {group.group_id: group for group in groups}
        for gid, (room, day, start, _end) in pinned_assignments.items():
            group = by_id[gid]
            if not state.assign(group, room, day, start, allow_lab_override=gid in lab_overrides):
                raise ValueError(f"{gid}: pinned reservation failed")
            group.pinned = True

        # 6. Run scheduler
        scheduler = Scheduler(seed=self.seed, cancelled=cancelled)
        scheduler.schedule(state, groups)

        # Return schedule even if partial (greedy may leave some groups unassigned)
        checkpoint(cancelled)
        errors = validate_schedule(state.assignments, groups, classrooms, time_model,
                                   {g.group_id for g in groups if g.lab_override}, resources)
        if errors:
            raise ValueError("; ".join(map(str, errors)))
        checkpoint(cancelled)
        return state.assignments, groups
