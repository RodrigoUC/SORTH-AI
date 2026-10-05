"""Explicit clipboard-to-external-AI guide; no provider, network or persistence.

Only the canonical contract and a sanitized candidate palette enter the prompt.
The guide cannot access a timetable, source filename or imported metadata.
"""
import json

from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QFrame, QPlainTextEdit, QScrollArea, QSizePolicy, QVBoxLayout,
    QWidget,
)

from .i18n import language_manager, msg
from .i18n_widgets import (
    QDialog, QDialogButtonBox, QLabel, QPushButton, ResponsiveActionLabels,
    ResponsiveDialogButtonBox,
)
from .theme_contract import (
    MAX_THEME_BYTES, contrast_checks, theme_json_schema, validate_theme,
)


def _safe_template(candidate):
    """Allowlist palette data and replace even valid imported metadata."""
    validated = validate_theme(candidate.to_dict())
    return validate_theme({
        'schema_version': validated.schema_version,
        'name': 'My SORTH theme',
        'description': 'A custom interface palette.',
        'mode': validated.mode,
        'colors': dict(validated.colors),
    })


def theme_creation_prompt(candidate):
    """Return reviewable instructions from the canonical contract, never user text.

    Metadata accepted as plain text by an importer can still contain instructions
    for an AI. Revalidate the candidate, then allowlist only its mode and colors.
    Schema and contrast requirements are derived, not independently maintained.
    """
    template = _safe_template(candidate)
    requirements = [
        {'foreground': check.foreground, 'background': check.background,
         'minimum_ratio': check.minimum}
        for check in contrast_checks(template)
    ]
    instructions = msg(
        'Crea un tema de interfaz SORTH según mis preferencias visuales, que añadiré a este mensaje. '
        'Devuelve un único objeto JSON UTF-8 para un archivo .sorth-theme.json, sin Markdown ni texto alrededor. '
        'Usa la plantilla completa como punto de partida. Cambia solo los colores y los metadatos del tema; '
        'no añadas campos, estilos, código, rutas, fuentes ni recursos externos. '
        'No necesitas cursos, horarios, archivos personales, cuentas ni credenciales.\n\n'
        'Cumple el esquema canónico y todas las parejas de contraste indicadas. '
        'Los contrastes usan luminancia relativa sRGB WCAG, sin redondear antes de comparar. '
        'No uses claves duplicadas, NaN, Infinity, BOM, marcado ni caracteres Unicode de control o formato. '
        'El archivo final debe ocupar como máximo {limit} bytes. '
        'Si tienes el repositorio SORTH correspondiente, usa su habilidad sorth-theme-designer y su validador canónico. '
        'Si no puedes ejecutar ese validador, dilo por separado y no afirmes que el tema está validado. '
        'SORTH comprobará el resultado al importarlo; cumplir el esquema por sí solo no garantiza su aceptación ni certifica accesibilidad.',
        limit=MAX_THEME_BYTES)
    # Labels within the technical payload deliberately stay stable. Only JSON
    # values from validated hex colors/mode are variable; metadata is fixed.
    return (str(instructions) + '\n\nSORTH TEMPLATE\n' +
            json.dumps(template.to_dict(), ensure_ascii=False, indent=2) +
            '\n\nSORTH JSON SCHEMA\n' +
            json.dumps(theme_json_schema(), ensure_ascii=False, indent=2) +
            '\n\nSORTH CONTRAST REQUIREMENTS\n' +
            json.dumps(requirements, ensure_ascii=False, indent=2))


def _label(text, *, role=None):
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    label.setMinimumWidth(0)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                  Qt.TextInteractionFlag.TextSelectableByKeyboard)
    label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    if role:
        label.setObjectName(role)
    return label


