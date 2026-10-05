"""User-initiated template export; never imports or changes the live session."""
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog

from ..infrastructure.excel_template import write_import_template
from .dialogs import _InfoDialog
from .i18n import msg
from .i18n_widgets import QMessageBox, QPushButton, _focused_button_size


class TemplateSaveButton(QPushButton):
    """Reserve the native focused frame without widening unrelated controls."""
    def sizeHint(self):
        return super().sizeHint().expandedTo(_focused_button_size(self))

    def minimumSizeHint(self):
        return self.sizeHint()


def save_import_template(parent):
    path, _ = QFileDialog.getSaveFileName(
        parent, msg('Guardar plantilla Excel'), 'plantilla_sorth.xlsx',
        msg('Archivos Excel (*.xlsx)'))
    if not path:
        return
    try:
        if Path(path).suffix.lower() != '.xlsx':
            path += '.xlsx'
            destination = Path(path)
            # Native picker consent covers the selected path only.
            if destination.exists() or destination.is_symlink():
                confirmation = QMessageBox(parent)
                confirmation.setWindowTitle(msg('Confirmar reemplazo'))
                confirmation.setIcon(QMessageBox.Icon.Question)
                confirmation.setTextFormat(Qt.TextFormat.PlainText)
                confirmation.setText(msg('El archivo ya existe:\n{path}\n\n¿Desea reemplazarlo?', path=path))
                confirmation.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                confirmation.setDefaultButton(QMessageBox.StandardButton.No)
                try:
                    if confirmation.exec() != QMessageBox.StandardButton.Yes:
                        return
                finally:
                    confirmation.deleteLater()
        write_import_template(path)
    except Exception:
        parent.status_bar.showMessage(msg('No se pudo guardar la plantilla en {filename}. Revise el destino e inténtelo de nuevo.', filename=Path(path).name))
        _InfoDialog(parent, msg('Error'), msg('No se pudo guardar la plantilla. Cierre el archivo si está abierto y revise los permisos del destino.'), warning=True).exec()
    else:
        parent.status_bar.showMessage(msg('Plantilla guardada: {filename}. Reemplace los ejemplos y use Cargar Excel.', filename=Path(path).name))
