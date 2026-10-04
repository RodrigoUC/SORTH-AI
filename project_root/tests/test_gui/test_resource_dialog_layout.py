"""Resource drafts stay readable, reachable and unchanged by presentation."""
from dataclasses import replace
from pathlib import Path
import re
import time

import pytest
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QStyleFactory,
                             QStyle, QStyleOptionButton, QStyleOptionFrame, QListWidget, QLabel)

from src.gui.i18n import language_manager
from src.gui.resource_dialog import ResourceEditor, ResourceDialog, _ResourceFormDialog
from src.gui.theme import builtin_themes, theme_manager
from src.gui.theme_contract import load_theme_file
from src.scheduling.teaching_resources import Resource, ResourceCatalog
from src.scheduling.time_model import TimeModel
from tests.test_scheduling.test_teaching_resources import data


CUSTOM = load_theme_file(Path(__file__).resolve().parents[3] /
    '.agents/skills/sorth-theme-designer/assets/midnight-dark.sorth-theme.json')
LARGE_FONT = 'QPushButton, QCheckBox, QLabel, QLineEdit, QComboBox, QTableWidget, QListWidget, QHeaderView { font-size: 20pt; }'


def settle(dialog):
    previous = None
    stable = 0
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        QApplication.processEvents()
        snapshot = (dialog.size(), dialog.scroll.viewport().size(),
                    dialog.scroll.widget().size(), dialog.buttons.size())
        timers = [dialog._focus_reveal_timer, dialog._responsive_actions.timer,
                  dialog.buttons._metric_timer]
        stable = stable + 1 if snapshot == previous and not any(t.isActive() for t in timers) else 0
        if stable >= 2:
            return
        previous = snapshot
        QTest.qWait(1)
    pytest.fail('Resource native layout did not settle')


@pytest.fixture
def presentation():
    app = QApplication.instance()
    manager = theme_manager()
    original = (app.style().objectName(), language_manager().language, manager.current)
    yield app, manager
    app.setStyle(original[0])
    language_manager().set_language(original[1], persist=False)
    manager._apply(original[2])


def resource():
    return Resource('synthetic-resource', ('Guardar ' + 'alias largo ' * 8).strip(),
                    ((1, 480, 600), (2, 600, 720)))


def assert_compact(dialog):
    assert dialog.size() == QSize(460, 420)
    assert dialog.scroll.horizontalScrollBar().maximum() == 0
    assert dialog.scroll.viewport().height() >= 200
    for button in dialog.buttons.buttons():
        assert button.isVisible()
        assert button.width() >= button.minimumSizeHint().width()
        assert button.height() >= button.minimumSizeHint().height()
        assert dialog.rect().contains(button.mapTo(dialog, button.rect().topLeft()))
        assert dialog.rect().contains(button.mapTo(dialog, button.rect().bottomRight()))
    for action in dialog._responsive_actions.controls:
        if action.isHidden():
            continue
        assert action.width() >= action.minimumSizeHint().width()
        assert action.height() >= action.minimumSizeHint().height()
        source = action._messages['setText'][1][0].render()
        assert re.fullmatch(r'\s*'.join(re.escape(part) for part in action.text().split('\n')), source)
        assert action.accessibleName() == source


