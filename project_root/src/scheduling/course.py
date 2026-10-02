from .group import Group

# Sessions longer than this are split across multiple days
SPLIT_THRESHOLD_MIN = 270  # 4.5 hours


class Course:

    def __init__(
        self,
        code: str,
        number_of_groups: int,
        duration_min: int,
        required_room_type: str,
        size: int = 0,
        suggested_classroom: str | None = None,
        preferred_day: str | None = None,
        preferred_start_min: int | None = None,
        name: str | None = None,
        group_suggestions: list[dict] | None = None,
        force_split: bool | None = None,
    ):
        self.code = code
        self.name = name
        self.number_of_groups = number_of_groups
        self.duration_min = duration_min
        self.required_room_type = required_room_type
        self.size = size
        self.suggested_classroom = suggested_classroom
        self.preferred_day = preferred_day
        self.preferred_start_min = preferred_start_min
        self.group_suggestions: list[dict] = group_suggestions or []
        # None = auto (split if > SPLIT_THRESHOLD_MIN)
        # True = always split regardless of duration
        # False = never split regardless of duration
        self.force_split: bool | None = force_split

    def generate_groups(self) -> list[Group]:
        groups = []

        for i in range(1, self.number_of_groups + 1):
            base_group_id = f"{self.code}-G{i}"
            suggestion = self.group_suggestions[i - 1] if i - 1 < len(self.group_suggestions) else {}
            aula      = suggestion.get("aula") or self.suggested_classroom
            pref_day  = suggestion.get("preferred_day") or self.preferred_day
            pref_start = suggestion.get("preferred_start_min")
            if pref_start is None:
                pref_start = self.preferred_start_min

            if self.duration_min <= SPLIT_THRESHOLD_MIN:
                should_split = False
            else:
                should_split = True
            # User override
            if self.force_split is True:
                should_split = True
            elif self.force_split is False:
                should_split = False

            if not should_split:
                groups.append(Group(
                    group_id=base_group_id,
                    duration_min=self.duration_min,
                    required_room_type=self.required_room_type,
                    size=self.size,
                    suggested_classroom=aula,
                    course_code=self.code,
                    preferred_start_min=pref_start,
                    preferred_day=pref_day,
                    course_name=self.name,
                ))
            else:
                parts = self._split_duration(self.duration_min)
                for idx, part_min in enumerate(parts, 1):
                    groups.append(Group(
                        group_id=f"{base_group_id}-P{idx}",
                        duration_min=part_min,
                        required_room_type=self.required_room_type,
                        size=self.size,
                        suggested_classroom=aula,
                        course_code=self.code,
                        preferred_start_min=pref_start,
                        preferred_day=pref_day,
                        course_name=self.name,
                        parent_group_id=base_group_id,
                        subgroup_index=idx,
                        total_subgroups=len(parts),
                    ))

        return groups

    def _split_duration(self, duration_min: int) -> list[int]:
        """
        Split a long session into parts of at most 120 min.
        Last chunk is at least 60 min; if remainder < 60, merge into previous.
        """
        chunk = 120
        parts = []
        remaining = duration_min
        while remaining > chunk:
            parts.append(chunk)
            remaining -= chunk
        # Avoid tiny last chunks: merge remainder into previous if < 60 min
        if parts and remaining < 60:
            parts[-1] += remaining
        else:
            parts.append(remaining)
        return parts
