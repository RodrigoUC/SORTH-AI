"""Native appearance changes are presentation-only, bounded and commit-first."""
import json
from pathlib import Path
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem
from src.gui import theme
from src.gui.theme_contract import parse_theme
from src.gui.theme_preferences import ThemePreferences, ThemePersistenceError, MAX_PREFERENCE_BYTES
from src.gui import theme_preferences


@pytest.fixture
def manager(tmp_path, monkeypatch):
    app = QApplication.instance()
    old = theme.current_theme()
    old_prepared = theme.stylesheet_for(old), theme.palette_for(old)
    value = theme.ThemeManager(app, ThemePreferences(tmp_path / 'appearance.json'))
    monkeypatch.setattr(app, '_sorth_theme_manager', value, raising=False)
    yield value
    value._apply(old, prepared=old_prepared)
    value.deleteLater()


@pytest.mark.parametrize('choice', theme.builtin_themes(), ids=lambda x:x.key)
def test_palette_sets_all_color_groups(choice):
    palette = theme.palette_for(choice.spec)
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        assert palette.color(group, QPalette.ColorRole.Window).name() == choice.spec.colors['canvas'].lower()
        assert palette.color(group, QPalette.ColorRole.ToolTipText).name() == choice.spec.colors['on_header'].lower()
        assert palette.isBrushSet(group, QPalette.ColorRole.PlaceholderText)
        expected = 'disabled_text' if group == QPalette.ColorGroup.Disabled else 'on_accent'
        assert palette.color(group, QPalette.ColorRole.HighlightedText).name() == choice.spec.colors[expected].lower()


def test_preview_is_local_and_does_not_persist(manager):
    main, sample = QWidget(), QWidget()
    try:
        main.setObjectName('brandHeader')
        before = QApplication.instance().styleSheet(), theme.current_theme(), dict(theme.COLORS)
        theme.preview_theme(sample, theme.builtin_themes()[1].spec)
        assert before == (QApplication.instance().styleSheet(), theme.current_theme(), dict(theme.COLORS))
        assert not manager.preferences.path.exists()
        assert sample.palette().color(QPalette.ColorRole.Window).name() == '#131922'
        assert main.palette().color(QPalette.ColorRole.Window).name() == '#eff3f9'
    finally:
        main.close(); sample.close()


def test_switch_preserves_focus_editor_selection_and_scroll(manager):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    edit = QLineEdit('Uncommitted course name')
    table = QTableWidget(50, 2)
    for row in range(50):
        table.setItem(row, 0, QTableWidgetItem(str(row)))
    button = QPushButton('Disabled')
    button.setEnabled(False)
    layout.addWidget(edit); layout.addWidget(table); layout.addWidget(button)
    widget.resize(600, 400); widget.show()
    QApplication.processEvents()
    edit.setFocus(); edit.setSelection(2, 5)
    table.setCurrentCell(23, 0); table.verticalScrollBar().setValue(20)
    before = (edit.text(), edit.selectedText(), table.currentItem(), table.verticalScrollBar().value())
    changes = []
    edit.textChanged.connect(changes.append)
    for choice in (*theme.builtin_themes()[1:], theme.builtin_themes()[0]):
        manager.save_and_apply(choice.spec, choice.key)
        QApplication.processEvents()
        assert (edit.text(), edit.selectedText(), table.currentItem(), table.verticalScrollBar().value()) == before
        assert edit.hasFocus()
        assert not button.isEnabled()
    assert not changes
    widget.close()


def test_custom_saved_payload_survives_deleted_import_and_restart(manager, tmp_path):
    data = theme.builtin_themes()[1].spec.to_dict()
    data['name'] = 'Personal imported theme'
    imported = tmp_path / 'custom.sorth-theme.json'
    imported.write_text(json.dumps(data))
    spec = parse_theme(imported.read_bytes())
    manager.save_and_apply(spec)
    imported.unlink()
    reopened = ThemePreferences(manager.preferences.path)
    assert reopened.current_key == 'custom'
    assert reopened.current.to_dict() == spec.to_dict()
    assert not reopened.recovery_issue


