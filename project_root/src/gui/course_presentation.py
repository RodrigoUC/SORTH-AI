"""Background-aware screen colors, separate from permanent course identity.

Print consumers keep the Qt-free scheduling palette on their white paper.
Screen consumers resolve the same identity against the actual reading surface,
not a theme name or its declared mode. Cached values include that surface, so
live changes and isolated import previews cannot retain another theme's colors.
"""
from dataclasses import dataclass
from functools import lru_cache

from ..scheduling.course_style import CourseStyle, GRID_TEXT_COLOR
from .theme_contract import contrast_ratio


@dataclass(frozen=True)
class CoursePresentation:
    fill: str
    accent: str
    text: str
    marker: int


def _mix(first: str, second: str, amount: float) -> str:
    a = tuple(int(first[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(second[i:i + 2], 16) for i in (1, 3, 5))
    return '#' + ''.join(f'{round(x + (y - x) * amount):02X}' for x, y in zip(a, b))


@lru_cache(maxsize=256)
def course_presentation(style: CourseStyle, surface: str) -> CoursePresentation:
    """Keep hue/marker identity while fitting the destination reading surface.

    Original white surfaces retain the paper palette exactly. Dark surfaces use
    a restrained tint, light custom surfaces retain the familiar pastel family.
    Text always reaches 4.5:1; accents reach 3:1 on both fill and gutter. Identity
    is still the literal course code and marker, never color alone.
    """
    base_fill, base_accent = '#' + style.fill, '#' + style.accent
    if surface.upper() == '#FFFFFF':
        return CoursePresentation(base_fill, base_accent, '#' + GRID_TEXT_COLOR, style.marker)
    # Compare the real background, not imported metadata (which may say custom).
    dark = contrast_ratio('#FFFFFF', surface) > contrast_ratio('#000000', surface)
    fill = _mix(surface, base_accent, .30) if dark else _mix(surface, base_fill, .80)
    endpoints = ('#FFFFFF', '#000000')
    text = '#' + GRID_TEXT_COLOR
    if contrast_ratio(text, fill) < 4.5:
        text = max(endpoints, key=lambda color: contrast_ratio(color, fill))
    target = max(endpoints, key=lambda color: min(contrast_ratio(color, bg) for bg in (fill, surface)))
    accent = base_accent
    for step in range(101):
        accent = _mix(base_accent, target, step / 100)
        if min(contrast_ratio(accent, bg) for bg in (fill, surface)) >= 3:
            break
    return CoursePresentation(fill, accent, text, style.marker)
