"""Small Qt adapters that retain explicitly marked Message properties.

Only Message values are rebound on a language change. Ordinary strings are
always literal, including user-entered data equal to a catalog key. The same
widgets/items remain alive, preserving focus, input, selection and scroll state.
"""
from PyQt6 import QtWidgets as QtW
from PyQt6.QtCore import QEvent, Qt, QObject, QTimer
from PyQt6 import sip
from PyQt6.QtGui import QAction as QtAction, QTextLayout, QTextOption
from .i18n import Message, msg, language_manager, _render


class _Localized:
    def __init__(self, *args, **kwargs):
        self._messages = {}
        super().__init__(*args, **kwargs)
        language_manager().register(self)
        if args and isinstance(args[0], Message) and hasattr(self, 'setText'):
            self.setText(args[0])

    def _remember(self, method, arguments, key=None):
        key = key or method
        if any(isinstance(value, Message) for value in arguments):
            self._messages[key] = (method, arguments)
        else:
            self._messages.pop(key, None)
        return getattr(super(), method)(*[_render(value) for value in arguments])

    def retranslate(self):
        for method, arguments in list(self._messages.values()):
            rendered = [_render(value) for value in arguments]
            # Rendering may run callbacks or GC. A Python wrapper can outlive
            # its Qt object, so check after rendering and before the native call.
            if sip.isdeleted(self):
                return
            getattr(super(), method)(*rendered)


def _localized_setter(method):
    def setter(self, value):
        return self._remember(method, (value,))
    setter.__name__ = method
    return setter


# Qt property setters used by SORTH. Calling an unsupported setter remains an
# error, as it would on its native Qt class.
for _name in ('setText', 'setWindowTitle', 'setToolTip', 'setAccessibleName',
              'setAccessibleDescription', 'setPlaceholderText', 'setPrefix', 'setSuffix', 'setFormat', 'setInformativeText', 'setDetailedText'):
    setattr(_Localized, _name, _localized_setter(_name))


class QLabel(_Localized, QtW.QLabel):
    def clear(self):
        self._messages.pop('setText', None)
        super().clear()


class _ResponsiveButtonText:
    def wrapPresentationText(self, available_width):
        """Wrap only the native display; keep the complete Message binding intact."""
        binding = self._messages.get('setText')
        if binding is None:
            return
        source = binding[1][0]
        full_text = str(_render(source))
        self.setAccessibleName(source)
        self.ensurePolished()
        # Ask the current native style for its indicator, border and padding.
        # Use the current display width, including any previous line breaks.
        metrics = self.fontMetrics()
        current_text_width = metrics.size(Qt.TextFlag.TextShowMnemonic, self.text()).width()
        chrome = max(0, self.minimumSizeHint().width() - current_text_width)
        text_width = max(1, available_width - chrome - 4)
        while True:
            lines = []
            for paragraph in full_text.split('\n'):
                # QTextLine offsets count UTF-16 units, unlike Python slices.
                utf16 = paragraph.encode('utf-16-le')
                # Use the same paint device as native fontMetrics/sizeHint.
                # Screen-default DPI is not necessarily this widget's DPI.
                text_layout = QTextLayout(paragraph, self.font(), self)
                option = QTextOption()
                option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
                text_layout.setTextOption(option)
                text_layout.beginLayout()
                while True:
                    line = text_layout.createLine()
                    if not line.isValid():
                        break
                    line.setLineWidth(text_width)
                    start = line.textStart() * 2
                    end = start + line.textLength() * 2
                    lines.append(utf16[start:end].decode('utf-16-le').strip())
                text_layout.endLayout()
                if not paragraph:
                    lines.append('')
            display = '\n'.join(lines)
            if display != self.text():
                # Keep the source Message and full accessible name unchanged.
                QtW.QAbstractButton.setText(self, display)
            excess = self.minimumSizeHint().width() - available_width
            if excess <= 0 or text_width <= 1:
                break
            # Native styles can reserve more space than the initial estimate.
            # Confirm the final native hint, then reduce only the wrap budget.
            # A strictly decreasing integer budget guarantees termination.
            text_width = max(1, text_width - max(4, excess))


class QPushButton(_ResponsiveButtonText, _Localized, QtW.QPushButton):
    pass


class QCheckBox(_ResponsiveButtonText, _Localized, QtW.QCheckBox):
    pass


