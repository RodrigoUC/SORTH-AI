"""Project catalog and comparison stay reachable at native compact sizes."""
from pathlib import Path
import re
import time

import pytest
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (QApplication, QLabel, QStyleFactory, QStyle, QStyleOptionButton)
from src.gui.i18n import language_manager
from src.gui.project_dialog import ProjectDialog, ComparisonDialog
from src.gui.theme import builtin_themes, theme_manager
from src.gui.theme_contract import load_theme_file
from src.application.scenario_comparison import compare_scenarios, scenario_metadata
from tests.test_gui.test_projects import window

CUSTOM = load_theme_file(Path(__file__).resolve().parents[3] /
    '.agents/skills/sorth-theme-designer/assets/midnight-dark.sorth-theme.json')
LARGE = 'QWidget { font-size: 20pt; }'


def settle(dialog):
    previous, stable = None, 0
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        QApplication.processEvents()
        snapshot = (dialog.size(), dialog.scroll.viewport().size(), dialog.scroll.widget().size(),
                    tuple((b.text(), b.size()) for b in getattr(dialog, 'buttons', {}).values()))
        timers = [dialog.close_buttons._metric_timer, dialog._focus_reveal_timer]
        if hasattr(dialog, '_responsive_actions'):
            timers.append(dialog._responsive_actions.timer)
        stable = stable + 1 if snapshot == previous and not any(t.isActive() for t in timers) else 0
        if stable >= 2:
            return
        previous = snapshot
        QTest.qWait(1)
    pytest.fail('Project native layout did not settle')


@pytest.fixture
def presentation():
    app, manager = QApplication.instance(), theme_manager()
    original = (app.style().objectName(), language_manager().language, manager.current)
    yield app, manager
    app.setStyle(original[0])
    language_manager().set_language(original[1], persist=False)
    manager._apply(original[2])


def comparison(window):
    left = window._repo.load_session()
    result = compare_scenarios((left, scenario_metadata('test')),
                              (dict(left, seed=(left['seed'] or 0) + 1), scenario_metadata('test')))
    return ComparisonDialog(window, {'name': 'Guardar ' + 'A' * 112}, {'name': 'Literal B'}, result)


def assert_compact(dialog):
    assert dialog.size() == QSize(460, 420)
    assert dialog.scroll.horizontalScrollBar().maximum() == 0
    assert dialog.scroll.viewport().height() >= 200
    for button in dialog.close_buttons.buttons():
        assert button.isVisible()
        assert button.width() >= button.minimumSizeHint().width()
        assert button.height() >= button.minimumSizeHint().height()
        assert dialog.rect().contains(button.mapTo(dialog, button.rect().topLeft()))
        assert dialog.rect().contains(button.mapTo(dialog, button.rect().bottomRight()))
    for label in dialog.scroll.widget().findChildren(QLabel):
        if label.wordWrap() and label.text():
            assert label.height() >= label.heightForWidth(label.width())
    assert dialog.table.viewport().height() >= dialog.table.rowHeight(0)
    for column in range(dialog.table.columnCount()):
        assert dialog.table.columnWidth(column) >= dialog.table.sizeHintForColumn(column)


