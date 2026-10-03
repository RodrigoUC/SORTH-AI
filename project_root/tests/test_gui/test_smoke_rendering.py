"""Visual smoke must reject tofu and blank rendering, not just nonempty PNGs."""
import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QWidget
import pytest

from src.gui import smoke_rendering


@pytest.fixture
def window():
    widget = QWidget()
    widget.show()
    yield widget
    widget.close()


def test_live_font_and_raster_evidence(window, tmp_path):
    report = smoke_rendering.require_readable_text(window, tmp_path, 'test')
    assert report['ok'] and report['family_count'] > 0
    assert all(not font['missing_characters'] and font['distinct_probe_rasters'] == 3
               and all(font['probe_ink_pixels']) for font in report['fonts'])
    assert not QImage(str(tmp_path / report['raster_image'])).isNull()
    assert json.loads((tmp_path / 'text-rendering-test.json').read_text()) == report


@pytest.mark.parametrize('failure', ['empty_database', 'missing_glyph', 'tofu', 'blank', 'save'])
def test_visual_guard_fails_closed_with_diagnostics(window, tmp_path, monkeypatch, failure):
    if failure == 'empty_database':
        monkeypatch.setattr(smoke_rendering.QFontDatabase, 'families', lambda: [])
    elif failure == 'missing_glyph':
        original = smoke_rendering.QFontMetrics
        class MissingAccent(original):
            def inFontUcs4(self, codepoint):
                return codepoint != ord('ñ') and super().inFontUcs4(codepoint)
        monkeypatch.setattr(smoke_rendering, 'QFontMetrics', MissingAccent)
    elif failure in ('tofu', 'blank'):
        def unreadable(font, text):
            image = QImage(32, 32, QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.white)
            return image, ('same-missing-glyph-box' if failure == 'tofu' else None), (20 if failure == 'tofu' else 0)
        monkeypatch.setattr(smoke_rendering, '_raster', unreadable)
    else:
        monkeypatch.setattr(smoke_rendering.QImage, 'save', lambda *args: False)
    with pytest.raises(RuntimeError):
        smoke_rendering.require_readable_text(window, tmp_path, 'failure')
    report = json.loads((tmp_path / 'text-rendering-failure.json').read_text())
    assert report['ok'] is False and report['error']
    assert not (tmp_path / 'text-rendering-failure.png').exists()
    if failure == 'missing_glyph':
        assert 'ñ' in report['fonts'][0]['missing_characters']


def test_windows_ci_discovers_fonts_without_packaging_them():
    root = Path(__file__).resolve().parents[3]
    workflow = (root / '.github/workflows/windows-review.yml').read_text()
    script = (root / 'project_root/tools/configure_windows_qt_fonts.ps1').read_text()
    assert workflow.index('configure_windows_qt_fonts.ps1') < workflow.index('Collect full regression inventory')
    assert '[Environment+SpecialFolder]::Fonts' in script
    assert 'QT_QPA_FONTDIR=$fontDir' in script
    assert '.ttf' in script and '.otf' in script
    assert '$fonts.Count -eq 0' in script and 'GITHUB_ENV' in script
    assert 'Copy-Item' not in script and 'Invoke-WebRequest' not in script
    assert 'text_rendering.$phase.ok' in workflow
    installer = (root / 'project_root/tools/test_installer.ps1').read_text()
    assert 'text_rendering.$phase.ok' in installer
    assert "$env:PYTHONPATH = $null" in workflow and "$env:PYTHONPATH = $null" in installer


def test_smoke_does_not_accept_captures_when_font_database_is_empty(tmp_path):
    import os
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[2]
    output = tmp_path / 'unreadable-smoke'
    script = '''
import sys
from src.gui import smoke_rendering
smoke_rendering.QFontDatabase.families = lambda: []
import gui_app
sys.argv = ['gui_app.py', '--smoke-test', '--smoke-output', sys.argv[1]]
gui_app.main()
'''
    child = subprocess.run([sys.executable, '-c', script, str(output)], cwd=root,
                           env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                           capture_output=True, text=True, timeout=30)
    assert child.returncode != 0
    report = json.loads((output / 'smoke-result.json').read_text())
    assert report['ok'] is False and report['stages'] == []
    assert 'font database is empty' in report['error']
    diagnostic = json.loads((output / 'text-rendering-startup.json').read_text())
    assert diagnostic['ok'] is False and diagnostic['family_count'] == 0
    assert not (output / 'schedule.png').exists()
