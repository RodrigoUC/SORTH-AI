"""Palette regression checks: text, component boundaries and packaged icons."""
from pathlib import Path
import pytest
from src.gui.theme import COLORS, STYLESHEET
from src.scheduling.schedule_grid import COURSE_COLORS, GRID_TEXT_COLOR
from src.scheduling.course_style import COURSE_STYLES


def contrast(a, b):
    def luminance(value):
        value = value.lstrip('#')
        rgb = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
        return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))
    low, high = sorted((luminance(a), luminance(b)))
    return (high + .05) / (low + .05)


@pytest.mark.parametrize('foreground,background', [
    ('text', 'surface'), ('text', 'surface_alt'), ('muted', 'surface'),
    ('muted', 'canvas'), ('muted', 'surface_alt'), ('warning', 'canvas'),
    ('navy', 'surface'), ('muted', 'accent_soft'), ('navy', 'primary_soft'),
    ('on_primary', 'primary'), ('on_primary', 'primary_hover'),
    ('on_primary', 'primary_pressed'), ('on_navy', 'navy'),
    ('on_navy_muted', 'navy'), ('on_navy', 'navy_hover'),
    ('accent', 'accent_soft'), ('disabled_text', 'disabled'),
    ('danger', 'danger_soft'), ('success', 'success_soft'), ('warning', 'warning_soft'),
])
def test_text_contrast(foreground, background):
    assert contrast(COLORS[foreground], COLORS[background]) >= 4.5


@pytest.mark.parametrize('foreground,background', [
    ('border', 'surface'), ('border', 'canvas'), ('focus', 'surface'),
    ('focus', 'canvas'), ('on_primary', 'primary'), ('on_navy', 'navy'),
])
def test_controls_and_focus_contrast(foreground, background):
    assert contrast(COLORS[foreground], COLORS[background]) >= 3


def test_course_palette_keeps_readable_labels():
    assert all(contrast(GRID_TEXT_COLOR, color) >= 4.5 for color in COURSE_COLORS)


def test_course_edges_keep_non_text_contrast_against_fill_and_gutter():
    for style in COURSE_STYLES:
        assert contrast(style.accent, style.fill) >= 3
        assert contrast(style.accent, COLORS['surface']) >= 3
        assert style.fill not in (COLORS['danger_soft'][1:], COLORS['warning_soft'][1:])


def test_qss_resolved_and_sort_icons_exist():
    assert '$' not in STYLESHEET
    assert Path(COLORS['sort_up']).is_file()
    assert Path(COLORS['sort_down']).is_file()
