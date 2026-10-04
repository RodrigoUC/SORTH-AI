from copy import deepcopy
import pytest
from PyQt6.QtCore import QSettings, Qt, QItemSelectionModel
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.gui.main_window import MainWindow
from src.gui.bulk_course_dialog import BulkCourseDialog
from src.gui.i18n import language_manager
from src.application.edit_history import fingerprint
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def window(tmp_path):
    settings = QSettings(str(tmp_path/'prefs.ini'), QSettings.Format.IniFormat)
    for key in ('undo_redo', 'bulk_operations'):
        settings.setValue('features/'+key, True)
    w = MainWindow(SessionRepository(str(tmp_path/'session.db')), restore_session=False, feature_settings=settings)
    w._classrooms = {'R': Classroom('R', 50, 'REGULAR')}
    w.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR', size=10),
        Course('CHEM', 1, 60, 'REGULAR', size=20), Course('OTHER', 1, 60, 'REGULAR', size=40)])
    w.show()
    yield w
    language_manager().set_language('es', persist=False)
    w._unsaved = False
    w.close()


def select(window, codes):
    table = window.course_manager.table
    table.clearSelection()
    for row in range(table.rowCount()):
        if table.item(row, 0).data(Qt.ItemDataRole.UserRole) in codes:
            table.selectionModel().select(table.model().index(row, 0),
                QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)


def test_filtered_sorted_selection_only_explicit_fields_and_single_undo(window):
    manager = window.course_manager
    manager.table.sortItems(0, Qt.SortOrder.DescendingOrder)
    select(window, ('BIO', 'CHEM', 'OTHER'))
    manager._search.setText('BIO')
    assert manager.selected_course_codes() == ('BIO',)
    before = fingerprint(window._capture_edit_state())
    dialog = BulkCourseDialog(window)
    assert not any(c.isChecked() for c in dialog.checks.values())
    dialog.checks['size'].setChecked(True)
    dialog.inputs['size'].setValue(25)
    dialog._review()
    assert dialog.plan.selected_codes == ('BIO',) and dialog.apply.isEnabled()
    dialog._apply()
    assert window.course_manager.courses[0].size == 25
    assert window.course_manager.courses[1].size == 20
    assert window._travel_history(True)
    assert fingerprint(window._capture_edit_state()) == before


def test_mixed_preview_refresh_clear_day_cancel_and_failed_save(window, monkeypatch):
    select(window, ('BIO', 'CHEM'))
    before = fingerprint(window._capture_edit_state())
    dialog = BulkCourseDialog(window)
    assert 'Valores mezclados' in ' '.join(label.text() for label in dialog.findChildren(type(dialog.impact)))
    dialog.checks['size'].setChecked(True)
    dialog.inputs['size'].setValue(30)
    dialog._review()
    assert len(dialog.plan.changes) == 2
    dialog.inputs['size'].setValue(35)
    assert dialog.plan is None and not dialog.apply.isEnabled()
    dialog._review()
    monkeypatch.setattr(window._repo, 'save_session', lambda **k: (_ for _ in ()).throw(OSError('full')))
    dialog._apply()
    assert dialog.error.text() and fingerprint(window._capture_edit_state()) == before
    assert not window._history.can_undo
    dialog.reject()
    assert fingerprint(window._capture_edit_state()) == before


def test_stale_selection_settings_dependency_and_locales(window):
    select(window, ('BIO', 'CHEM'))
    dialog = BulkCourseDialog(window)
    dialog.checks['size'].setChecked(True)
    dialog.inputs['size'].setValue(30)
    dialog._review()
    select(window, ('BIO',))
    dialog._apply()
    assert 'selección cambió' in dialog.error.text()
    values = window._features.values()
    values['undo_redo'] = False
    window._features.save(values)
    window._apply_feature_preferences()
    assert not window.btn_bulk.isHidden() and not window.btn_bulk.isEnabled()
    dialog.reject()
    language_manager().set_language('en', persist=False)
    other = BulkCourseDialog(window)
    assert other.windowTitle() == 'Edit courses in bulk'
    assert other.inputs['preferred_day'].itemText(0) == 'Clear preference'
    assert other.table.accessibleName()
    other.reject()


