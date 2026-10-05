"""Theme spin buttons must receive real pointer hits, not covered editor clicks."""
import pytest
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication, QAbstractSpinBox, QDateEdit, QDateTimeEdit, QDoubleSpinBox,
    QProxyStyle, QSpinBox, QStyle, QStyleFactory, QStyleOptionSpinBox, QTimeEdit,
    QDialogButtonBox,
)
from src.gui.dialogs import AddClassroomDialog
from src.gui.theme import builtin_themes, stylesheet_for
from src.gui.theme_contract import ThemeSpec


class HorizontalSpinStyle(QProxyStyle):
    """Exercise Win11-shaped native buttons on non-Windows CI too.

    Qt's Windows 11 style places two font-sized buttons side by side. The
    stylesheet's default edit-field calculation reserves only the widest one,
    leaving the up button under the QLineEdit. This proxy models that geometry,
    not native Windows painting or platform acceptance.
    Reference: qtbase/src/plugins/styles/modernwindows/qwindows11style.cpp,
    QWindows11Style::subControlRect (Qt 6.10).
    """
    def subControlRect(self, control, option, subcontrol, widget=None):
        if (control == QStyle.ComplexControl.CC_SpinBox
                and subcontrol in (QStyle.SubControl.SC_SpinBoxUp,
                                   QStyle.SubControl.SC_SpinBoxDown)):
            if option.buttonSymbols == QAbstractSpinBox.ButtonSymbols.NoButtons:
                return QRect()
            frame = self.pixelMetric(QStyle.PixelMetric.PM_SpinBoxFrameWidth,
                                     option, widget) if option.frame else 0
            height = min(option.rect.height() - 3 * frame,
                         option.fontMetrics.height() * 5 // 4)
            width = height * 6 // 5
            x = option.rect.right() - frame - 2 * width + 1
            if subcontrol == QStyle.SubControl.SC_SpinBoxDown:
                x += width
            return QRect(x, option.rect.y() + (option.rect.height() - height) // 2,
                         width, height)
        return super().subControlRect(control, option, subcontrol, widget)


# Native Windows CI picks up windows11/windowsvista automatically.
STYLES = list(QStyleFactory.keys()) + ['horizontal-proxy']
THEMES = [choice.spec for choice in builtin_themes()]
THEMES.append(ThemeSpec('Custom capacity test', THEMES[0].mode, dict(THEMES[0].colors)))


@pytest.fixture(params=STYLES)
def native_style(request):
    app = QApplication.instance()
    old_name, old_qss = app.style().objectName(), app.styleSheet()
    app.setStyleSheet('')
    style = HorizontalSpinStyle('Fusion') if request.param == 'horizontal-proxy' else QStyleFactory.create(request.param)
    app.setStyle(style)
    yield app
    app.setStyleSheet('')
    app.setStyle(old_name or 'Fusion')
    app.setStyleSheet(old_qss)


def button_rect(spin, subcontrol):
    option = QStyleOptionSpinBox()
    spin.initStyleOption(option)
    return spin.style().subControlRect(QStyle.ComplexControl.CC_SpinBox,
                                      option, subcontrol, spin)


def click_visible_button(spin, subcontrol):
    rect = button_rect(spin, subcontrol)
    assert rect.isValid() and spin.rect().contains(rect)
    # QTest.mouseClick(spin, ...) would bypass child interception and give a
    # false pass on the old horizontal geometry. Route to the actual receiver.
    receiver = spin.childAt(rect.center()) or spin
    QTest.mouseClick(receiver, Qt.MouseButton.LeftButton,
                     pos=receiver.mapFrom(spin, rect.center()))
    QApplication.processEvents()


@pytest.mark.parametrize('spec', THEMES, ids=lambda spec: spec.name)
@pytest.mark.parametrize('points', [10, 20])
def test_capacity_clicks_keyboard_and_bounds(native_style, spec, points):
    native_style.setStyleSheet(stylesheet_for(spec).replace('font-size: 10pt;', f'font-size: {points}pt;'))
    dialog = AddClassroomDialog(None)
    dialog.resize(460, 420)
    dialog.show()
    native_style.processEvents()
    spin = dialog.inp_capacity
    for focused in (False, True):
        (spin if focused else dialog.inp_code).setFocus()
        native_style.processEvents()
        spin.setValue(30)
        click_visible_button(spin, QStyle.SubControl.SC_SpinBoxUp)
        assert spin.value() == 31
        click_visible_button(spin, QStyle.SubControl.SC_SpinBoxDown)
        assert spin.value() == 30
        up = button_rect(spin, QStyle.SubControl.SC_SpinBoxUp)
        down = button_rect(spin, QStyle.SubControl.SC_SpinBoxDown)
        assert not up.intersects(down)
        assert not spin.lineEdit().geometry().intersects(up)
        assert not spin.lineEdit().geometry().intersects(down)
    for value, subcontrol in [(1, QStyle.SubControl.SC_SpinBoxDown),
                              (500, QStyle.SubControl.SC_SpinBoxUp)]:
        spin.setValue(value)
        click_visible_button(spin, subcontrol)
        assert spin.value() == value
    spin.setFocus()
    spin.selectAll()
    QTest.keyClicks(spin, '42')
    QTest.keyClick(spin, Qt.Key.Key_Up)
    assert spin.value() == 43
    QTest.keyClick(spin, Qt.Key.Key_Down)
    assert spin.value() == 42
    dialog.inp_code.setText('A-CAPACITY')
    dialog._on_accept()
    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.get_classroom().capacity == 42
    dialog.close()


@pytest.mark.parametrize('kind', [QSpinBox, QDoubleSpinBox, QTimeEdit, QDateEdit, QDateTimeEdit])
def test_shared_spin_controls_do_not_cover_buttons(native_style, kind):
    native_style.setStyleSheet(stylesheet_for(THEMES[0]))
    spin = kind()
    spin.resize(max(180, spin.sizeHint().width()), spin.sizeHint().height())
    spin.show()
    native_style.processEvents()
    for subcontrol in [QStyle.SubControl.SC_SpinBoxUp, QStyle.SubControl.SC_SpinBoxDown]:
        rect = button_rect(spin, subcontrol)
        assert not spin.lineEdit().geometry().intersects(rect)
        before = spin.text()
        # Stay away from the default numeric lower boundary.
        if isinstance(spin, (QSpinBox, QDoubleSpinBox)):
            spin.setValue(30)
            before = spin.text()
        click_visible_button(spin, subcontrol)
        assert spin.text() != before
    spin.close()


def test_add_classroom_persists_pointer_selected_capacity(native_style, tmp_path, monkeypatch):
    from src.gui import main_window
    from src.infrastructure.session_repository import SessionRepository
    native_style.setStyleSheet(stylesheet_for(THEMES[0]))
    path = tmp_path / 'session.db'
    window = main_window.MainWindow(SessionRepository(str(path)), restore_session=False)
    def complete_dialog(dialog):
        dialog.show()
        QApplication.processEvents()
        dialog.inp_code.setText('A-CAPACITY')
        dialog.inp_desc.setText('Pointer test')
        dialog.inp_campus.setText('HO')
        click_visible_button(dialog.inp_capacity, QStyle.SubControl.SC_SpinBoxUp)
        buttons = dialog.findChild(QDialogButtonBox)
        QTest.mouseClick(buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)
        return dialog.result()
    monkeypatch.setattr(AddClassroomDialog, 'exec', complete_dialog)
    window._add_classroom()
    assert window._classrooms['A-CAPACITY'].capacity == 31
    saved = SessionRepository(str(path)).load_session()
    assert saved['classrooms']['A-CAPACITY'].capacity == 31
    window.close()


def test_capacity_bounds_and_code_validation_are_unchanged(monkeypatch):
    from src.gui import dialogs
    warnings = []
    monkeypatch.setattr(dialogs.QMessageBox, 'warning', lambda *args: warnings.append(args))
    dialog = AddClassroomDialog(None)
    dialog.show()
    QApplication.processEvents()
    dialog.inp_capacity.setValue(0)
    assert dialog.inp_capacity.value() == 1
    dialog.inp_capacity.setValue(999)
    assert dialog.inp_capacity.value() == 500
    dialog._on_accept()
    assert warnings and dialog.result() == dialog.DialogCode.Rejected
    assert dialog.inp_code.hasFocus()
    dialog.reject()


@pytest.mark.parametrize('kind', [QSpinBox, QDoubleSpinBox, QTimeEdit, QDateEdit, QDateTimeEdit])
def test_disabled_and_buttonless_controls_remain_native(native_style, kind):
    native_style.setStyleSheet(stylesheet_for(THEMES[0]))
    spin = kind()
    spin.show()
    native_style.processEvents()
    spin.setEnabled(False)
    before = spin.text()
    click_visible_button(spin, QStyle.SubControl.SC_SpinBoxUp)
    assert spin.text() == before
    spin.setEnabled(True)
    spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    native_style.processEvents()
    option = QStyleOptionSpinBox()
    spin.initStyleOption(option)
    assert not (option.subControls & (QStyle.SubControl.SC_SpinBoxUp | QStyle.SubControl.SC_SpinBoxDown))
    spin.close()
