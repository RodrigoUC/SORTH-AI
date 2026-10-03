"""Palette contracts, trusted assets and immutable native theme choices."""
from pathlib import Path
from PyQt6.QtCore import QFile, QIODevice
from dataclasses import FrozenInstanceError
import pytest
from src.gui.theme import COLORS, STYLESHEET, builtin_themes, stylesheet_for, trusted_assets
from src.gui.theme_contract import COLOR_ROLES, COURSE_GUTTER, ThemeSpec, contrast_ratio, contrast_checks
from src.scheduling.schedule_grid import COURSE_COLORS, GRID_TEXT_COLOR
from src.scheduling.course_style import COURSE_STYLES


@pytest.mark.parametrize('choice', builtin_themes(), ids=lambda choice: choice.key)
def test_builtin_contrast_contract(choice):
    assert all(check.passes for check in contrast_checks(choice.spec))
    assert set(choice.spec.colors) == set(COLOR_ROLES)
    assert '$' not in stylesheet_for(choice.spec)


def test_original_preserves_existing_canonical_palette():
    colors = builtin_themes()[0].spec.colors
    assert colors['canvas'] == '#EFF3F9'
    assert colors['header'] == colors['heading'] == colors['on_primary_soft'] == '#183153'
    assert colors['primary'] == '#087F83'
    assert colors['accent'] == colors['focus'] == '#6545AD'
    assert colors['danger'] == '#A12D46'
    assert colors['surface'] == '#FFFFFF'


def test_course_palette_keeps_readable_labels_and_fixed_white_gutters():
    assert all(contrast_ratio('#' + GRID_TEXT_COLOR, '#' + color) >= 4.5 for color in COURSE_COLORS)
    for style in COURSE_STYLES:
        assert contrast_ratio('#' + style.accent, '#' + style.fill) >= 3
        assert contrast_ratio('#' + style.accent, COURSE_GUTTER) >= 3


def test_qss_resolved_and_assets_separate_from_color_values():
    assert '$' not in STYLESHEET
    assert set(COLORS) == set(COLOR_ROLES)
    for choice in builtin_themes():
        for name, path in trusted_assets(choice.spec).items():
            file = QFile(path)
            assert file.open(QIODevice.OpenModeFlag.ReadOnly)
            data = bytes(file.readAll()).decode('ascii')
            assert data.startswith('<svg')
            if name.startswith('sort_'):
                assert choice.spec.colors['on_header'].lower() in data.lower()


def test_direct_theme_construction_detaches_color_dictionary():
    source = dict(builtin_themes()[0].spec.colors)
    spec = ThemeSpec('Detached', 'light', source)
    source['canvas'] = '#000000'
    assert spec.colors['canvas'] == '#EFF3F9'
    with pytest.raises(TypeError):
        spec.colors['canvas'] = '#000000'
    with pytest.raises(FrozenInstanceError):
        spec.name = 'Changed'
