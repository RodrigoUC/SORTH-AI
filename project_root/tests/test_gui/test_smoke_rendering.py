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


@pytest.mark.parametrize('style_name', [None, 'Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('font_points', [10, 20])
def test_capture_settles_busy_and_localized_action_captions(tmp_path, style_name, locale, font_points):
    """Reproduce the short busy/ES widths used by the formerly clipped PNGs."""
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QHBoxLayout, QStyleFactory
    from src.gui.i18n import language_manager, msg
    from src.gui.i18n_widgets import QPushButton
    from src.gui.theme import builtin_themes, stylesheet_for
    app = QApplication.instance()
    previous_style = app.style().objectName()
    manager = language_manager()
    previous_locale = manager.language
    host = QWidget()
    timer = QTimer(host)
    timer.setSingleShot(True)
    callbacks = []
    timer.timeout.connect(lambda: callbacks.append('timer'))
    try:
        if style_name:
            app.setStyle(QStyleFactory.create(style_name))
        manager.set_language('es', persist=False)
        row = QHBoxLayout(host)
        row.addStretch()
        generate = QPushButton(msg('Generando…'))
        generate.setObjectName('primaryAction')
        add = QPushButton(msg('Agregar aula'))
        export = QPushButton(msg('Exportar filtrado ({p1})', p1=0))
        for button in (generate, add, export):
            row.addWidget(button)
        host.show()
        # Test each palette through repeated compact/wide transitions; the
        # helper must preserve fonts and source captions, not resize to fit.
        for choice in builtin_themes():
            host.setStyleSheet(stylesheet_for(choice.spec) +
                              f'\nQPushButton {{ font-size: {font_points}pt; }}')
            for width in (1200, 960, 1200):
                host.resize(width, 120)
                manager.set_language('es', persist=False)
                generate.setText(msg('Generando…'))
                export.setText(msg('Exportar filtrado ({p1})', p1=0))
                smoke_rendering.settle_capture_layout(host)
                old_width = generate.width()
                generate.setText(msg('Generar horario'))
                export.setText(msg('Exportar filtrado ({p1})', p1=42))
                manager.set_language(locale, persist=False)
                assert generate.width() == old_width
                assert any(not entry['fits'] for entry in smoke_rendering._action_geometry(host))
                fonts = [button.font().toString() for button in (generate, add, export)]
                captions = [button.text() for button in (generate, add, export)]
                window_size = host.size()
                timer.start(0)
                smoke_rendering.settle_capture_layout(host)
                assert all(entry['fits'] for entry in smoke_rendering._action_geometry(host))
                assert [button.font().toString() for button in (generate, add, export)] == fonts
                assert [button.text() for button in (generate, add, export)] == captions
                assert host.size() == window_size
                assert callbacks == [] and timer.isActive()
                timer.stop()
        report = smoke_rendering.require_readable_text(host, tmp_path, 'actions')
        assert report['actions'] and all(entry['fits'] for entry in report['actions'])
    finally:
        timer.stop()
        host.close()
        host.deleteLater()
        manager.set_language(previous_locale, persist=False)
        app.setStyle(QStyleFactory.create(previous_style))


def test_capture_rejects_a_genuinely_clipped_action(window, tmp_path):
    from PyQt6.QtWidgets import QPushButton
    button = QPushButton('Generate schedule', window)
    button.setFixedSize(30, 30)
    button.show()
    with pytest.raises(RuntimeError, match='action caption does not fit'):
        smoke_rendering.require_readable_text(window, tmp_path, 'clipped')
    report = json.loads((tmp_path / 'text-rendering-clipped.json').read_text())
    assert report['ok'] is False and report['actions'][0]['fits'] is False
    assert not (tmp_path / 'text-rendering-clipped.png').exists()


def test_capture_rejects_unstable_layout(window, monkeypatch):
    states = iter(range(18))
    monkeypatch.setattr(smoke_rendering, '_layout_signature', lambda _: next(states))
    with pytest.raises(RuntimeError, match='capture layout did not settle'):
        smoke_rendering.settle_capture_layout(window)


@pytest.mark.parametrize('style_name', ['Fusion', 'Windows'])
@pytest.mark.parametrize('adornment', ['menu', 'icon', 'both'])
@pytest.mark.parametrize('themed', [False, True])
def test_action_guard_reserves_menu_and_icon_space(window, tmp_path, style_name, adornment, themed):
    from PyQt6.QtGui import QIcon, QPixmap
    from PyQt6.QtWidgets import QApplication, QMenu, QPushButton, QStyleFactory, QVBoxLayout
    from src.gui.theme import builtin_themes, stylesheet_for
    app = QApplication.instance()
    previous_style = app.style().objectName()
    try:
        app.setStyle(QStyleFactory.create(style_name))
        if themed:
            window.setStyleSheet(stylesheet_for(builtin_themes()[0].spec))
        layout = QVBoxLayout(window)
        button = QPushButton('Schedule tools (F7)')
        if adornment in ('menu', 'both'):
            button.setMenu(QMenu(button))
        if adornment in ('icon', 'both'):
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.blue)
            button.setIcon(QIcon(pixmap))
        layout.addWidget(button)
        button.show()
        smoke_rendering.settle_capture_layout(window)
        natural = smoke_rendering._action_geometry(window)[0]
        assert natural['fits']
        # Leave room for bare text/chrome but not the actual menu/icon. The old
        # content-only assertion accepted this visibly clipped native button.
        chrome = button.width() - natural['content_size'][0]
        button.setFixedWidth(chrome + natural['text_size'][0])
        smoke_rendering.settle_capture_layout(window)
        clipped = smoke_rendering._action_geometry(window)[0]
        assert clipped['content_size'][0] >= clipped['text_size'][0]
        assert clipped['required_native_size'][0] > button.width()
        assert not clipped['fits']
        with pytest.raises(RuntimeError, match='action caption does not fit'):
            smoke_rendering.require_readable_text(window, tmp_path, 'adorned')
    finally:
        app.setStyle(QStyleFactory.create(previous_style))
