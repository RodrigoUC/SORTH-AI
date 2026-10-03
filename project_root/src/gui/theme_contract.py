"""Version 1 data-only UI theme contract, shared by the app and theme skill.

This module has no Qt dependency and does not apply a theme or write preferences.
The schema describes the shape; this validator additionally checks strict JSON,
size, plain-text metadata and the actual intended color adjacencies.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping
import unicodedata


SCHEMA_VERSION = 1
MAX_THEME_BYTES = 16 * 1024
COURSE_GUTTER = "#FFFFFF"  # Original/print reference; live course gutters use surface.
COLOR_ROLES = (
    "canvas", "surface", "surface_alt",
    "header", "header_hover", "on_header", "on_header_muted",
    "text", "muted", "heading", "border", "divider",
    "primary", "primary_hover", "primary_pressed", "on_primary",
    "primary_soft", "on_primary_soft", "accent", "on_accent", "accent_soft",
    "focus", "disabled", "disabled_text",
    "success", "success_soft", "warning", "warning_soft", "danger", "danger_soft",
)
_HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")
_REQUIRED = frozenset(("schema_version", "name", "mode", "colors"))
_OPTIONAL = frozenset(("description",))


class ThemeValidationError(ValueError):
    """A rejected file, with actionable plain-text reasons and no partial result."""

    def __init__(self, issues):
        self.issues = tuple(issues)
        super().__init__("; ".join(self.issues))


@dataclass(frozen=True)
class ThemeSpec:
    name: str
    mode: str
    colors: Mapping[str, str]
    description: str | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self):
        # Direct construction cannot retain a mutable caller-owned mapping.
        # Full validation remains the responsibility of validate_theme().
        object.__setattr__(self, "colors", MappingProxyType(dict(self.colors)))

    def to_dict(self):
        result = {"schema_version": self.schema_version, "name": self.name,
                  "mode": self.mode, "colors": dict(self.colors)}
        if self.description is not None:
            result["description"] = self.description
        return result


@dataclass(frozen=True)
class ContrastCheck:
    foreground: str
    background: str
    ratio: float
    minimum: float
    purpose: str

    @property
    def passes(self):
        # Never round before comparison: 4.499 is not 4.5.
        return self.ratio >= self.minimum


# These are rendering contracts, not every possible token combination. A new
# consumer must map its role to an existing adjacency or extend this contract.
_TEXT_PAIRS = (
    *(("text", bg, "body/control text") for bg in
      ("canvas", "surface", "surface_alt", "accent_soft", "primary_soft")),
    *(("muted", bg, "secondary/placeholder text") for bg in
      ("canvas", "surface", "surface_alt", "accent_soft", "primary_soft")),
    ("heading", "canvas", "section heading"),
    ("heading", "surface", "section heading"),
    ("on_primary_soft", "primary_soft", "overview/time gutter/hover tab"),
    *(("on_primary", bg, "primary action text") for bg in
      ("primary", "primary_hover", "primary_pressed")),
    *((fg, bg, "header/control/tooltip text") for fg in
      ("on_header", "on_header_muted") for bg in ("header", "header_hover")),
    ("on_accent", "accent", "text selection"),
    ("accent", "surface", "selected tab text"),
    ("accent", "accent_soft", "selected menu text"),
    ("disabled_text", "disabled", "disabled text (SORTH readability baseline)"),
    *((fg, bg, "semantic status text") for fg in ("success", "warning", "danger")
      for bg in ("canvas", "surface", fg + "_soft")),
    ("danger", "accent_soft", "pressed destructive action text"),
)
_BOUNDARY_PAIRS = (
    *(("border", bg, "control border/scrollbar") for bg in
      ("canvas", "surface", "surface_alt")),
    *(("focus", bg, "keyboard focus") for bg in
      ("canvas", "surface", "surface_alt", "primary_soft", "accent_soft")),
    *((fg, bg, "filled action boundary") for fg in
      ("primary", "primary_hover", "primary_pressed") for bg in ("canvas", "surface")),
    ("primary", "primary_soft", "hovered control border/progress chunk"),
    ("accent", "surface", "selected tab indicator"),
    ("accent", "accent_soft", "pressed control border"),
)


def contrast_ratio(first: str, second: str) -> float:
    """WCAG sRGB relative-luminance contrast for validated opaque colors."""
    def luminance(color):
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
                  for c in channels]
        return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))

    low, high = sorted((luminance(first), luminance(second)))
    return (high + .05) / (low + .05)


def contrast_checks(theme: ThemeSpec) -> tuple[ContrastCheck, ...]:
    colors = theme.colors
    checks = []
    for pairs, minimum in ((_TEXT_PAIRS, 4.5), (_BOUNDARY_PAIRS, 3.0)):
        for foreground, background, purpose in pairs:
            backdrop = background if background.startswith("#") else colors[background]
            checks.append(ContrastCheck(foreground, background,
                                        contrast_ratio(colors[foreground], backdrop),
                                        minimum, purpose))
    return tuple(checks)


def _label_issue(value, label, maximum):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        return f"{label} must contain 1–{maximum} plain-text characters"
    if value != value.strip() or any(
        char in "<>" or unicodedata.category(char).startswith("C") for char in value
    ):
        return f"{label} must be trimmed plain text without markup or control/format characters"
    return None


def validate_theme(data) -> ThemeSpec:
    """Validate an already-decoded object; use parse_theme for imported bytes.

    Never merges a partial theme with defaults or repairs palette choices.
    Returns a detached, read-only color mapping only after all checks pass.
    """
    if not isinstance(data, dict):
        raise ThemeValidationError(("theme must be a JSON object",))
    issues = []
    unknown = set(data) - _REQUIRED - _OPTIONAL
    if unknown:
        names = ", ".join(sorted(repr(key) for key in unknown))
        issues.append(f"theme has unknown fields ({names}); only schema_version, name, mode, colors and description are allowed")
    if _REQUIRED - set(data):
        issues.append("theme is missing required fields: " + ", ".join(sorted(_REQUIRED - set(data))))
    if type(data.get("schema_version")) is not int or data["schema_version"] != SCHEMA_VERSION:
        issues.append("schema_version must be the integer 1; future/unknown versions are not supported")
    for key, limit in (("name", 64), ("description", 240)):
        if key in data or key == "name":
            issue = _label_issue(data.get(key), key, limit)
            if issue:
                issues.append(issue)
    if data.get("mode") not in ("light", "dark"):
        issues.append("mode must be light or dark")
    colors = data.get("colors")
    if not isinstance(colors, dict):
        issues.append("colors must be an object containing all 30 v1 roles")
    else:
        missing = set(COLOR_ROLES) - set(colors)
        if missing:
            issues.append("colors is missing roles: " + ", ".join(sorted(missing)))
        unknown_roles = set(colors) - set(COLOR_ROLES)
        if unknown_roles:
            names = ", ".join(sorted(repr(key) for key in unknown_roles))
            issues.append(f"colors has unknown roles ({names}); paths, fonts, assets and style/code fields are not supported")
        for role in COLOR_ROLES:
            if role in colors and (not isinstance(colors[role], str) or not _HEX.fullmatch(colors[role])):
                issues.append(f"colors.{role} must be one opaque #RRGGBB color")
    if issues:
        raise ThemeValidationError(issues)
    theme = ThemeSpec(data["name"], data["mode"], MappingProxyType(dict(colors)), data.get("description"))
    failures = [check for check in contrast_checks(theme) if not check.passes]
    if failures:
        raise ThemeValidationError(tuple(
            f"{check.foreground} on {check.background}: {check.ratio:.4f}:1 is below "
            f"{check.minimum:g}:1 ({check.purpose})" for check in failures
        ))
    return theme


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ThemeValidationError(("duplicate JSON key is not allowed",))
        result[key] = value
    return result


def _reject_constant(_value):
    raise ThemeValidationError(("NaN and Infinity are not valid theme JSON values",))


def parse_theme(payload: bytes | str) -> ThemeSpec:
    """Strict, bounded JSON decoding for a complete imported theme."""
    if isinstance(payload, str):
        try:
            payload = payload.encode("utf-8")
        except UnicodeError as error:
            raise ThemeValidationError(("theme must be valid UTF-8",)) from error
    if not isinstance(payload, bytes):
        raise ThemeValidationError(("theme payload must be UTF-8 bytes or text",))
    if len(payload) > MAX_THEME_BYTES:
        raise ThemeValidationError(("theme exceeds the 16 KiB UTF-8 size limit",))
    try:
        data = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant)
    except ThemeValidationError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ThemeValidationError(("theme must be one valid UTF-8 JSON object without a BOM",)) from error
    return validate_theme(data)


def load_theme_file(path: str | Path) -> ThemeSpec:
    """Read no more than limit+1 bytes; no writes or theme activation."""
    with Path(path).open("rb") as stream:
        payload = stream.read(MAX_THEME_BYTES + 1)
    return parse_theme(payload)


def theme_json_schema() -> dict:
    """Structural schema; strict decoding and contrast still need this module."""
    label = {"type": "string", "minLength": 1,
             "description": "Trimmed plain text only; no markup or Unicode control/format characters. The canonical validator enforces this additional rule."}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "SORTH UI theme v1",
        "description": "Data-only theme. Maximum 16 KiB UTF-8. Structural schema validation alone does not establish contrast or runtime compatibility.",
        "type": "object", "additionalProperties": False,
        "required": ["schema_version", "name", "mode", "colors"],
        "properties": {
            "schema_version": {"type": "integer", "const": SCHEMA_VERSION},
            "name": {**label, "maxLength": 64},
            "description": {**label, "maxLength": 240},
            "mode": {"enum": ["light", "dark"]},
            "colors": {"type": "object", "additionalProperties": False,
                       "required": list(COLOR_ROLES), "properties": {
                           role: {"type": "string", "minLength": 7, "maxLength": 7,
                                  "pattern": "^#[0-9A-Fa-f]{6}$"}
                           for role in COLOR_ROLES}},
        },
    }
