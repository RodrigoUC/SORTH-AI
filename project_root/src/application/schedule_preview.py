"""Pure preview use cases: no files, sessions, SDK, GUI or model service."""
from typing import Protocol

from .preview_contract import (CAPABILITIES, MAX_CANDIDATES, MAX_SESSIONS,
                               OUTPUT_SCHEMA, ContractError, normalized_request, validate_shape)
from .scheduling_service import SchedulingService
from .schedule_result import matches_requested_groups
from ..scheduling.classroom import Classroom
from ..scheduling.course import Course
from ..scheduling.time_model import TimeModel
from ..scheduling.validation import validate_schedule, unassigned_reason


class SchedulingPort(Protocol):
    def run(self, courses=None, classroom_restrictions=None, classrooms=None): ...


def domain_input(normalized):
    courses = [Course(**course) for course in normalized["courses"]]
    rooms = {room["name"]: Classroom(**room) for room in normalized["classrooms"]}
    restrictions = {r["classroom"]: set(r["allowed_courses"])
                    for r in normalized["classroom_restrictions"]}
    return courses, rooms, restrictions


def validate_configuration(request):
    normalized = normalized_request(request)
    courses, rooms, _ = domain_input(normalized)
    groups = [group for course in courses for group in course.generate_groups()]
    if len(groups) > MAX_SESSIONS:
        raise ContractError("SESSION_LIMIT", "request.courses", f"Split sessions total {len(groups)}; reduce to at most {MAX_SESSIONS}.")
    if len({group.group_id for group in groups}) != len(groups):
        raise ContractError("DUPLICATE_GROUP", "request.courses", "Course codes generate colliding group identifiers; choose distinct codes.")
    # Full-day grid has <=31 starts; preference windows <=13. Six fixed days.
    upper = len(groups) * len(rooms) * 6 * 31
    if upper > MAX_CANDIDATES:
        raise ContractError("CANDIDATE_LIMIT", "request", f"Candidate bound {upper} exceeds {MAX_CANDIDATES}; reduce rooms or groups.")
    result = {"status": "validated", "normalized": normalized,
              "session_count": len(groups), "candidate_upper_bound": upper,
              "assignments": [], "pending": [], "notices": [{
                  "code": "SCOPE", "message": "Input accepted within supported rules. This does not prove feasibility. Preferences may be relaxed; teacher/cohort constraints are not modeled."}],
              "capabilities": list(CAPABILITIES)}
    validate_shape(result, OUTPUT_SCHEMA, "result")
    return result


def generate_preview(request, scheduler: SchedulingPort | None = None):
    result = validate_configuration(request)
    courses, rooms, restrictions = domain_input(result["normalized"])
    service = scheduler if scheduler is not None else SchedulingService(None, result["normalized"]["seed"])
    expected_groups = [group for course in courses for group in course.generate_groups()]
    _, validation_rooms, validation_restrictions = domain_input(result["normalized"])
    assignments, groups = service.run(courses=courses, classrooms=rooms,
                                    classroom_restrictions=restrictions)
    # Independent validation also protects against alternate implementations.
    for room, allowed in validation_restrictions.items():
        validation_rooms[room].set_allowed_courses(allowed)
    # Do not trust a port to redefine the requested population or constraints.
    # Canonical groups were built before invoking it and are never handed over.
    if (not isinstance(assignments, dict)
            or not matches_requested_groups(groups, expected_groups, ordered=True)):
        raise ContractError("INVALID_RESULT", "result", "Scheduler changed or omitted requested groups; no proposal was returned or saved.")
    errors = validate_schedule(assignments, expected_groups, validation_rooms, TimeModel.default())
    if errors:
        raise ContractError("INVALID_RESULT", "result", "Generated result failed independent validation; no proposal was returned or saved.")
    by_id = {group.group_id: group for group in groups}
    result["assignments"] = [{"group_id": gid, "course_code": by_id[gid].course_code,
                              "classroom": slot[0], "day": slot[1],
                              "start_min": slot[2], "end_min": slot[3]}
                             for gid, slot in sorted(assignments.items())]
    result["pending"] = [{"group_id": group.group_id, "reason": str(unassigned_reason(group, validation_rooms, TimeModel.default()))}
                         for group in expected_groups if group.group_id not in assignments]
    result["status"] = "partial" if result["pending"] else "complete"
    result["notices"].append({"code": "PREVIEW_ONLY", "message": "No session was read or changed. Review this normalized configuration and proposal; no save, apply or LAB override is performed. Excel is available separately through generate_excel after scope confirmation."})
    validate_shape(result, OUTPUT_SCHEMA, "result")
    return result