@pytest.mark.parametrize('kind', ['catalog', 'comparison'])
@pytest.mark.parametrize('style_name', ['native-default', 'Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('large', [False, True])
@pytest.mark.parametrize('spec', [builtin_themes()[0].spec, builtin_themes()[1].spec, CUSTOM],
                         ids=['light', 'dark', 'custom'])
def test_project_content_fits_compact_native_metrics(window, presentation, kind, style_name, locale, large, spec):
    app, manager = presentation
    if style_name != 'native-default':
        if style_name not in QStyleFactory.keys():
            pytest.skip(f'{style_name} unavailable')
        app.setStyle(style_name)
    manager._apply(spec)
    language_manager().set_language(locale, persist=False)
    dialog = ProjectDialog(window) if kind == 'catalog' else comparison(window)
    if large:
        dialog.setStyleSheet(LARGE)
    dialog.resize(460, 420)
    dialog.show()
    settle(dialog)
    assert_compact(dialog)
    for button in [*getattr(dialog, 'buttons', {}).values(), *dialog.close_buttons.buttons()]:
        if button.isEnabled():
            button.setFocus()
        settle(dialog)
        option = QStyleOptionButton()
        option.initFrom(button)
        if button.autoDefault():
            option.features |= QStyleOptionButton.ButtonFeature.AutoDefaultButton
        if button.isDefault():
            option.features |= QStyleOptionButton.ButtonFeature.DefaultButton
        text_size = button.fontMetrics().size(Qt.TextFlag.TextShowMnemonic, button.text())
        native = button.style().sizeFromContents(QStyle.ContentsType.CT_PushButton, option, text_size, button)
        assert button.width() >= native.width()
        assert button.height() >= native.height()
        if button in getattr(dialog, 'buttons', {}).values():
            source = button._messages['setText'][1][0].render()
            assert re.fullmatch(r'\s*'.join(re.escape(part) for part in button.text().split('\n')), source)
            assert button.accessibleName() == source
    dialog.reject()


@pytest.mark.parametrize('kind', ['catalog', 'comparison'])
@pytest.mark.parametrize('backwards', [False, True], ids=['Tab', 'Shift-Tab'])
def test_project_keyboard_reveals_controls_and_keeps_footer(window, presentation, kind, backwards):
    dialog = ProjectDialog(window) if kind == 'catalog' else comparison(window)
    dialog.setStyleSheet(LARGE)
    dialog.resize(460, 420)
    dialog.show()
    if kind == 'catalog':
        dialog.table.selectRow(0)
    settle(dialog)
    dialog.table.setFocus()
    seen = []
    for _ in range(20):
        QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab,
                       Qt.KeyboardModifier.ShiftModifier if backwards else Qt.KeyboardModifier.NoModifier)
        settle(dialog)
        focused = QApplication.focusWidget()
        if focused is dialog.table:
            break
        seen.append(focused)
        if dialog.scroll.widget().isAncestorOf(focused):
            assert dialog.scroll.viewport().rect().contains(
                focused.mapTo(dialog.scroll.viewport(), focused.rect().center()))
    else:
        pytest.fail('Project keyboard did not return to table')
    expected = ([b for b in dialog.buttons.values() if b.isEnabled()] if kind == 'catalog'
                else [dialog._difference_detail])
    assert set(expected + dialog.close_buttons.buttons()) <= set(seen)
    assert_compact(dialog)
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Escape)
    assert not dialog.isVisible()


def test_project_reflow_preserves_selection_and_native_catalog_scroll(window, presentation):
    dialog = ProjectDialog(window)
    first = dialog.rows[0]
    for number in range(30):
        dialog.catalog.duplicate(first['id'], f'Literal {number:02} ' + 'X' * 90)
    dialog.refresh()
    dialog.resize(460, 420)
    dialog.show()
    settle(dialog)
    dialog.table.setCurrentCell(12, 1)
    dialog.table.selectRow(12)
    dialog.table.setFocus()
    dialog.table.verticalScrollBar().setValue(10)
    dialog.table.horizontalScrollBar().setValue(100)
    selected, current = dialog.selected(), dialog.table.currentItem()
    scroll = (dialog.table.verticalScrollBar().value(), dialog.table.horizontalScrollBar().value())
    for locale in ('en', 'es', 'en'):
        language_manager().set_language(locale, persist=False)
        settle(dialog)
        assert dialog.selected() == selected
        assert dialog.table.currentItem() is current
        assert dialog.table.hasFocus()
        assert (dialog.table.verticalScrollBar().value(), dialog.table.horizontalScrollBar().value()) == scroll
        assert_compact(dialog)
    dialog.resize(1400, 800)
    settle(dialog)
    assert all(row.direction() == row.Direction.LeftToRight for row in dialog._action_rows)
    assert all('\n' not in b.text() for b in dialog.buttons.values())
    dialog.resize(460, 420)
    settle(dialog)
    assert_compact(dialog)
    assert dialog.selected() == selected
    dialog.reject()


@pytest.mark.parametrize('compatible', [False, True])
def test_comparison_opens_at_readable_intro_and_keeps_incompatibility_notice(window, presentation, compatible):
    left = window._repo.load_session()
    metadata = scenario_metadata('test')
    other = metadata if compatible else dict(metadata, format_version=999)
    dialog = ComparisonDialog(window, {'name': 'A'}, {'name': 'B'},
                              compare_scenarios((left, metadata), (left, other)))
    dialog.setStyleSheet(LARGE)
    dialog.resize(460, 420)
    dialog.show()
    settle(dialog)
    assert dialog.scroll.verticalScrollBar().value() == 0
    labels = dialog.scroll.widget().findChildren(QLabel)
    assert labels[0].hasFocus()
    for label in labels:
        assert label.height() >= label.heightForWidth(label.width())
        assert label.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByKeyboard
    if not compatible:
        assert dialog.table.rowCount() == 0
        assert len(labels) == 3
    dialog.reject()


