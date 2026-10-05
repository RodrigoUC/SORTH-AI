"""Verify destructive import defaults after the actual modal is shown."""
import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialogButtonBox

from src.application.edit_history import encoded
from src.gui.i18n import language_manager
from src.gui.import_preview_dialog import ImportPreviewDialog
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources
from tests.test_gui.import_helpers import wait_for_import
from tests.test_gui.test_background_import import (
    enable_preview, session, window, workbook,
)


@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('action', [
    'return', 'escape', 'tab_back_return', 'click_replace', 'tab_replace_space',
])
def test_shown_preview_requires_explicit_replacement(
        window, tmp_path, monkeypatch, language, action):
    """Inspect the shown native buttons; constructor-only checks miss reparenting."""
    manager, previous_language = language_manager(), language_manager().language
    enable_preview(window)
    window.resources = SchedulingResources(tuple(
        ResourceCatalog(kind, True, (Resource(f"{kind}-synthetic", f"Synthetic {kind}"),),
                        (("BIO-G1", (f"{kind}-synthetic",)),))
        for kind in ("teacher", "student_group", "student")))
    assert window._save_session()
    resources = window.resources
    before = session(window)
    before_edit = encoded(window._capture_edit_state())
    before_history = encoded(vars(window._history))
    path = tmp_path / 'session.db'
    before_bytes = path.read_bytes()
    original_exec = ImportPreviewDialog.exec
    observed = []

    def review(dialog):
        def interact():
            # Store observations for assertions outside the Qt callback so a
            # failed regression cannot abort the interpreter or leave a modal.
            buttons = dialog.findChild(QDialogButtonBox)
            replace_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
            cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
            state = {
                'visible': dialog.isVisible(),
                'focus_details': QApplication.focusWidget() is dialog.details,
                'replace_default': replace_button.isDefault(),
                'cancel_default': cancel_button.isDefault(),
                'native_auto_defaults': (replace_button.autoDefault(), cancel_button.autoDefault()),
            }
            observed.append(state)
            if action in ('tab_back_return', 'tab_replace_space'):
                for _ in range(8):
                    if replace_button.hasFocus():
                        break
                    QTest.keyClick(QApplication.focusWidget() or dialog, Qt.Key.Key_Tab)
                state['replace_reached_by_tab'] = replace_button.hasFocus()
                state['focused_replace_default'] = replace_button.isDefault()
                if action == 'tab_back_return':
                    QTest.keyClick(replace_button, Qt.Key.Key_Backtab)
                    state['details_reached_by_backtab'] = QApplication.focusWidget() is dialog.details
                    state['cancel_default_after_backtab'] = cancel_button.isDefault()
                    QTest.keyClick(QApplication.focusWidget() or dialog, Qt.Key.Key_Return)
                else:
                    QTest.keyClick(replace_button, Qt.Key.Key_Space)
            elif action == 'click_replace':
                QTest.mouseClick(replace_button, Qt.MouseButton.LeftButton)
            else:
                QTest.keyClick(dialog.details, Qt.Key.Key_Return if action == 'return' else Qt.Key.Key_Escape)
            # A modal that ignores the key is not proof of the intended default.
            state['closed_by_action'] = not dialog.isVisible()
            if dialog.isVisible():
                dialog.reject()
        QTimer.singleShot(30, interact)
        return original_exec(dialog)

    monkeypatch.setattr(ImportPreviewDialog, 'exec', review)
    try:
        manager.set_language(language, persist=False)
        window.show()
        candidate = workbook(tmp_path / 'replacement.xlsx', count=2)
        window._import.start(candidate)
        wait_for_import(window)
        assert len(observed) == 1
        state = observed[0]
        assert state['visible'] and state['focus_details']
        assert state['cancel_default'] and not state['replace_default'], state
        assert state['native_auto_defaults'] == (True, True)
        assert state['closed_by_action']
        if action in ('tab_back_return', 'tab_replace_space'):
            assert state['replace_reached_by_tab'] and state['focused_replace_default']
        if action == 'tab_back_return':
            assert state['details_reached_by_backtab'] and state['cancel_default_after_backtab']
        if action in ('click_replace', 'tab_replace_space'):
            assert window.excel_path == candidate
            assert window.course_manager.get_courses()[0].number_of_groups == 2
            restored = SessionRepository(str(path)).load_session()
            assert restored['courses'][0].number_of_groups == 2
            assert restored['resources'].to_data() == resources.to_data()
            assert restored['pinned_group_ids'] == {'BIO-G1'}
            assert restored['assignments'] == {'BIO-G1': ('R', 1, 480, 540)}
            assert path.read_bytes() != before_bytes
        else:
            assert session(window) == before
            assert encoded(window._capture_edit_state()) == before_edit
            assert encoded(vars(window._history)) == before_history
            assert path.read_bytes() == before_bytes
    finally:
        manager.set_language(previous_language, persist=False)