@pytest.mark.parametrize('payload', [b'{broken', b'{"version":2}', b'x' * (MAX_PREFERENCE_BYTES + 50), b'{"version":1,"version":1}'])
def test_corrupt_preferences_remain_exact_until_explicit_recovery(tmp_path, payload):
    path = tmp_path / 'appearance.json'; path.write_bytes(payload)
    store = ThemePreferences(path)
    assert store.current_key == 'original'
    assert store.recovery_issue
    assert path.read_bytes() == payload
    choice = theme.builtin_themes()[1]
    with pytest.raises(ThemePersistenceError, match='explicit'):
        store.save(choice.spec, choice.key)
    assert path.read_bytes() == payload
    store.save(choice.spec, choice.key, recover=True)
    assert store.last_backup_path.read_bytes() == payload
    assert ThemePreferences(path).current_key == 'nocturno'
    assert not store.recovery_issue


@pytest.mark.parametrize('stage', ['open', 'short_write', 'commit'])
def test_atomic_failure_keeps_bytes_and_current_theme(manager, monkeypatch, stage):
    original = theme.builtin_themes()[0]
    manager.save_and_apply(original.spec, original.key)
    before = manager.preferences.path.read_bytes(), theme.current_theme(), QApplication.instance().styleSheet()
    real = theme_preferences.QSaveFile
    calls = []
    class FailingSaveFile:
        def __init__(self, path):
            self.file = real(path)
        def setDirectWriteFallback(self, value):
            calls.append(value); self.file.setDirectWriteFallback(value)
        def open(self, mode):
            return False if stage == 'open' else self.file.open(mode)
        def write(self, data):
            return self.file.write(data[:len(data)//2]) if stage == 'short_write' else self.file.write(data)
        def commit(self):
            return False if stage == 'commit' else self.file.commit()
        def cancelWriting(self):
            self.file.cancelWriting()
    monkeypatch.setattr(theme_preferences, 'QSaveFile', FailingSaveFile)
    choice = theme.builtin_themes()[1]
    with pytest.raises(ThemePersistenceError):
        manager.save_and_apply(choice.spec, choice.key)
    assert before == (manager.preferences.path.read_bytes(), theme.current_theme(), QApplication.instance().styleSheet())
    assert calls == [False]


def test_external_preference_change_is_not_overwritten(manager):
    choice = theme.builtin_themes()[1]
    other = ThemePreferences(manager.preferences.path)
    other.save(choice.spec, choice.key)
    before = manager.preferences.path.read_bytes()
    with pytest.raises(ThemePersistenceError, match='externally'):
        manager.save_and_apply(theme.builtin_themes()[0].spec, 'original')
    assert manager.preferences.path.read_bytes() == before
    assert manager.current_key == 'original'


def test_invalid_direct_spec_cannot_reach_live_stylesheet(manager):
    colors = dict(theme.builtin_themes()[0].spec.colors)
    colors['on_header'] = 'url(/tmp/arbitrary.svg)'
    spec = theme.ThemeSpec('Unsafe', 'light', colors)
    before = QApplication.instance().styleSheet()
    with pytest.raises(ValueError):
        manager.save_and_apply(spec)
    assert QApplication.instance().styleSheet() == before
    assert not manager.preferences.path.exists()


def test_save_does_not_touch_adjacent_optional_preferences(manager):
    other = manager.preferences.path.with_name('optional-features.json')
    original = b'{"version":1,"features":{"mcp_server":false}}\n'
    other.write_bytes(original)
    for choice in theme.builtin_themes():
        manager.save_and_apply(choice.spec, choice.key)
    assert other.read_bytes() == original


def test_main_theme_change_never_writes_domain_or_changes_other_preferences(manager, tmp_path, monkeypatch):
    from copy import deepcopy
    from PyQt6.QtCore import QSettings
    from src.gui.main_window import MainWindow
    from src.infrastructure.session_repository import SessionRepository
    from src.scheduling.course import Course
    from src.scheduling.classroom import Classroom
    from src.scheduling.group import Group
    from src.scheduling.time_model import TimeModel
    settings = QSettings(str(tmp_path / 'other.ini'), QSettings.Format.IniFormat)
    settings.setValue('interface/reduced_motion', True)
    settings.setValue('interface/language', 'es')
    settings.sync()
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')),
                        restore_session=False, feature_settings=settings)
    try:
        window._classrooms = {'A1': Classroom('A1', 30, 'REGULAR')}
        window.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR')])
        window.current_schedule = {'BIO-G1': ('A1', 1, 480, 540)}
        window.current_groups = [Group('BIO-G1', 60, 'REGULAR', course_code='BIO')]
        window.schedule_viewer.display_schedule(window.current_schedule, TimeModel.default(), window.current_groups)
        window._save_session()
        before_record = deepcopy(window._repo.load_session())
        before_bytes = Path(window._repo._db_path).read_bytes()
        before_flags = window._features.values()
        before_settings = Path(settings.fileName()).read_bytes()
        before_schedule = window.current_schedule
        before_courses = window.course_manager.get_courses()
        before_motion = window._motion.reduced
        def forbidden(*args, **kwargs):
            pytest.fail('Appearance must not persist or regenerate domain state')
        monkeypatch.setattr(window._repo, 'save_session', forbidden)
        monkeypatch.setattr(window, '_generate_schedule', forbidden)
        for choice in theme.builtin_themes():
            manager.save_and_apply(choice.spec, choice.key)
            QApplication.processEvents()
            assert window.current_schedule is before_schedule
            assert window.course_manager.get_courses() == before_courses
            assert window._features.values() == before_flags
            assert window._motion.reduced == before_motion
            assert Path(window._repo._db_path).read_bytes() == before_bytes
            assert Path(settings.fileName()).read_bytes() == before_settings
            assert window._repo.load_session()['assignments'] == before_record['assignments']
    finally:
        window.close()


def test_interface_theme_cannot_recolor_or_change_excel_csv_pdf_exports(manager, tmp_path):
    from io import BytesIO
    from zipfile import ZipFile
    from pypdf import PdfReader
    from src.infrastructure.schedule_exporter import ScheduleExporter
    from src.scheduling.time_model import TimeModel
    exporter = ScheduleExporter(TimeModel.default())
    assignments = {'BIO-G1': ('A1', 1, 480, 540), 'QUIL-G1': ('A1', 2, 600, 660)}
    results = []
    for choice in theme.builtin_themes():
        manager.save_and_apply(choice.spec, choice.key)
        csv = tmp_path / f'{choice.key}.csv'
        xlsx = tmp_path / f'{choice.key}.xlsx'
        pdf = tmp_path / f'{choice.key}.pdf'
        exporter.to_csv(assignments, str(csv))
        exporter.to_excel(assignments, str(xlsx))
        exporter.to_pdf(assignments, str(pdf))
        with ZipFile(xlsx) as archive:
            # Core creation timestamps are not appearance; all style/sheet XML is.
            xml = {name: archive.read(name) for name in archive.namelist()
                   if name.startswith('xl/') and name.endswith('.xml')}
        reader = PdfReader(pdf)
        results.append((csv.read_bytes(), xml, tuple(page.get_contents().get_data() for page in reader.pages)))
    assert results[0] == results[1] == results[2]


def test_reopening_reconciles_external_preferences_without_applying_or_writing(manager):
    other = ThemePreferences(manager.preferences.path)
    external = theme.builtin_themes()[1]
    other.save(external.spec, external.key)
    before_bytes = manager.preferences.path.read_bytes()
    with pytest.raises(ThemePersistenceError, match='externally'):
        manager.save_and_apply(theme.builtin_themes()[0].spec, 'original')
    assert manager.refresh_preferences()
    assert manager.preferences.path.read_bytes() == before_bytes
    assert manager.current_key == 'original'
    assert manager.preferences.current_key == 'nocturno'
    manager.save_and_apply(manager.preferences.current, manager.preferences.current_key)
    assert manager.current_key == 'nocturno'
    assert not manager.refresh_preferences()


def test_postcommit_refresh_failure_is_distinct_and_remaining_widgets_update(manager):
    class BrokenWidget(QWidget):
        def refresh_theme(self):
            raise OSError('injected paint failure')
    class HealthyWidget(QWidget):
        refreshed = False
        def refresh_theme(self):
            self.refreshed = True
    broken, healthy = BrokenWidget(), HealthyWidget()
    try:
        choice = theme.builtin_themes()[1]
        with pytest.raises(theme.ThemeApplicationError, match='was saved') as caught:
            manager.save_and_apply(choice.spec, choice.key)
        assert caught.value.saved_theme == choice.spec
        assert 'injected paint failure' in manager.application_issue
        assert healthy.refreshed
        assert manager.current_key == ThemePreferences(manager.preferences.path).current_key == 'nocturno'
        assert theme.current_theme() == choice.spec
    finally:
        broken.deleteLater(); healthy.deleteLater()
        from PyQt6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_icons_preview_and_startup_need_no_writable_temporary_directory(manager, tmp_path, monkeypatch):
    import tempfile
    def unavailable(*args, **kwargs):
        raise OSError('No writable temporary directory')
    monkeypatch.setattr(tempfile, 'TemporaryDirectory', unavailable)
    monkeypatch.setattr(tempfile, 'mkdtemp', unavailable)
    data = theme.builtin_themes()[1].spec.to_dict()
    data['name'] = 'Uncached in-memory arrows'
    data['colors']['on_header'] = '#F4F7FB'
    spec = parse_theme(json.dumps(data))
    sample = QWidget()
    try:
        theme.preview_theme(sample, spec)
        manager.save_and_apply(spec)
        reopened = ThemePreferences(manager.preferences.path)
        restarted = theme.ThemeManager(QApplication.instance(), reopened)
        assert restarted.current == spec
        assert theme.trusted_assets(spec)['sort_up'].startswith(':/sorth_theme_')
        restarted.deleteLater()
    finally:
        sample.close()


def test_preview_preparation_failure_does_not_partially_mutate_subtree(manager, monkeypatch):
    sample = QWidget()
    before = sample.palette(), sample.styleSheet(), sample.property('sorthThemePreview')
    def unavailable(spec):
        raise OSError('injected preparation failure')
    monkeypatch.setattr(theme, 'stylesheet_for', unavailable)
    with pytest.raises(OSError, match='preparation'):
        theme.preview_theme(sample, theme.builtin_themes()[1].spec)
    assert before == (sample.palette(), sample.styleSheet(), sample.property('sorthThemePreview'))
    sample.close()


def test_startup_preparation_failure_falls_back_without_rewriting_valid_record(manager, monkeypatch):
    choice = theme.builtin_themes()[1]
    manager.save_and_apply(choice.spec, choice.key)
    original_bytes = manager.preferences.path.read_bytes()
    def unavailable(spec):
        raise OSError('injected startup preparation failure')
    monkeypatch.setattr(theme, 'stylesheet_for', unavailable)
    restarted = theme.ThemeManager(QApplication.instance(), ThemePreferences(manager.preferences.path))
    assert restarted.current_key == 'original'
    assert restarted.startup_issue
    assert not restarted.recovery_issue
    assert restarted.preferences.current_key == 'nocturno'
    assert manager.preferences.path.read_bytes() == original_bytes
    restarted.deleteLater()
