from .time_model import TimeModel
from .classroom import Classroom
from .group import Group


class ScheduleState:

    def __init__(self, time_model: TimeModel, classrooms: list[Classroom], resources=None):
        self.resources = resources
        self.time_model = time_model
        self.classrooms = {c.name: c for c in classrooms}
        # assignments[group_id] = (classroom_name, day_index, start_min, end_min)
        self.assignments: dict[str, tuple] = {}

    def assign(self, group: Group, classroom_name: str,
               day: int, start_min: int, *, allow_lab_override: bool = False) -> bool:

        # Reassignment must be explicit (unassign, then assign). Overwriting an
        # existing record would leave its old interval occupied forever.
        if group.is_assigned() or group.group_id in self.assignments:
            return False

        if classroom_name not in self.classrooms:
            return False

        classroom = self.classrooms[classroom_name]
        end_min = start_min + group.duration_min

        if group.required_room_type == "LAB" and classroom.room_type != "LAB" and not allow_lab_override:
            return False

        if classroom.capacity < group.size:
            return False

        if not self.time_model.is_valid_interval(day, start_min, end_min):
            return False

        if self.time_model.overlaps_lunch(start_min, end_min):
            return False

        if not classroom.is_available(day, start_min, end_min):
            return False

        # Check classroom course restriction
        if not classroom.allows_course(group.course_code):
            return False

        if not self.resources_allow(group, day, start_min):
            return False

        group.lab_override = (group.required_room_type == "LAB" and classroom.room_type != "LAB")
        classroom.occupy(day, start_min, end_min)
        group.assignment = (classroom_name, day, start_min, end_min)
        self.assignments[group.group_id] = group.assignment

        return True

    def unassign(self, group: Group) -> None:
        if group.group_id not in self.assignments:
            return

        classroom_name, day, start_min, end_min = self.assignments[group.group_id]
        self.classrooms[classroom_name].release(day, start_min, end_min)

        group.assignment = None
        group.lab_override = False
        del self.assignments[group.group_id]

    def resources_allow(self, group, day, start_min):
        return self.resources is None or not self.resources.placement_issues(
            group.group_id, day, start_min, start_min + group.duration_min, self.assignments)
