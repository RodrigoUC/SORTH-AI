"""Small Qt adapters that retain explicitly marked Message properties.

Only Message values are rebound on a language change. Ordinary strings are
always literal, including user-entered data equal to a catalog key. The same
widgets/items remain alive, preserving focus, input, selection and scroll state.
"""
from PyQt6 import QtWidgets as QtW
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QAction as QtAction
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
            getattr(super(), method)(*[_render(value) for value in arguments])


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


class QPushButton(_Localized, QtW.QPushButton):
    pass


class QCheckBox(_Localized, QtW.QCheckBox):
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
    pass


class QMainWindow(_Localized, QtW.QMainWindow):
    pass


class QAction(_Localized, QtAction):
    pass


class QTableWidgetItem(_Localized, QtW.QTableWidgetItem):
    pass


class QTableWidget(_Localized, QtW.QTableWidget):
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


class QMessageBox(_LocalizedButtons, _Localized, QtW.QMessageBox):
    # Inherit Qt's static helpers unchanged, including compatibility with test
    # patches. Constructed message boxes retain explicit marked properties.
    pass