def test_project_error_is_revealed_without_changing_selection(window, presentation):
    import sqlite3
    dialog = ProjectDialog(window)
    dialog.setStyleSheet(LARGE)
    dialog.resize(460, 420)
    dialog.show()
    dialog.table.selectRow(0)
    before = dialog.selected()
    catalog = dialog.catalog.list_scenarios()
    def duplicate_name():
        raise sqlite3.IntegrityError('Synthetic duplicate')
    dialog._run(duplicate_name)
    settle(dialog)
    assert dialog.feedback.hasFocus()
    assert dialog.scroll.viewport().rect().contains(
        dialog.feedback.mapTo(dialog.scroll.viewport(), dialog.feedback.rect().center()))
    assert dialog.selected() == before
    assert dialog.catalog.list_scenarios() == catalog
    assert_compact(dialog)
    dialog.reject()


def test_project_name_draft_and_cancel_restore_invoker(window, presentation):
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QLineEdit, QDialogButtonBox
    from src.gui.project_dialog import ask_name
    from src.gui.i18n import msg
    parent = ProjectDialog(window)
    parent.setStyleSheet(LARGE)
    parent.resize(460, 420)
    parent.show()
    settle(parent)
    invoker = parent.buttons['new']
    invoker.setFocus()
    failures = []
    def inspect():
        dialog = QApplication.activeModalWidget()
        try:
            dialog.resize(460, 420)
            QApplication.processEvents()
            edit = dialog.findChild(QLineEdit)
            assert edit.hasFocus()
            QTest.keyClicks(edit, 'Literal draft')
            for locale in ('en', 'es'):
                language_manager().set_language(locale, persist=False)
                QApplication.processEvents()
                assert dialog.size() == QSize(460, 420)
                assert edit.text() == 'Literal draft'
                assert edit.hasFocus()
            QTest.keyClick(edit, Qt.Key.Key_Tab)
            assert QApplication.focusWidget() in dialog.findChild(QDialogButtonBox).buttons()
            QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Escape)
        except BaseException as error:
            failures.append(error)
        finally:
            dialog.reject()
    QTimer.singleShot(0, inspect)
    assert ask_name(parent, msg('Crear proyecto desde la sesión')) is None
    settle(parent)
    assert not failures
    # Offscreen can leave the owner inactive; preserve its remembered target.
    assert parent.focusWidget() is invoker
    parent.reject()


def test_comparison_locale_preserves_detail_selection_and_scroll(window, presentation):
    from PyQt6.QtGui import QTextCursor
    left = window._repo.load_session()
    result = compare_scenarios((left, scenario_metadata('test')),
                              (dict(left, seed=(left['seed'] or 0) + 1), scenario_metadata('test')))
    result['differences'].append('resources')
    result['difference_values']['resources'] = (
        [{'id': f'synthetic-{index}', 'label': 'Literal long alias ' * 12} for index in range(40)], [])
    dialog = ComparisonDialog(window, {'name': 'A'}, {'name': 'B'}, result)
    dialog.resize(460, 420)
    dialog.show()
    settle(dialog)
    detail = dialog._difference_detail
    detail.setFocus()
    cursor = detail.textCursor()
    cursor.setPosition(130)
    cursor.setPosition(155, QTextCursor.MoveMode.KeepAnchor)
    detail.setTextCursor(cursor)
    detail.verticalScrollBar().setValue(20)
    expected = (cursor.anchor(), cursor.position(), detail.verticalScrollBar().value())
    assert expected[2] == 20
    for locale, name in [('en', 'Different values (left / right)'),
                         ('es', 'Valores diferentes (izquierda / derecha)'),
                         ('en', 'Different values (left / right)')]:
        language_manager().set_language(locale, persist=False)
        settle(dialog)
        cursor = detail.textCursor()
        assert (cursor.anchor(), cursor.position(), detail.verticalScrollBar().value()) == expected
        assert detail.hasFocus()
        assert detail.accessibleName() == name
        assert 'Literal long alias' in detail.toPlainText()
    dialog.reject()
