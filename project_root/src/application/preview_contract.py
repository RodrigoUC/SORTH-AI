"""SDK-free, strict and bounded JSON contract for stateless previews.

The small validator deliberately supports only the JSON Schema keywords used
below. Keeping this contract in the application layer prevents MCP/Qt imports.
"""
from copy import deepcopy
import re

MAX_SESSIONS = 128
MAX_CANDIDATES = 100_000
MAX_INPUT_BYTES = 131_072
MAX_OUTPUT_BYTES = 262_144


def obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False}


def array(items, maximum, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum}


def integer(low, high):
    return {"type": "integer", "minimum": low, "maximum": high}


ID = {"type": "string", "minLength": 1, "maxLength": 64,
      "pattern": r"^[A-Za-z0-9][A-Za-z0-9_-]*$"}
TEXT = {"type": "string", "maxLength": 160}
ROOM_TYPE = {"type": "string", "enum": ["LAB", "REGULAR"]}
DAY = {"type": "string", "enum": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]}
COURSE = obj({
    "code": ID, "number_of_groups": integer(1, 16), "duration_min": integer(1, 540),
    "required_room_type": ROOM_TYPE, "size": integer(1, 1000), "name": TEXT,
    "suggested_classroom": ID, "preferred_day": DAY,
    "preferred_start_min": integer(420, 1319), "force_split": {"type": "boolean"},
}, ["code", "number_of_groups", "duration_min", "required_room_type", "size"])
ROOM = obj({"name": ID, "capacity": integer(1, 1000), "room_type": ROOM_TYPE})
RESTRICTION = obj({"classroom": ID, "allowed_courses": array(ID, 32)})
INPUT_SCHEMA = obj({
    "courses": array(COURSE, 32, 1), "classrooms": array(ROOM, 16, 1),
    "seed": integer(0, 2**32 - 1), "classroom_restrictions": array(RESTRICTION, 16),
}, ["courses", "classrooms", "seed"])

NOTICE = obj({"code": {"type": "string", "maxLength": 64},
              "message": {"type": "string", "maxLength": 512}})
ASSIGNMENT = obj({"group_id": {"type": "string", "maxLength": 96},
                  "course_code": ID, "classroom": ID, "day": integer(1, 6),
                  "start_min": integer(420, 1319), "end_min": integer(421, 1320)})
PENDING = obj({"group_id": {"type": "string", "maxLength": 96},
               "reason": {"type": "string", "maxLength": 512}})
CAPABILITIES = [
    "preview_only_no_persistence", "strict_lab_no_override", "room_capacity_and_conflicts",
    "course_room_restrictions", "split_sessions_distinct_days_same_time",
    "mon_sat_0700_2200_lunch_1200_1300", "preferences_are_soft",
    "no_teacher_cohort_travel_or_custom_calendar_constraints", "greedy_not_optimality_proof",
]
OUTPUT_SCHEMA = obj({
    "status": {"type": "string", "enum": ["validated", "complete", "partial"]},
    "normalized": INPUT_SCHEMA, "session_count": integer(1, MAX_SESSIONS),
    "candidate_upper_bound": integer(0, MAX_CANDIDATES),
    "assignments": array(ASSIGNMENT, MAX_SESSIONS), "pending": array(PENDING, MAX_SESSIONS),
    "notices": array(NOTICE, 8),
    "capabilities": array({"type": "string", "enum": CAPABILITIES}, len(CAPABILITIES)),
})


ERROR_SCHEMA = obj({"error": obj({
    "code": {"type": "string", "maxLength": 64},
    "path": {"type": "string", "maxLength": 256},
    "message": {"type": "string", "maxLength": 512},
})})
TOOL_OUTPUT_SCHEMA = {"type": "object", "oneOf": [OUTPUT_SCHEMA, ERROR_SCHEMA]}


class ContractError(ValueError):
    def __init__(self, code, path, message):
        super().__init__(message)
        self.code, self.path, self.message = code, path, message

    def as_dict(self):
        return {"code": self.code, "path": self.path, "message": self.message}


def validate_shape(value, schema, path="request"):
    """Validate this module's closed JSON Schema subset without coercion."""
    kind = schema["type"]
    types = {"object": dict, "array": list, "integer": int, "string": str, "boolean": bool}
    if type(value) is not types[kind]:
        raise ContractError("INVALID_TYPE", path, f"Expected {kind}; provide explicit typed data.")
    if kind == "object":
        if set(value) - set(schema["properties"]):
            # Never echo unknown keys: they may contain secrets or prompt text.
            raise ContractError("UNSUPPORTED_FIELD", path, "Unknown fields are unsupported. Use only advertised fields; clarify other constraints with the user.")
        for key in schema["required"]:
            if key not in value:
                raise ContractError("MISSING_FIELD", f"{path}.{key}", "Required field missing; ask the user rather than guessing.")
        for key, child in value.items():
            validate_shape(child, schema["properties"][key], f"{path}.{key}")
    elif kind == "array":
        if not schema["minItems"] <= len(value) <= schema["maxItems"]:
            raise ContractError("LIMIT", path, f"Provide {schema['minItems']}–{schema['maxItems']} items.")
        for i, child in enumerate(value):
            validate_shape(child, schema["items"], f"{path}[{i}]")
    elif kind == "integer" and not schema["minimum"] <= value <= schema["maximum"]:
        raise ContractError("LIMIT", path, f"Use an integer from {schema['minimum']} to {schema['maximum']}.")
    elif kind == "string":
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 512):
            raise ContractError("LIMIT", path, "Text length exceeds the advertised bound or is empty.")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise ContractError("INVALID_ID", path, "Use an ASCII letter/digit followed by letters, digits, underscores or hyphens; no paths.")
        if any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ContractError("INVALID_TEXT", path, "Control characters and unpaired Unicode surrogates are unsupported.")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError("UNSUPPORTED_VALUE", path, "Use one of the values advertised in the schema; clarify unsupported rules.")


def normalized_request(value):
    validate_shape(value, INPUT_SCHEMA)
    result = deepcopy(value)
    result.setdefault("classroom_restrictions", [])
    for field, key in (("courses", "code"), ("classrooms", "name"),
                       ("classroom_restrictions", "classroom")):
        ids = [item[key] for item in result[field]]
        if len(ids) != len(set(ids)):
            raise ContractError("DUPLICATE_ID", f"request.{field}", "Identifiers must be unique.")
    rooms = {room["name"] for room in result["classrooms"]}
    codes = {course["code"] for course in result["courses"]}
    for i, course in enumerate(result["courses"]):
        if "suggested_classroom" in course and course["suggested_classroom"] not in rooms:
            raise ContractError("UNKNOWN_ROOM", f"request.courses[{i}].suggested_classroom", "Reference a supplied classroom.")
    for i, restriction in enumerate(result["classroom_restrictions"]):
        if restriction["classroom"] not in rooms or not set(restriction["allowed_courses"]) <= codes:
            raise ContractError("UNKNOWN_REFERENCE", f"request.classroom_restrictions[{i}]", "Reference only supplied classrooms and course codes.")
        if len(set(restriction["allowed_courses"])) != len(restriction["allowed_courses"]):
            raise ContractError("DUPLICATE_ID", f"request.classroom_restrictions[{i}]", "List each allowed course once.")
    return result