class ResponsiveActionLabels(QObject):
    """Fit full native button/checkbox labels to a scroll area's viewport."""
    def __init__(self, scroll, controls, parent=None):
        super().__init__(parent or scroll)
        self.scroll = scroll
        self.viewport = scroll.viewport()
        self.content = scroll.widget()
        self.controls = tuple(controls)
        self._reflowing = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._rewrap)
        scroll.viewport().installEventFilter(self)
        scroll.widget().installEventFilter(self)
        language_manager().changed.connect(self._rewrap)
        self._schedule()

    def _schedule(self, *_):
        if not sip.isdeleted(self.timer):
            self.timer.start(0)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show) and watched is self.viewport:
            # A zero timer need not fire in the first processEvents pass on
            # Windows. First-show/resize must not depend on timer delivery.
            self._rewrap()
        elif event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.FontChange,
                              QEvent.Type.StyleChange):
            self._schedule()
        return super().eventFilter(watched, event)

    def _rewrap(self, *_):
        if (self._reflowing or sip.isdeleted(self.scroll)
                or sip.isdeleted(self.viewport) or sip.isdeleted(self.content)
                or sip.isdeleted(self.timer)):
            return
        self.timer.stop()
        self._reflowing = True
        try:
            margins = self.scroll.widget().layout().contentsMargins()
            width = self.scroll.viewport().width() - margins.left() - margins.right()
            if width <= 0:
                return
            content = self.scroll.widget()
            changed = False
            for control in self.controls:
                previous = control.text()
                control.wrapPresentationText(width)
                if control.text() != previous:
                    changed = True
                    # Section layouts can still cache the old unwrapped hint.
                    # Update inner layouts before querying the outer minimum.
                    parent = control.parentWidget()
                    while parent is not None and parent is not content:
                        if parent.layout() is not None:
                            parent.layout().invalidate()
                            parent.layout().activate()
                        parent = parent.parentWidget()
            if changed:
                content.layout().invalidate()
            content.layout().activate()
            content.resize(max(self.scroll.viewport().width(), content.minimumSizeHint().width()),
                           content.height())
        finally:
            self._reflowing = False



class QListWidget(_Localized, QtW.QListWidget):
    pass


class QLineEdit(_Localized, QtW.QLineEdit):
    pass


class QSpinBox(_Localized, QtW.QSpinBox):
    pass


class QProgressBar(_Localized, QtW.QProgressBar):
    pass


class QTimeEdit(_Localized, QtW.QTimeEdit):
    pass


class QWidget(_Localized, QtW.QWidget):
    pass


class QDialog(_Localized, QtW.QDialog):
    def exec(self):
        # A stable invoker, rather than a reconstructed first control, receives
        # focus after both acceptance and Escape/cancellation.
        invoker = QtW.QApplication.focusWidget()
        try:
            return super().exec()
        finally:
            if (invoker is not None and not sip.isdeleted(invoker)
                    and invoker.isVisible() and invoker.isEnabled()):
                invoker.setFocus(Qt.FocusReason.OtherFocusReason)


class QMainWindow(_Localized, QtW.QMainWindow):
    pass


class QAction(_Localized, QtAction):
    pass


class QTableWidgetItem(_Localized, QtW.QTableWidgetItem):
    def setData(self, role, value):
        self._remember('setData', (role, value), ('data', role))


class QTableWidget(_Localized, QtW.QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Arrow keys explore cells; Tab always reaches the following action.
        self.setTabKeyNavigation(False)
        self.setAccessibleDescription(msg('Use flechas para recorrer celdas y Tab para salir. En tablas ordenables, Ctrl+Mayús+Arriba o Abajo ordena la columna actual.'))

    def keyPressEvent(self, event):
        if (self.isSortingEnabled() and self.currentColumn() >= 0
                and event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
                and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down)):
            order = (Qt.SortOrder.AscendingOrder if event.key() == Qt.Key.Key_Up
                     else Qt.SortOrder.DescendingOrder)
            self.sortItems(self.currentColumn(), order)
            event.accept()
            return
        super().keyPressEvent(event)

    def setHorizontalHeaderLabels(self, labels):
        for column, label in enumerate(labels):
            self.setHorizontalHeaderItem(column, QTableWidgetItem(label))


class QComboBox(_Localized, QtW.QComboBox):
    def addItem(self, text, userData=None):
        super().addItem(str(_render(text)), userData)
        self.setItemText(self.count() - 1, text)

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def setItemText(self, index, text):
        self._remember('setItemText', (index, text), ('item', index))

    def clear(self):
        self._messages = {key: value for key, value in self._messages.items()
                          if not isinstance(key, tuple) or key[0] != 'item'}
        super().clear()


class QTabWidget(_Localized, QtW.QTabWidget):
    def addTab(self, widget, text):
        index = super().addTab(widget, str(_render(text)))
        self.setTabText(index, text)
        return index

    def setTabText(self, index, text):
        self._remember('setTabText', (index, text), ('tab', index))

    def setTabToolTip(self, index, text):
        self._remember('setTabToolTip', (index, text), ('tooltip', index))


