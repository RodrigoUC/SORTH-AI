class Group:

    def __init__(
        self,
        group_id: str,
        duration_min: int,
        required_room_type: str,
        size: int = 0,
        suggested_classroom: str | None = None,
        course_code: str | None = None,
        preferred_start_min: int | None = None,   # minutes from midnight
        preferred_day: str | None = None,
        course_name: str | None = None,
        parent_group_id: str | None = None,
        subgroup_index: int = 0,
        total_subgroups: int = 1
    ):
        self.group_id = group_id
        self.duration_min = duration_min          # duration in minutes
        self.required_room_type = required_room_type
        self.size = size
        self.suggested_classroom = suggested_classroom
        self.course_code = course_code
        self.course_name = course_name
        self.preferred_start_min = preferred_start_min
        self.preferred_day = preferred_day

        # For split groups (duration > 180 min)
        self.parent_group_id = parent_group_id
        self.subgroup_index = subgroup_index
        self.total_subgroups = total_subgroups

        # CSP fields
        # domain entries: (classroom, day_index, start_min)
        self.domain: list[tuple] = []
        # assignment: (classroom_name, day_index, start_min, end_min)
        self.assignment: tuple | None = None
        self.lab_override = False
        self.pinned = False
        self.unassigned_reason = ""

    def is_assigned(self) -> bool:
        return self.assignment is not None