class ThemeCreationDialog(QDialog):
    """Accepted means 'open the existing importer', never apply or save a theme."""

    def __init__(self, candidate, parent=None):
        super().__init__(parent)
        # No reference to the appearance manager, imported file or parent data.
        # Discard metadata even in the stored seed, before any later translation.
        self._seed = _safe_template(candidate)
        self.setObjectName('themeCreationDialog')
        self.setWindowTitle(msg('Crear un tema con IA'))
        self.resize(660, 640)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName('settingsContent')
        body = QVBoxLayout(content)
        body.setContentsMargins(12, 12, 12, 12)
        body.setSpacing(10)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)
        self.intro = _label(msg('Usa la IA que prefieras fuera de SORTH. Esta guía no abre ni conecta servicios, no envía datos y no realiza llamadas de pago.'), role='mutedText')
        body.addWidget(self.intro)
        self.step_copy = _label(msg('1. Copia la especificación'), role='settingsSectionTitle')
        body.addWidget(self.step_copy)
        self.copy_hint = _label(msg('Incluye el contrato y los colores de la vista previa, con nombre y descripción de ejemplo. No incluye cursos, horarios, nombres de archivos ni datos del proyecto.'))
        body.addWidget(self.copy_hint)
        self.specification = QPlainTextEdit()
        self.specification.setReadOnly(True)
        self.specification.setTabChangesFocus(True)
        self.specification.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.specification.setMinimumWidth(0)
        self.specification.setMinimumHeight(150)
        self.specification.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        body.addWidget(self.specification)
        self.copy_button = QPushButton(msg('Copiar especificación'))
        self.copy_button.clicked.connect(self._copy)
        body.addWidget(self.copy_button)
        self.copy_status = _label('')
        self.copy_status.hide()
        body.addWidget(self.copy_status)
        self.step_generate = _label(msg('2. Genera el archivo en tu IA'), role='settingsSectionTitle')
        body.addWidget(self.step_generate)
        self.generate_hint = _label(msg('Pega la especificación, añade tus preferencias visuales y pide el archivo JSON. Revisa la privacidad y los posibles cargos de ese servicio. Si tu asistente usa habilidades, el repositorio incluye sorth-theme-designer.'))
        body.addWidget(self.generate_hint)
        self.step_import = _label(msg('3. Importa y revisa'), role='settingsSectionTitle')
        body.addWidget(self.step_import)
        self.import_hint = _label(msg('La IA puede producir un tema inválido. SORTH comprobará el archivo y su contraste. Si es válido, solo cambiará la vista previa; después debes pulsar Aplicar.'))
        body.addWidget(self.import_hint)
        self.import_button = QPushButton(msg('Importar resultado…'))
        self.import_button.clicked.connect(self.accept)
        body.addWidget(self.import_button)
        body.addStretch(1)
        self.buttons = ResponsiveDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.close_button = self.buttons.button(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        for button in (self.copy_button, self.import_button, self.close_button):
            button.setAutoDefault(False)
        self._responsive_actions = ResponsiveActionLabels(
            self.scroll, [self.copy_button, self.import_button], self)
        ordered = [self.intro, self.step_copy, self.copy_hint, self.specification,
                   self.copy_button, self.copy_status, self.step_generate,
                   self.generate_hint, self.step_import, self.import_hint,
                   self.import_button, self.close_button]
        for previous, following in zip(ordered, ordered[1:]):
            self.setTabOrder(previous, following)
        self._focus_reveal_timer = QTimer(self)
        self._focus_reveal_timer.setSingleShot(True)
        self._focus_reveal_timer.timeout.connect(self._reveal_focus)
        for target in (self.scroll.viewport(), content):
            target.installEventFilter(self)
        QApplication.instance().focusChanged.connect(self._scroll_to_focus)
        language_manager().changed.connect(self._retranslate_specification)
        self._retranslate_specification()
        self.intro.setFocus(Qt.FocusReason.TabFocusReason)

    def _copy(self):
        expected = self.specification.toPlainText()
        copied = False
        try:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                # Qt's void setText can return after a native clipboard failure.
                # Compare only after this explicit write; never retain or expose
                # whatever another application may have left in the clipboard.
                clipboard.setText(expected)
                copied = clipboard.text() == expected
        except RuntimeError:
            # An unavailable/deleted native wrapper also leaves manual copying
            # available. Native error details may contain unrelated private data.
            copied = False
        if copied:
            self.copy_status.setText(msg('Especificación copiada. Pégala en la IA que elijas; el tema sigue sin aplicarse.'))
        else:
            self.copy_status.setText(msg('No se pudo confirmar la copia. Inténtalo de nuevo o selecciona el texto de la especificación y cópialo manualmente.'))
        self.copy_status.show()

    def _retranslate_specification(self, *_):
        self.specification.setAccessibleName(str(msg('Especificación y plantilla para copiar')))
        cursor = self.specification.textCursor()
        position, anchor = cursor.position(), cursor.anchor()
        scroll = self.specification.verticalScrollBar().value()
        self.specification.setPlainText(theme_creation_prompt(self._seed))
        cursor = self.specification.textCursor()
        limit = self.specification.document().characterCount() - 1
        cursor.setPosition(min(anchor, limit))
        cursor.setPosition(min(position, limit), cursor.MoveMode.KeepAnchor)
        self.specification.setTextCursor(cursor)
        self.specification.verticalScrollBar().setValue(scroll)

    def _scroll_to_focus(self, previous, focused):
        if (self.isVisible() and focused is not None
                and self.scroll.widget().isAncestorOf(focused)):
            self._reveal_focus()
            self._focus_reveal_timer.start(0)

    def _reveal_focus(self):
        focused = QApplication.focusWidget()
        if (not self.isVisible() or focused is None or not focused.isVisible()
                or not self.scroll.widget().isAncestorOf(focused)):
            return
        viewport = self.scroll.viewport()
        rect = focused.rect().translated(focused.mapTo(viewport, focused.rect().topLeft()))
        if viewport.rect().contains(rect):
            return
        if rect.height() > viewport.height() and viewport.rect().contains(rect.center()):
            return
        # ensureWidgetVisible may use a text editor's cursor rectangle rather
        # than its frame, leaving most of the editor below the viewport at 20pt.
        # Reveal the native control itself; tall selectable labels stay centered.
        center = focused.mapTo(self.scroll.widget(), focused.rect().center())
        self.scroll.ensureVisible(center.x(), center.y(), 0,
                                  min(viewport.height() // 2,
                                      focused.height() // 2 + 12))

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.LayoutRequest,
                            QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._focus_reveal_timer.start(0)
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'scroll'):
            compact = self.height() < 520
            self.layout().setContentsMargins(*((8, 8, 8, 8) if compact else (12, 12, 12, 12)))
            self.layout().setSpacing(6 if compact else 10)