class QFormLayout(QtW.QFormLayout):
    def addRow(self, *args):
        if args and isinstance(args[0], Message):
            label = QLabel(args[0])
            if isinstance(args[1], QtW.QWidget):
                label.setBuddy(args[1])
                if not args[1].accessibleName():
                    args[1].setAccessibleName(args[0])
            args = (label, *args[1:])
        super().addRow(*args)


class QStatusBar(_Localized, QtW.QStatusBar):
    def showMessage(self, text, timeout=0):
        self._remember('showMessage', (text, timeout))

    def clearMessage(self):
        self._messages.pop('showMessage', None)
        super().clearMessage()


_BUTTON_TEXT = {
    QtW.QDialogButtonBox.StandardButton.Ok: 'Aceptar',
    QtW.QDialogButtonBox.StandardButton.Cancel: 'Cancelar',
    QtW.QDialogButtonBox.StandardButton.Yes: 'Sí',
    QtW.QDialogButtonBox.StandardButton.No: 'No',
    QtW.QDialogButtonBox.StandardButton.Close: 'Cerrar',
    QtW.QDialogButtonBox.StandardButton.Save: 'Guardar',
    QtW.QDialogButtonBox.StandardButton.Open: 'Abrir',
    QtW.QDialogButtonBox.StandardButton.Retry: 'Reintentar',
    QtW.QDialogButtonBox.StandardButton.Discard: 'Descartar',
}


class _LocalizedButtons:
    def __init__(self, *args, **kwargs):
        self._button_messages = {}
        super().__init__(*args, **kwargs)
        self.retranslate()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.LanguageChange and hasattr(self, '_messages'):
            self.retranslate()

    def setButtonText(self, standard, text):
        self._button_messages[standard.value] = text
        button = self.button(standard)
        if button:
            button.setText(_render(text))

    def retranslate(self):
        super().retranslate()
        for standard, source in _BUTTON_TEXT.items():
            standard = self.StandardButton(standard.value)
            button = self.button(standard)
            if button:
                button.setText(_render(self._button_messages.get(standard.value, msg(source))))


class QDialogButtonBox(_LocalizedButtons, _Localized, QtW.QDialogButtonBox):
    pass


class ResponsiveDialogButtonBox(QDialogButtonBox):
    """Retain native action buttons, stacking them only when a row cannot fit."""
    def __init__(self, *args, **kwargs):
        self._fitting = False
        self._fit_signature = None
        self._metric_change_pending = False
        super().__init__(*args, **kwargs)
        self._metric_timer = QTimer(self)
        self._metric_timer.setSingleShot(True)
        self._metric_timer.timeout.connect(self._after_metric_change)
        # The footer may reflow rather than raising the dialog's minimum width.
        self.setSizePolicy(QtW.QSizePolicy.Policy.Ignored, QtW.QSizePolicy.Policy.Minimum)

    def _fit_actions(self):
        if self._fitting:
            return
        signature = (self.width(), tuple((button.text(), button.minimumSizeHint().width(),
                                          button.minimumSizeHint().height()) for button in self.buttons()))
        if signature == self._fit_signature:
            return
        self._fit_signature = signature
        self._fitting = True
        try:
            self.setOrientation(Qt.Orientation.Horizontal)
            if self.minimumSizeHint().width() > self.width():
                self.setOrientation(Qt.Orientation.Vertical)
            self.updateGeometry()
            parent = self.parentWidget()
            if parent is not None and parent.layout() is not None:
                parent.layout().activate()
            self.layout().activate()
        finally:
            self._fitting = False

    def _after_metric_change(self):
        self._metric_change_pending = False
        self._fit_actions()

    def event(self, event):
        result = super().event(event)
        if event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.FontChange, QEvent.Type.StyleChange):
            if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
                self._metric_change_pending = True
            timer = getattr(self, '_metric_timer', None)
            if timer is not None:
                # Never activate ancestor layouts while QApplication is
                # replacing a native style and unpolishing its widget tree.
                timer.start(0)
        return result

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._metric_change_pending:
            self._fit_actions()

    def showEvent(self, event):
        self._metric_change_pending = False
        self._fit_actions()
        super().showEvent(event)

    def retranslate(self):
        super().retranslate()
        self._fit_actions()


class QMessageBox(_LocalizedButtons, _Localized, QtW.QMessageBox):
    # Inherit Qt's static helpers unchanged, including compatibility with test
    # patches. Constructed message boxes retain explicit marked properties.
    pass
