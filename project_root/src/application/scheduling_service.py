# src/application/scheduling_service.py

from copy import deepcopy

from ..scheduling.time_model import TimeModel
from ..scheduling.schedule_state import ScheduleState
from ..scheduling.scheduler import Scheduler
from ..scheduling.course import Course
from ..scheduling.validation import validate_schedule


class SchedulingService:

    def __init__(self, excel_path: str | None, seed: int | None = 42):
        self.excel_path = excel_path
        self.seed = seed

    def run(self, courses: list[Course] | None = None,
            classroom_restrictions: dict[str, set[str]] | None = None,
            classrooms: dict | None = None,
            pinned_assignments: dict | None = None, lab_overrides=()):
        """
        Run the scheduling algorithm.

        Args:
            courses: List of Course objects. If None, loads from Excel.
            classroom_restrictions: {classroom_name: {course_codes}} to apply
                                    restricted classrooms. If None, no restrictions.
            classrooms: Pre-built classrooms dict. If None, loads from Excel.

        Returns:
            (assignments, groups) on success, (None, None) on failure.
        """
        # Optional file adapter is loaded only for the legacy Excel workflow.
        # Supplied-data callers need neither pandas, Qt nor filesystem access.
        if classrooms is None or courses is None:
            from ..infrastructure.excel_reader import ExcelReader
            reader = ExcelReader(self.excel_path)
        if classrooms is None and courses is None:
            imported = reader.load_validated()
            classrooms = imported.classrooms
            courses = imported.courses

        # 1. Load classrooms (use provided or load from Excel)
        if classrooms is None:
            classrooms = reader.load_classrooms()
        else:
            classrooms = deepcopy(classrooms)  # isolate occupancy and restrictions from the UI

        # Reset occupancy AND restrictions so re-runs start from a clean state
        for cls in classrooms.values():
            cls.occupancy.clear()
            cls.allowed_courses = None

        # 2. Apply classroom restrictions if provided
        if classroom_restrictions:
            for classroom_name, allowed_codes in classroom_restrictions.items():
                if classroom_name in classrooms:
                    classrooms[classroom_name].set_allowed_courses(allowed_codes)

        # 3. Load courses from Excel if not provided externally
        if courses is None:
            courses = reader.load_courses()

        # 4. Build TimeModel (default 07:00-22:00, all 6 days)
        time_model = TimeModel.default()

        # 5. Build ScheduleState
        state = ScheduleState(
            time_model=time_model,
            classrooms=list(classrooms.values()),
        )

        # 6. Generate groups from courses
        groups = []
        for course in courses:
            groups.extend(course.generate_groups())

        # Validate the complete pin set before reserving anything. These copies
        # isolate failures from the last accepted UI/persisted schedule.
        pinned_assignments = dict(pinned_assignments or {})
        errors = validate_schedule(pinned_assignments, groups, classrooms, time_model, lab_overrides)
        if errors:
            raise ValueError("; ".join(errors))
        by_id = {group.group_id: group for group in groups}
        for gid, (room, day, start, _end) in pinned_assignments.items():
            group = by_id[gid]
            if not state.assign(group, room, day, start, allow_lab_override=gid in lab_overrides):
                raise ValueError(f"{gid}: pinned reservation failed")
            group.pinned = True

        # 7. Run scheduler
        scheduler = Scheduler(seed=self.seed)
        scheduler.schedule(state, groups)

        # Return schedule even if partial (greedy may leave some groups unassigned)
        errors = validate_schedule(state.assignments, groups, classrooms, time_model,
                                   {g.group_id for g in groups if g.lab_override})
        if errors:
            raise ValueError("; ".join(errors))
        return state.assignments, groups
