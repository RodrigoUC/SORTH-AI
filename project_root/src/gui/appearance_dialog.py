"""Data-only theme selection with an isolated, interactive native preview.

Selection and import only change the candidate. Apply is the single persistence
boundary; Settings' separate Save/Cancel transaction never owns a theme change.
"""
from PyQt6.QtCore import Qt, QEvent, QSignalBlocker, QTimer
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QAbstractItemView, QFileDialog, QFrame, QGridLayout,
    QHeaderView, QPlainTextEdit, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from .i18n import language_manager, msg
from .i18n_widgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, ResponsiveActionLabels,
    ResponsiveDialogButtonBox,
)
from . import theme
from .theme_contract import ThemeValidationError, load_theme_file, validate_theme
from .theme_preferences import ThemePersistenceError
from ..scheduling.course_style import course_style
from .schedule_grid_delegate import CourseCard, COURSE_CARD_ROLE, ScheduleGridDelegate


_BUILTIN_NAMES = {
    'original': 'Original claro',
    'nocturno': 'Nocturno',
    'high_contrast': 'Alto contraste claro',
}
_BUILTIN_DESCRIPTIONS = {
    'original': 'La identidad original de SORTH: azul marino, verde azulado y violeta.',
    'nocturno': 'Superficies oscuras y controles nítidos para trabajar con poca luz.',
    'high_contrast': 'Superficies claras con bordes y texto de mayor contraste.',
}


def _label(text='', *, role=None, selectable=False):
    result = QLabel(text)
    result.setTextFormat(Qt.TextFormat.PlainText)
    result.setWordWrap(True)
    result.setMinimumWidth(0)
    result.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    if role:
        result.setObjectName(role)
    if selectable:
        result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                       Qt.TextInteractionFlag.TextSelectableByKeyboard)
        result.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    return result


def _swatch(spec):
    """A local hint beside a native option, never its sole identity."""
    pixmap = QPixmap(48, 20)
    pixmap.fill(QColor(spec.colors['surface']))
    painter = QPainter(pixmap)
    for index, role in enumerate(('header', 'primary', 'accent')):
        painter.fillRect(index * 16, 0, 16, 20, QColor(spec.colors[role]))
    painter.end()
    return QIcon(pixmap)