def test_preview_language_change_invalidates_and_clear_preference_is_explicit(window):
    window.course_manager.courses[0].preferred_day = 'Lunes'
    select(window, ('BIO',))
    dialog = BulkCourseDialog(window)
    dialog.checks['preferred_day'].setChecked(True)
    dialog.inputs['preferred_day'].setCurrentIndex(0)
    dialog._review()
    assert dialog.plan.changes == (('BIO', 'preferred_day', 'Lunes', None),)
    language_manager().set_language('en', persist=False)
    assert dialog.plan is None and not dialog.apply.isEnabled()
    dialog._review()
    dialog._apply()
    assert window.course_manager.courses[0].preferred_day is None
    assert window._travel_history(True)
    assert window.course_manager.courses[0].preferred_day == 'Lunes'


def test_bulk_render_failure_retains_accepted_state_and_preview(window, monkeypatch):
    select(window, ('BIO', 'CHEM'))
    before = fingerprint(window._capture_edit_state())
    before_db = fingerprint(window._repo.load_session())
    dialog = BulkCourseDialog(window)
    dialog.checks['size'].setChecked(True)
    dialog.inputs['size'].setValue(30)
    dialog._review()
    original = window._display_edit_state
    calls = []
    def fail_once(state):
        calls.append(1)
        original(state)
        if len(calls) == 1:
            raise RuntimeError('injected bulk view failure')
    monkeypatch.setattr(window, '_display_edit_state', fail_once)
    dialog._apply()
    assert dialog.error.text() and dialog.plan is not None
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == before_db
    assert not window._history.can_undo
    dialog.reject()


def test_multiselection_is_retained_after_bulk_and_failed_presentation_is_durable(window, monkeypatch):
    select(window, ('BIO', 'CHEM'))
    dialog = BulkCourseDialog(window)
    dialog.checks['size'].setChecked(True)
    dialog.inputs['size'].setValue(30)
    dialog._review()
    monkeypatch.setattr(dialog, 'accept', lambda: (_ for _ in ()).throw(RuntimeError('dialog close failed')))
    dialog._apply()
    assert window.course_manager.selected_course_codes() == ('BIO', 'CHEM')
    assert [c.size for c in window._repo.load_session()['courses']][:2] == [30, 30]
    assert window._history.can_undo and window._restore_failed
    assert 'se guardó' in window.status_bar.currentMessage()
    dialog.reject()


def test_bulk_action_tracks_filtered_selection_with_deselected_current_row(window):
    manager = window.course_manager
    table = manager.table
    window.tabs.setCurrentWidget(manager)
    QApplication.processEvents()
    def click(code, modifiers=Qt.KeyboardModifier.NoModifier):
        item = next(table.item(row, 0) for row in range(table.rowCount())
                    if table.item(row, 0).data(Qt.ItemDataRole.UserRole) == code)
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, modifiers,
                         table.visualItemRect(item).center())
        QApplication.processEvents()
    click('BIO')
    click('CHEM', Qt.KeyboardModifier.ControlModifier)
    click('CHEM', Qt.KeyboardModifier.ControlModifier)
    assert manager.selected_course_codes() == ('BIO',)
    assert table.currentItem().data(Qt.ItemDataRole.UserRole) == 'CHEM'
    assert not table.currentItem().isSelected()
    assert window.btn_bulk.isEnabled()
    manager._search.setText('CHEM')
    assert manager.selected_course_codes() == ()
    assert not window.btn_bulk.isEnabled()
    manager._search.clear()
    assert manager.selected_course_codes() == ('BIO',)
    assert window.btn_bulk.isEnabled()