@pytest.mark.parametrize('kind', ['editor', 'catalog'])
@pytest.mark.parametrize('style_name', ['native-default', 'Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('large', [False, True])
@pytest.mark.parametrize('spec', [builtin_themes()[0].spec, builtin_themes()[1].spec, CUSTOM],
                         ids=['light', 'dark', 'custom'])
def test_resource_controls_fit_compact_native_metrics(presentation, kind, style_name, locale, large, spec):
    app, manager = presentation
    if style_name != 'native-default':
        if style_name not in QStyleFactory.keys():
            pytest.skip(f'{style_name} unavailable')
        app.setStyle(style_name)
    manager._apply(spec)
    language_manager().set_language(locale, persist=False)
    original = resource()
    catalog = ResourceCatalog('teacher', True, (original,))
    dialog = (ResourceEditor(original, TimeModel.default()) if kind == 'editor'
              else ResourceDialog(catalog, data()[1], TimeModel.default()))
    if large:
        dialog.setStyleSheet(LARGE_FONT)
    dialog.resize(460, 420)
    dialog.show()
    settle(dialog)
    assert_compact(dialog)
    if kind == 'editor':
        assert dialog.label.text() == original.label
        for row in range(dialog.windows.rowCount()):
            for column in range(3):
                control = dialog.windows.cellWidget(row, column)
                assert control.height() >= control.minimumSizeHint().height()
                assert control.width() >= control.minimumSizeHint().width()
            # The entire HH:mm input remains available even when the table scrolls.
            time_edit = dialog.windows.cellWidget(row, 1)
            assert time_edit.width() >= time_edit.fontMetrics().horizontalAdvance('00:00') + 6
        checkbox = dialog.declared
        for focused in [checkbox, dialog.label, checkbox]:
            focused.setFocus()
            settle(dialog)
            option = QStyleOptionButton()
            checkbox.initStyleOption(option)
            text_size = checkbox.style().itemTextRect(checkbox.fontMetrics(), QRect(),
                Qt.TextFlag.TextShowMnemonic, False, checkbox.text()).size()
            native = checkbox.style().sizeFromContents(QStyle.ContentsType.CT_CheckBox,
                                                       option, text_size, checkbox)
            contents = checkbox.style().subElementRect(QStyle.SubElement.SE_CheckBoxContents,
                                                       option, checkbox)
            assert checkbox.height() >= native.height()
            assert contents.height() >= text_size.height()
        dialog._submit()
        assert dialog.result_resource == original
    else:
        assert dialog.list.item(0).toolTip() == dialog.list.item(0).text()
        assert dialog.list.minimumHeight() >= 100
        assert dialog.sessions.minimumHeight() >= 160
        assert dialog.sessions.rowHeight(0) >= dialog.sessions.fontMetrics().height()
        for column in range(3):
            assert dialog.sessions.columnWidth(column) >= dialog.sessions.horizontalHeader().sectionSizeHint(column)
        dialog._submit()
        assert dialog.result_catalog == catalog
    dialog.close()


@pytest.mark.parametrize('save', [False, True], ids=['cancel', 'save'])
@pytest.mark.parametrize('kind', ['teacher', 'student_group', 'student'])
@pytest.mark.parametrize('locale', ['es', 'en'])
def test_resource_chooser_long_session_keeps_footer_and_keyboard(presentation, monkeypatch, kind, locale, save):
    language_manager().set_language(locale, persist=False)
    groups = data()[1]
    groups[0].group_id = 'SYNTHETIC-' + 'X' * 180
    original = ResourceCatalog(kind, True, (resource(),))
    parent = ResourceDialog(original, groups, TimeModel.default())
    parent.setStyleSheet(LARGE_FONT)
    parent.sessions.setCurrentCell(0, 0)
    def inspect(dialog):
        dialog.resize(460, 420)
        dialog.show()
        settle(dialog)
        assert_compact(dialog)
        labels = [label for label in dialog.findChildren(QLabel) if label.text() == groups[0].group_id]
        assert len(labels) == 1
        assert labels[0].textFormat() == Qt.TextFormat.PlainText
        choices = dialog.findChild(QListWidget)
        assert choices.item(0).toolTip() == choices.item(0).text()
        choices.setCurrentRow(0)
        choices.setFocus()
        QTest.keyClick(choices, Qt.Key.Key_Space)
        assert choices.item(0).checkState() == Qt.CheckState.Checked
        QTest.keyClick(choices, Qt.Key.Key_Tab)
        settle(dialog)
        assert QApplication.focusWidget() in dialog.buttons.buttons()
        button = dialog.buttons.button(QDialogButtonBox.StandardButton.Save if save
                                       else QDialogButtonBox.StandardButton.Cancel)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        return dialog.result()
    monkeypatch.setattr(_ResourceFormDialog, 'exec', inspect)
    parent._choose()
    expected = {groups[0].group_id: (resource().id,)} if save else {}
    assert parent.memberships == expected
    assert parent.result_catalog is None
    parent._submit()
    assert dict(parent.result_catalog.memberships) == expected
    reopened = ResourceDialog(parent.result_catalog, groups, TimeModel.default())
    assert reopened.memberships == expected
    assert original.memberships == ()
    reopened.reject()
    parent.reject()


@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('backwards', [False, True], ids=['Tab', 'Shift-Tab'])
def test_availability_keyboard_order_after_add_remove_and_validation(presentation, locale, backwards):
    language_manager().set_language(locale, persist=False)
    original = resource()
    dialog = ResourceEditor(original, TimeModel.default())
    dialog.setStyleSheet(LARGE_FONT)
    dialog.resize(460, 420)
    dialog.show()
    for repeat in range(3):
        dialog._add_window((3, 900, 960))
        dialog.windows.setCurrentCell(1, 0)
        dialog._remove_window()
        settle(dialog)
        dialog.label.setFocus()
        seen = []
        modifiers = Qt.KeyboardModifier.ShiftModifier if backwards else Qt.KeyboardModifier.NoModifier
        for _ in range(40):
            QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab, modifiers)
            settle(dialog)
            focused = QApplication.focusWidget()
            assert focused is not None and focused.isVisible()
            if focused is dialog.label:
                break
            seen.append(focused)
            if dialog.scroll.widget().isAncestorOf(focused):
                assert dialog.scroll.viewport().rect().contains(
                    focused.mapTo(dialog.scroll.viewport(), focused.rect().center()))
                if focused in [dialog.windows.cellWidget(row, col)
                               for row in range(dialog.windows.rowCount()) for col in range(3)]:
                    for viewport in [dialog.windows.viewport(), dialog.scroll.viewport()]:
                        assert viewport.rect().contains(focused.mapTo(viewport, focused.rect().topLeft()))
                        assert viewport.rect().contains(focused.mapTo(viewport, focused.rect().bottomRight()))
        else:
            pytest.fail('Resource keyboard loop did not return to Name')
        controls = [dialog.declared, dialog.windows]
        controls.extend(dialog.windows.cellWidget(row, col)
                        for row in range(dialog.windows.rowCount()) for col in range(3))
        controls.extend([dialog.add, dialog.remove, *dialog.buttons.buttons()])
        assert set(controls) <= set(seen)
        if not backwards:
            assert [widget for widget in seen if widget in controls] == controls
    dialog.windows.cellWidget(0, 1).setText('invalid')
    dialog._submit()
    settle(dialog)
    assert dialog.result_resource is None
    assert dialog.error.hasFocus() and dialog.error.isVisible()
    assert dialog.error.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByKeyboard
    assert dialog.scroll.viewport().rect().contains(dialog.error.mapTo(dialog.scroll.viewport(), dialog.error.rect().center()))
    assert_compact(dialog)
    dialog.reject()
    reopened = ResourceEditor(original, TimeModel.default())
    reopened._submit()
    assert reopened.result_resource == original


def test_catalog_retranslation_preserves_current_items_and_scroll(presentation):
    resources = tuple(Resource(f'id-{i}', f'Guardar alias {i} ' + 'x' * 70) for i in range(40))
    dialog = ResourceDialog(ResourceCatalog('teacher', True, resources), data()[1], TimeModel.default())
    dialog.resize(460, 420)
    dialog.show()
    settle(dialog)
    dialog.list.setCurrentRow(7)
    dialog.list.setFocus()
    dialog.list.verticalScrollBar().setValue(20)
    dialog.list.horizontalScrollBar().setValue(30)
    item = dialog.list.currentItem()
    scroll = (dialog.list.verticalScrollBar().value(), dialog.list.horizontalScrollBar().value())
    for locale in ['en', 'es', 'en']:
        language_manager().set_language(locale, persist=False)
        settle(dialog)
        assert dialog.list.currentItem() is item
        assert dialog.list.hasFocus()
        assert dialog.list.currentRow() == 7
        assert (dialog.list.verticalScrollBar().value(), dialog.list.horizontalScrollBar().value()) == scroll
        assert 'Guardar alias 7' in item.text()
    dialog.reject()


@pytest.mark.parametrize('style_name', ['Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('large', [False, True])
def test_name_focus_keeps_fresh_native_text_height(presentation, style_name, locale, large):
    app, _ = presentation
    app.setStyle(style_name)
    language_manager().set_language(locale, persist=False)
    dialog = ResourceEditor(resource(), TimeModel.default())
    if large:
        dialog.setStyleSheet(LARGE_FONT)
    dialog.resize(460, 420)
    dialog.show()
    settle(dialog)
    heights = []
    for target in [dialog.label, dialog.declared, dialog.label]:
        target.setFocus()
        settle(dialog)
        option = QStyleOptionFrame()
        dialog.label.initStyleOption(option)
        text_size = dialog.label.fontMetrics().size(Qt.TextFlag.TextSingleLine, 'Alias')
        native = dialog.label.style().sizeFromContents(QStyle.ContentsType.CT_LineEdit,
                                                       option, text_size, dialog.label)
        heights.append(native.height())
        assert dialog.label.height() >= native.height()
    assert len(set(heights)) == 1
    dialog.reject()


@pytest.mark.parametrize('kind', ['editor', 'catalog'])
def test_resize_retranslation_preserves_resource_draft(presentation, kind):
    original = resource()
    catalog = ResourceCatalog('teacher', True, (original,))
    dialog = (ResourceEditor(original, TimeModel.default()) if kind == 'editor'
              else ResourceDialog(catalog, data()[1], TimeModel.default()))
    dialog.setStyleSheet(LARGE_FONT)
    dialog.show()
    if kind == 'editor':
        dialog.label.setText('Draft alias')
        dialog.windows.cellWidget(0, 1).setText('09:15')
        control = dialog.label
    else:
        dialog.list.setCurrentRow(0)
        dialog.resources[0] = replace(original, label='Draft alias')
        dialog._refresh()
        control = dialog.list
    control.setFocus()
    for size, locale in [((460, 420), 'en'), ((960, 720), 'es'), ((460, 420), 'es'),
                         ((960, 720), 'en'), ((460, 420), 'en')]:
        dialog.resize(*size)
        language_manager().set_language(locale, persist=False)
        settle(dialog)
        assert control.hasFocus()
        assert dialog.size() == QSize(*size)
        assert dialog.scroll.horizontalScrollBar().maximum() == 0
        if size == (460, 420):
            assert_compact(dialog)
        if kind == 'editor':
            assert dialog.label.text() == 'Draft alias'
            assert dialog.windows.cellWidget(0, 1).text() == '09:15'
        else:
            assert dialog.list.currentRow() == 0
            assert 'Draft alias' in dialog.list.currentItem().text()
    dialog.reject()
    assert catalog.resources == (original,)