class ThemePreview(QFrame):
    """Real sample controls. Editing and clicking cannot touch timetable data."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('themePreview')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._stacked = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        header = QFrame()
        header.setObjectName('settingsHeader')
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(4)
        header_layout.addWidget(_label(msg('Tu espacio de trabajo'), role='settingsTitle'))
        header_layout.addWidget(_label(msg('Vista previa interactiva · datos de ejemplo'), role='settingsSubtitle'))
        layout.addWidget(header)

        self.columns = QGridLayout()
        self.columns.setContentsMargins(0, 0, 0, 0)
        self.columns.setHorizontalSpacing(16)
        self.columns.setVerticalSpacing(12)
        self.controls = QWidget()
        controls = QVBoxLayout(self.controls)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        field_label = _label(msg('Nombre del horario'))
        self.input = QLineEdit()
        self.input.setPlaceholderText(msg('Escribe para probar el tema'))
        self.input.setAccessibleName(msg('Nombre del horario de ejemplo'))
        self.input.setMinimumWidth(0)
        field_label.setBuddy(self.input)
        controls.addWidget(field_label)
        controls.addWidget(self.input)
        self.focus_button = QPushButton(msg('Probar foco'))
        self.focus_button.setAccessibleDescription(msg('Control de ejemplo. Usa Tab para ver el indicador de foco.'))
        self.focus_button.clicked.connect(lambda: self.input.setFocus(Qt.FocusReason.OtherFocusReason))
        controls.addWidget(self.focus_button)
        self.primary = QPushButton(msg('Probar acción'))
        self.primary.setObjectName('primaryAction')
        self.primary.clicked.connect(self._sample_action)
        controls.addWidget(self.primary)
        self.disabled = QPushButton(msg('No disponible'))
        self.disabled.setEnabled(False)
        controls.addWidget(self.disabled)
        self.sample_status = _label(msg('Los controles solo cambian esta muestra.'), role='mutedText')
        controls.addWidget(self.sample_status)
        controls.addStretch(1)

        self.schedule = QWidget()
        schedule = QVBoxLayout(self.schedule)
        schedule.setContentsMargins(0, 0, 0, 0)
        schedule.setSpacing(8)
        self.table = QTableWidget(2, 1)
        self.table.setAccessibleName(msg('Filas de ejemplo; la primera está seleccionada'))
        self.table.setHorizontalHeaderLabels([msg('Sesiones')])
        self.table.setItem(0, 0, QTableWidgetItem(msg('Fila seleccionada')))
        self.table.setItem(1, 0, QTableWidgetItem(msg('Fila sin seleccionar')))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(0)
        self.table.setMinimumWidth(0)
        self.table.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.table.setAlternatingRowColors(True)
        self.table.setCurrentCell(0, 0)
        self.table.selectRow(0)
        schedule.addWidget(self.table)
        self.course = QTableWidget(1, 1)
        self.course.setAccessibleName(msg('Bloque de curso de ejemplo'))
        self.course.setMinimumWidth(0)
        self.course.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.course.horizontalHeader().hide()
        self.course.verticalHeader().hide()
        self.course.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.course.horizontalHeader().setMinimumSectionSize(0)
        self.course.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.course.setShowGrid(False)
        self.course.setItem(0, 0, QTableWidgetItem())
        self.course.setCurrentCell(0, 0)
        self.course.selectRow(0)
        schedule.addWidget(self.course)
        schedule.addWidget(_label(msg('Tonos adaptados; identidad y patrones estables.'), role='mutedText'))
        schedule.addStretch(1)
        self.columns.addWidget(self.controls, 0, 0)
        self.columns.addWidget(self.schedule, 0, 1)
        layout.addLayout(self.columns)
        self.warning = _label(msg('Aviso de ejemplo: revisa las sesiones pendientes.'))
        self.warning.setObjectName('themeSampleWarning')
        self.error = _label(msg('Error de ejemplo: hay un cruce de horario.'))
        self.error.setObjectName('themeSampleError')
        layout.addWidget(self.warning)
        layout.addWidget(self.error)
        language_manager().changed.connect(self._fit_table)

    def _sample_action(self):
        self.sample_status.setText(msg('Acción de ejemplo completada. Tu horario no ha cambiado.'))

    def set_theme(self, spec):
        # The runtime helper validates again and scopes both QSS and QPalette.
        theme.preview_theme(self, spec)
        c = spec.colors
        self.setStyleSheet(self.styleSheet() + f'''
            QFrame#themePreview {{ border: 1px solid {c['divider']}; border-radius: 7px; }}
            QFrame#themePreview QLabel {{ border: 1px solid transparent; }}
            QFrame#themePreview QLabel:focus {{ border-color: {c['focus']}; }}
            QLabel#themeSampleWarning {{ color: {c['warning']}; background: {c['warning_soft']}; padding: 8px; border-radius: 4px; }}
            QLabel#themeSampleError {{ color: {c['danger']}; background: {c['danger_soft']}; padding: 8px; border-radius: 4px; }}
        ''')
        previous = self.course.itemDelegate()
        self.course.setItemDelegate(ScheduleGridDelegate(self.course, colors=spec.colors))
        if previous is not None:
            previous.deleteLater()
        self._fit_table()

    def _fit_table(self, *_):
        if not hasattr(self, 'table') or not hasattr(self, 'course'):
            return
        self.table.resizeRowsToContents()
        height = (self.table.horizontalHeader().height() +
                  sum(self.table.rowHeight(row) for row in range(self.table.rowCount())) +
                  self.table.frameWidth() * 2 + 4)
        self.table.setFixedHeight(height)
        self.course.item(0, 0).setData(COURSE_CARD_ROLE, CourseCard(
            course_style('MAT101'), (('MAT101', '08:00–09:00', str(msg('Matemáticas · Aula 101'))),)))
        self.course.item(0, 0).setText(msg('MAT101 · 08:00–09:00 · Matemáticas · Aula 101'))
        course_height = self.course.fontMetrics().height() * 4 + 32
        self.course.setRowHeight(0, course_height)
        self.course.setFixedHeight(course_height + self.course.frameWidth() * 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Native widgets keep their font. Only the column count changes.
        stacked = self.width() < max(540, self.fontMetrics().horizontalAdvance('M') * 44)
        if stacked != self._stacked:
            self._stacked = stacked
            self.columns.removeWidget(self.schedule)
            self.columns.addWidget(self.schedule, 1 if stacked else 0, 0 if stacked else 1)
            self.columns.setColumnStretch(0, 1)
            self.columns.setColumnStretch(1, 0 if stacked else 1)
        self._fit_table()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._fit_table()


class AppearanceDialog(QDialog):
    def __init__(self, parent=None, *, manager=None):
        super().__init__(parent)
        self.manager = manager if manager is not None else theme.theme_manager()
        preference_changed = self.manager.refresh_preferences()
        self.candidate = self.manager.preferences.current
        self.candidate_key = self.manager.preferences.current_key
        self._applying = False
        self._preview_ready = False
        self._choices = {choice.key: choice.spec for choice in theme.builtin_themes()}
        if self.candidate_key not in self._choices:
            self._choices['custom'] = self.candidate
            self.candidate_key = 'custom'
        self.setObjectName('appearanceDialog')
        self.setWindowTitle(msg('Apariencia'))
        self.resize(740, 760)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName('settingsContent')
        body = QVBoxLayout(content)
        body.setContentsMargins(14, 12, 14, 12)
        body.setSpacing(10)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)
        body.addWidget(_label(msg('Hazlo tuyo'), role='settingsSectionTitle'))
        body.addWidget(_label(msg('Elige un tema y prueba sus controles. Solo Aplicar cambia la aplicación. Cancelar descarta esta vista previa.'), role='mutedText'))
        theme_label = _label(msg('Tema'))
        self.selector = QComboBox()
        self.selector.setAccessibleName(msg('Tema'))
        self.selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.selector.setMinimumContentsLength(1)
        self.selector.setMinimumWidth(0)
        self.selector.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        theme_label.setBuddy(self.selector)
        body.addWidget(theme_label)
        body.addWidget(self.selector)
        self.metadata = _label(selectable=True)
        self.metadata.setAccessibleName(msg('Descripción del tema'))
        body.addWidget(self.metadata)
        self.import_button = QPushButton(msg('Importar tema JSON…'))
        self.import_button.clicked.connect(self.choose_file)
        body.addWidget(self.import_button)
        body.addWidget(_label(msg('Archivo local .sorth-theme.json · máximo 16 KiB. También admite temas creados con IA usando el contrato de SORTH. Sin código, fuentes ni recursos externos.'), role='mutedText'))
        self.guide_button = QPushButton(msg('Crear un tema con IA…'))
        self.guide_button.clicked.connect(self.open_creation_guide)
        self.guide_button.setAutoDefault(False)
        body.addWidget(self.guide_button)
        self.recovery_notice = _label(msg('El archivo del tema guardado no es válido y se conserva. Revisa Original claro en la vista previa antes de recuperarlo.'), role='settingsNotice')
        self.recovery_notice.setVisible(bool(self.manager.recovery_issue))
        body.addWidget(self.recovery_notice)
        self.recover = QCheckBox(msg('Conservar archivo inválido y reemplazarlo al aplicar'))
        self.recover.setVisible(bool(self.manager.recovery_issue))
        self.recover.toggled.connect(self._refresh_apply)
        body.addWidget(self.recover)
        self.feedback = _label(selectable=True)
        self.feedback.setAccessibleName(msg('Estado del tema'))
        self.feedback.hide()
        body.addWidget(self.feedback)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setTabChangesFocus(True)
        self.details.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.details.setAccessibleName(str(msg('Detalles del error de tema')))
        self.details.setMinimumWidth(0)
        self.details.setMinimumHeight(110)
        self.details.hide()
        body.addWidget(self.details)
        self.preview = ThemePreview()
        body.addWidget(self.preview)
        body.addWidget(_label(msg('El tema adapta los tonos de pantalla; PDF y Excel conservan su paleta para papel blanco. No cambia horarios, permisos MCP ni animaciones.'), role='mutedText'))
        body.addStretch(1)

        self.buttons = ResponsiveDialogButtonBox()
        self.restore_button = QPushButton(msg('Restaurar original'))
        self.restore_button.setAccessibleDescription(msg('Selecciona Original claro en la vista previa. Pulsa Aplicar para guardarlo.'))
        self.buttons.addButton(self.restore_button, QDialogButtonBox.ButtonRole.ResetRole)
        self.restore_button.clicked.connect(self.restore_original)
        self.cancel_button = self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.apply_button = QPushButton(msg('Aplicar'))
        self.apply_button.setObjectName('primaryAction')
        self.buttons.addButton(self.apply_button, QDialogButtonBox.ButtonRole.ApplyRole)
        self.apply_button.clicked.connect(self.apply_candidate)
        self.buttons.rejected.connect(self.reject)
        for button in self.buttons.buttons():
            button.setAutoDefault(False)
        outer.addWidget(self.buttons)
        self._responsive_actions = ResponsiveActionLabels(self.scroll, [
            self.import_button, self.guide_button, self.recover, self.preview.focus_button,
            self.preview.primary, self.preview.disabled,
        ], self)
        self.selector.currentIndexChanged.connect(self._select_candidate)
        self._populate_selector()
        self._show_candidate()
        if self._preview_ready and preference_changed:
            self.feedback.setText(msg('Las preferencias de apariencia cambiaron fuera de esta ventana. Revisa el tema guardado en la vista previa y pulsa Aplicar para usarlo.'))
            self.feedback.show()
        elif self._preview_ready and self.candidate.to_dict() != self.manager.current.to_dict():
            self.feedback.setText(msg('El tema guardado se muestra en vista previa. El tema activo no cambia hasta pulsar Aplicar.'))
            self.feedback.show()
        ordered = [self.selector, self.metadata, self.import_button, self.guide_button, self.recover,
                   self.feedback, self.details, self.preview.input, self.preview.focus_button,
                   self.preview.primary, self.preview.table, self.preview.course, self.restore_button,
                   self.cancel_button, self.apply_button]
        for previous, following in zip(ordered, ordered[1:]):
            self.setTabOrder(previous, following)
        self._focus_reveal_timer = QTimer(self)
        self._focus_reveal_timer.setSingleShot(True)
        self._focus_reveal_timer.timeout.connect(self._reveal_after_reflow)
        for target in (self.scroll.viewport(), content, self.preview):
            target.installEventFilter(self)
        QApplication.instance().focusChanged.connect(self._scroll_to_focus)
        language_manager().changed.connect(self._retranslate_details)
        self.selector.setFocus(Qt.FocusReason.TabFocusReason)

    def _populate_selector(self):
        with QSignalBlocker(self.selector):
            self.selector.clear()
            for key, spec in self._choices.items():
                caption = msg(_BUILTIN_NAMES[key]) if key in _BUILTIN_NAMES else spec.name
                self.selector.addItem(caption, key)
                self.selector.setItemIcon(self.selector.count() - 1, _swatch(spec))
            self.selector.setCurrentIndex(self.selector.findData(self.candidate_key))

    def _select_candidate(self, *_):
        key = self.selector.currentData()
        if key not in self._choices:
            return
        self._clear_feedback()
        self._show_candidate(self._choices[key], key)

    def _show_candidate(self, candidate=None, key=None):
        candidate = self.candidate if candidate is None else candidate
        key = self.candidate_key if key is None else key
        # Preparing trusted assets can fail (for example, a full temporary disk).
        # Never let that exception escape a Qt slot or replace a valid candidate.
        try:
            self.preview.set_theme(candidate)
        except (OSError, ThemeValidationError, RuntimeError) as error:
            with QSignalBlocker(self.selector):
                self.selector.setCurrentIndex(self.selector.findData(self.candidate_key))
            self.preview.setVisible(self._preview_ready)
            self._show_error(msg('No se pudo preparar la vista previa. No se ha aplicado ningún cambio.'), error)
            self._refresh_apply()
            return False
        self.candidate, self.candidate_key = candidate, key
        self._preview_ready = True
        self.preview.show()
        # Metadata is explicit plain text. Custom text never enters msg().
        description = (msg(_BUILTIN_DESCRIPTIONS[key])
                       if key in _BUILTIN_DESCRIPTIONS else candidate.description or '')
        mode = msg('Oscuro') if candidate.mode == 'dark' else msg('Claro')
        state = (msg('Tema activo') if candidate.to_dict() == self.manager.current.to_dict()
                 else msg('Vista previa sin aplicar'))
        name = '' if key in _BUILTIN_NAMES else '\n' + candidate.name
        self.metadata.setText(state + ' · ' + mode + name + ('\n' + description if description else ''))
        self._refresh_apply()
        return True

    def _refresh_apply(self, *_):
        if not hasattr(self, 'apply_button'):
            return
        self.apply_button.setEnabled(not self._applying and self._preview_ready and
                                     (not self.manager.recovery_issue or self.recover.isChecked()))

    def _clear_feedback(self):
        self.feedback.clear()
        self.feedback.hide()
        self.details.clear()
        self.details.hide()

    def _show_error(self, message, error):
        self.feedback.setText(message)
        self.feedback.show()
        issues = getattr(error, 'issues', ())
        self.details.setPlainText('\n'.join(str(issue) for issue in issues) if issues else str(error))
        self.details.show()
        self.details.setFocus(Qt.FocusReason.OtherFocusReason)
        self.scroll.ensureWidgetVisible(self.details, 0, 12)

    def open_creation_guide(self):
        from .theme_creation_dialog import ThemeCreationDialog
        try:
            guide = ThemeCreationDialog(self.candidate, self)
        except ThemeValidationError as error:
            self._show_error(msg('No se pudo preparar la especificación. No se ha aplicado ningún cambio.'), error)
            return
        result = guide.exec()
        self.activateWindow()
        guide.deleteLater()
        if result == QDialog.DialogCode.Accepted:
            # The guide requests the same bounded picker/import/preview path.
            # It has no access to the preference manager or Apply operation.
            self.import_button.setFocus(Qt.FocusReason.OtherFocusReason)
            self.choose_file()
        else:
            self.guide_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, str(msg('Importar tema JSON')), '',
            str(msg('Tema de SORTH (*.sorth-theme.json *.json)')))
        if path:
            self.import_file(path)

    def import_file(self, path):
        """Bounded local read only. The runtime owns copying on explicit Apply."""
        try:
            candidate = load_theme_file(path)
        except (OSError, ThemeValidationError) as error:
            self._show_error(msg('No se importó el tema. Revisa el archivo; el tema activo no ha cambiado.'), error)
            return False
        self._clear_feedback()
        if not self._show_candidate(candidate, 'custom'):
            return False
        self._choices['custom'] = candidate
        self._populate_selector()
        self.feedback.setText(msg('Archivo válido. La vista previa está lista; pulsa Aplicar para guardar una copia local.'))
        self.feedback.show()
        self.scroll.ensureWidgetVisible(self.selector, 0, 12)
        return True

    def restore_original(self):
        self._clear_feedback()
        if not self._show_candidate(self._choices['original'], 'original'):
            return
        with QSignalBlocker(self.selector):
            self.selector.setCurrentIndex(self.selector.findData('original'))
        self.feedback.setText(msg('Original claro está en vista previa. Pulsa Aplicar para restaurarlo.'))
        self.feedback.show()
        self.scroll.ensureWidgetVisible(self.selector, 0, 12)

    def apply_candidate(self):
        if self._applying or not self.apply_button.isEnabled():
            return
        self._applying = True
        self._refresh_apply()
        try:
            candidate = validate_theme(self.candidate.to_dict())
            self.manager.save_and_apply(candidate, key=self.candidate_key,
                                        recover=self.recover.isChecked())
        except theme.ThemeApplicationError as error:
            self._show_candidate()
            self._show_error(msg('El tema se guardó, pero la interfaz no pudo actualizarse por completo. Reinicia SORTH para terminar de aplicarlo.'), error)
        except (ThemePersistenceError, ThemeValidationError, OSError) as error:
            self._show_error(msg('No se pudo aplicar el tema. El tema anterior sigue activo. Puedes volver a intentarlo.'), error)
        else:
            self.accept()
        finally:
            self._applying = False
            self._refresh_apply()

    def _scroll_to_focus(self, previous, focused):
        if (self.isVisible() and focused is not None
                and self.scroll.widget().isAncestorOf(focused)):
            self._reveal_after_reflow()
            self._focus_reveal_timer.start(0)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.LayoutRequest,
                            QEvent.Type.FontChange, QEvent.Type.StyleChange):
            # Native text wrapping, footer stacking and preview column changes
            # may finish after the dialog's own resize event. Coalesce their
            # settled geometry without changing the existing keyboard focus.
            self._focus_reveal_timer.start(0)
        return super().eventFilter(watched, event)

    def _reveal_after_reflow(self):
        focused = QApplication.focusWidget()
        if (not self.isVisible() or focused is None or not focused.isVisible()
                or not self.scroll.widget().isAncestorOf(focused)):
            return
        viewport = self.scroll.viewport()
        rect = focused.rect().translated(focused.mapTo(viewport, focused.rect().topLeft()))
        visible = viewport.rect()
        if visible.contains(rect):
            return
        # A long selectable label/table may be taller than the viewport.
        # Keep its visible center as the usable target.
        if rect.height() > visible.height() and visible.contains(rect.center()):
            return
        # Like the theme creation guide, reveal the whole native frame.
        # ensureWidgetVisible uses QLineEdit's cursor rectangle and can leave
        # its bottom border clipped on first focus in a compact 20pt layout.
        center = focused.mapTo(self.scroll.widget(), focused.rect().center())
        self.scroll.ensureVisible(center.x(), center.y(), 0,
                                  min(viewport.height() // 2,
                                      focused.height() // 2 + 12))

    def _retranslate_details(self, *_):
        self.details.setAccessibleName(str(msg('Detalles del error de tema')))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'scroll'):
            compact = self.height() < 520
            self.layout().setContentsMargins(*((8, 8, 8, 8) if compact else (12, 12, 12, 12)))
            self.layout().setSpacing(6 if compact else 10)
