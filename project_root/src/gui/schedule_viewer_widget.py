"""Read-only schedule consultation with consistent filters and stable row identities."""

import re
from dataclasses import replace
import unicodedata

from PyQt6 import sip
from PyQt6.QtWidgets import (
    QVBoxLayout, QHeaderView, QHBoxLayout, QFrame, QMenu, QScrollArea
)
from PyQt6.QtCore import QCoreApplication, QEvent, Qt, pyqtSignal, QSignalBlocker
from PyQt6.QtGui import (
    QColor
)

from .theme import COLORS
from .schedule_grid_delegate import (
    COURSE_CARD_ROLE, GRID_BLOCK_ROLE, CourseCard, ScheduleGridDelegate,
    COURSE_CONFLICT_ACCENT, COURSE_CONFLICT_FILL,
)
from ..scheduling.course_style import course_style
from ..scheduling.time_model import TimeModel
from ..scheduling.quality import QualitySnapshot, analyze_quality
from ..scheduling.schedule_grid import build_schedule_grid, course_color, COURSE_COLORS, GRID_TEXT_COLOR

from .i18n import msg, plural, language_manager
from .i18n_widgets import (
    QAction, QComboBox, QDialog, QDialogButtonBox, QLabel, QLineEdit, QMessageBox, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QWidget,
    _keep_qt_owners_alive,
)

_DAY_ORDER = {d: i for i, d in enumerate(TimeModel.DAY_ORDER)}


def _search_key(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text).casefold())
                   if not unicodedata.combining(c))


def _natural_key(text):
    return tuple(int(part) if part.isdigit() else part.casefold()
                 for part in re.split(r"(\d+)", str(text)))


class _SortableItem(QTableWidgetItem):
    def __init__(self, text: str, sort_key):
        super().__init__(text)
        self._sort_key = sort_key

    def __lt__(self, other):
        if isinstance(other, _SortableItem):
            return self._sort_key < other._sort_key
        return super().__lt__(other)


class _SessionIdentityHeader(QHeaderView):
    """Keep the session column caption readable without fixing its width.

    Native sectionSizeHint includes the current font, section padding and sort
    indicator allowance. Only this identity column has a content-derived floor;
    wider user sizes and every other column's resize policy remain unchanged.
    """
    def __init__(self, session_column, table):
        self._session_column = session_column
        self._fitting_caption = False
        super().__init__(Qt.Orientation.Horizontal, table)
        self.sectionResized.connect(self._section_resized)
        table.model().headerDataChanged.connect(self._caption_changed)
        language_manager().changed.connect(self._fit_caption)

    def _section_resized(self, column, _old, _new):
        if column == self._session_column:
            self._fit_caption()

    def _caption_changed(self, orientation, first, last):
        if orientation == Qt.Orientation.Horizontal and first <= self._session_column <= last:
            self._fit_caption()

    @_keep_qt_owners_alive
    def _fit_caption(self, *_):
        if sip.isdeleted(self):
            return
        column = self._session_column
        if self._fitting_caption or column >= self.count():
            return
        if self.sectionResizeMode(column) != QHeaderView.ResizeMode.Interactive:
            return
        self._fitting_caption = True
        try:
            required = self.sectionSizeHint(column)
            if self.sectionSize(column) < required:
                self.resizeSection(column, required)
        finally:
            self._fitting_caption = False

    @_keep_qt_owners_alive
    def event(self, event):
        result = super().event(event)
        if sip.isdeleted(self):
            return result
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            # Fit after native style replacement unwinds, using the ordinary
            # layout queue instead of timers or event-loop reentrancy.
            QCoreApplication.postEvent(self, QEvent(QEvent.Type.LayoutRequest))
        elif event.type() in (QEvent.Type.Show, QEvent.Type.LayoutRequest):
            self._fit_caption()
        return result


class ScheduleViewerWidget(QWidget):
    edit_course_requested = pyqtSignal(str)
    manual_assignment_requested = pyqtSignal(str)
    placement_options_requested = pyqtSignal(str)
    group_removed = pyqtSignal(str)
    pin_requested = pyqtSignal(str)
    schedule_cleared = pyqtSignal()
    filters_changed = pyqtSignal()
    _COLOR_PALETTE = [QColor("#" + color) for color in COURSE_COLORS]

    def __init__(self):
        super().__init__()
        self._pin_controls = []
        self._suggestion_controls = []
        self._selection_hints = []
        self._assignments = {}
        self._search_keys = {}
        self._matching_gids = set()
        self._grid_dirty = True
        self._known_gids = set()
        self._groups = {}
        self._name_map = {}
        self._course_colors = {}
        self._classroom_assignments = {}
        self._gid_by_list_row = {}
        self._gid_by_cls_row = {}
        self._time_model = None
        self.summary_data = None
        self._quality_snapshot = None
        self._refreshing = False
        self._init_ui()
        self._clear()
        language_manager().changed.connect(self._request_grid_render)

    def set_suggestion_controls_visible(self, visible):
        for control in self._suggestion_controls:
            control.setVisible(visible)

    def refresh_theme(self):
        """Recolor cached interface brushes without rebuilding schedule data.

        Item identities, filters, selection, sorting and scroll positions remain
        intact. Course fills and conflict cards keep the fixed printable palette;
        their delegate reads the current interface focus color while painting.
        """
        for table in (self.list_table, self.classroom_table):
            with QSignalBlocker(table):
                for row in range(table.rowCount()):
                    for column in range(table.columnCount()):
                        item = table.item(row, column)
                        if item and item.data(Qt.ItemDataRole.UserRole) not in self._assignments:
                            item.setBackground(QColor(COLORS["danger_soft"]))
                            item.setForeground(QColor(COLORS["danger"]))
            table.viewport().update()
        with QSignalBlocker(self.grid_table):
            for row in range(self.grid_table.rowCount()):
                item = self.grid_table.item(row, 0)
                if item:
                    item.setBackground(QColor(COLORS["primary_soft"]))
                    item.setForeground(QColor(COLORS["on_primary_soft"]))
        self.grid_table.viewport().update()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        header = QHBoxLayout()
        self._summary_label = QLabel()
        self._summary_label.setWordWrap(True)
        header.addWidget(self._summary_label, 1)
        header.addStretch()
        self._btn_summary = QPushButton(msg('Ver resumen'))
        self._btn_summary.clicked.connect(self._show_summary)
        header.addWidget(self._btn_summary)
        self._btn_clear_schedule = QPushButton(msg('Limpiar horario'))
        self._btn_clear_schedule.setObjectName("dangerAction")
        self._btn_clear_schedule.setToolTip(msg('Eliminar todas las asignaciones del horario actual'))
        self._btn_clear_schedule.clicked.connect(self._clear_schedule)
        header.addWidget(self._btn_clear_schedule)
        layout.addLayout(header)

        search_row = QHBoxLayout()
        self._list_search = QLineEdit()
        self._list_search.setPlaceholderText(msg('Código, nombre de curso, grupo o aula'))
        self._list_search.setAccessibleName(msg('Buscar en todo el horario'))
        self._list_search.setClearButtonEnabled(True)
        self._list_search.textChanged.connect(self._apply_filters)
        search_label = QLabel(msg('&Buscar:'))
        search_label.setBuddy(self._list_search)
        search_row.addWidget(search_label)
        search_row.addWidget(self._list_search, 1)
        self._btn_reset_filters = QPushButton(msg('Restablecer filtros'))
        self._btn_reset_filters.clicked.connect(self._reset_filters)
        search_row.addWidget(self._btn_reset_filters)
        layout.addLayout(search_row)
        # One shared query intentionally serves all three consultation views.
        self._cls_search = self._list_search

        filters = QHBoxLayout()
        self._room_filter = self._make_filter(filters, msg('&Aula:'), msg('Filtrar por aula'))
        self._day_filter = self._make_filter(filters, msg('&Día:'), msg('Filtrar por día'))
        self._status_filter = self._make_filter(filters, msg('&Estado:'), msg('Filtrar por estado'))
        self._status_filter.addItem(msg('Todos'), "all")
        self._status_filter.addItem(msg('Asignados'), "assigned")
        self._status_filter.addItem(msg('Sin asignar'), "unassigned")
        filters.addStretch()
        self._result_label = QLabel()
        self._result_label.setWordWrap(True)
        filters.addWidget(self._result_label, 1)
        layout.addLayout(filters)

        self.tabs = QTabWidget()
        self.list_table, self._btn_edit_list, self._btn_remove_list = self._make_list_tab(
            msg('Lista detallada'), [msg('Código'), msg('Nombre del curso'), msg('Grupo / sesión'), msg('Aula'),
                               msg('Día'), msg('Inicio'), msg('Fin'), msg('Estado')], msg('Lista detallada del horario'))

        grid_widget = QWidget()
        grid_layout = QVBoxLayout(grid_widget)
        grid_layout.setContentsMargins(0, 8, 0, 0)
        grid_row = QHBoxLayout()
        grid_label = QLabel(msg('Aula de la &cuadrícula:'))
        self.classroom_selector = QComboBox()
        self.classroom_selector.setAccessibleName(msg('Aula de la cuadrícula'))
        self.classroom_selector.setMinimumContentsLength(12)
        self.classroom_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        grid_label.setBuddy(self.classroom_selector)
        self.classroom_selector.currentTextChanged.connect(self._request_grid_render)
        grid_row.addWidget(grid_label)
        grid_row.addWidget(self.classroom_selector)
        self._grid_hint = QLabel()
        self._grid_hint.setWordWrap(True)
        grid_row.addWidget(self._grid_hint, 1)
        grid_layout.addLayout(grid_row)
        self.grid_table = QTableWidget()
        self.grid_table.setAccessibleName(msg('Cuadrícula semanal por aula'))
        self.grid_table.setAccessibleDescription(msg('Use flechas para recorrer la cuadrícula y Tab para salir. La Lista detallada ofrece las mismas sesiones en filas, con estado y acciones.'))
        self.grid_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.grid_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.grid_table.verticalHeader().setVisible(False)
        self.grid_table.setWordWrap(True)
        self.grid_table.setItemDelegate(ScheduleGridDelegate(self.grid_table))
        grid_layout.addWidget(self.grid_table, 1)
        self.tabs.addTab(grid_widget, msg('Cuadrícula por aula'))

        self.classroom_table, self._btn_edit_cls, self._btn_remove_cls = self._make_list_tab(
            msg('Por aula'), [msg('Aula'), msg('Grupo / sesión'), msg('Nombre del curso'), msg('Día'), msg('Inicio'), msg('Fin')],
            msg('Asignaciones ordenadas por aula'))
        self.tabs.currentChanged.connect(self._on_view_changed)
        layout.addWidget(self.tabs, 1)
        scope = self._export_scope_hint = QLabel(msg('Exportar completo incluye todas las asignaciones. Exportar filtrado usa Buscar, Aula, Día y Estado; no el aula de la cuadrícula.'))
        scope.setWordWrap(True)
        scope.setObjectName("mutedText")
        layout.addWidget(scope)

    def set_compact_layout(self, compact):
        # Reserve room for actual timetable rows at native Windows metrics.
        # Explanatory copy remains available through accessible descriptions and
        # tooltips; every filter and action retains its normal font and target.
        self.layout().setContentsMargins(*(4, 2, 4, 2) if compact else (9, 9, 9, 9))
        for hint, table in zip(self._selection_hints, (self.list_table, self.classroom_table)):
            hint.setVisible(not compact)
            table.setAccessibleDescription(hint.text())
            table.setToolTip(hint.text())
        self._export_scope_hint.setVisible(not compact)
        self.setAccessibleDescription(self._export_scope_hint.text())
        self.setToolTip(self._export_scope_hint.text())
        tab_style = 'QTabBar::tab { padding-top: 7px; padding-bottom: 7px; }' if compact else ''
        if self.tabs.styleSheet() != tab_style:
            self.tabs.setStyleSheet(tab_style)

    def _make_filter(self, layout, text, accessible_name):
        label = QLabel(text)
        combo = QComboBox()
        combo.setAccessibleName(accessible_name)
        combo.setMinimumContentsLength(10)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        label.setBuddy(combo)
        layout.addWidget(label)
        layout.addWidget(combo)
        combo.currentIndexChanged.connect(self._apply_filters)
        return combo

    def _make_list_tab(self, label, headers, accessible_name):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeader(_SessionIdentityHeader(headers.index(msg('Grupo / sesión')), table))
        table.setHorizontalHeaderLabels(headers)
        table.setAccessibleName(accessible_name)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setSortingEnabled(True)
        table.setWordWrap(False)
        table.horizontalHeader().setMinimumSectionSize(65)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos: self._show_context_menu(table, pos, {}))
        layout.addWidget(table, 1)
        actions = QHBoxLayout()
        edit = QPushButton(msg('Editar curso'))
        edit.setToolTip(msg('Editar el curso de la sesión seleccionada; será necesario generar de nuevo'))
        edit.clicked.connect(lambda: self._action_edit(table, {}))
        remove = QPushButton(msg('Quitar del horario'))
        remove.setObjectName("dangerAction")
        remove.setToolTip(msg('Dejar la sesión seleccionada sin asignar'))
        remove.clicked.connect(lambda: self._action_remove(table, {}))
        options = QPushButton(msg('Ver opciones'))
        options.setVisible(False)
        options.setEnabled(False)
        options.clicked.connect(lambda: self.placement_options_requested.emit(self._selected_gid(table)))
        table.itemSelectionChanged.connect(lambda: options.setEnabled(
            self._selected_gid(table) in self._groups and self._selected_gid(table) not in self._assignments))
        self._suggestion_controls.append(options)
        actions.addWidget(options)
        assign = QPushButton(msg('Asignar manualmente'))
        assign.setEnabled(False)
        assign.clicked.connect(lambda: self.manual_assignment_requested.emit(self._selected_gid(table)))
        table.itemSelectionChanged.connect(lambda: assign.setEnabled(self._selected_gid(table) is not None))
        pin = QPushButton(msg('Fijar sesión'))
        self._pin_controls.append(pin)
        pin.setEnabled(False)
        pin.setToolTip(msg('Conservar solo esta sesión al regenerar; no es una preferencia.'))
        pin.clicked.connect(lambda: self.pin_requested.emit(self._selected_gid(table)))
        def update_pin():
            gid = self._selected_gid(table)
            pin.setEnabled(gid in self._assignments)
            pin.setText(msg('Desfijar sesión') if getattr(self._groups.get(gid), 'pinned', False) else msg('Fijar sesión'))
        table.itemSelectionChanged.connect(update_pin)
        actions.addWidget(pin)
        actions.addWidget(assign)
        actions.addWidget(edit)
        actions.addWidget(remove)
        actions.addStretch()
        hint = QLabel(msg('Seleccione una fila para editar o quitar.'))
        hint.setWordWrap(True)
        hint.setObjectName("mutedText")
        self._selection_hints.append(hint)
        table.setAccessibleDescription(hint.text())
        table.setToolTip(hint.text())
        actions.addWidget(hint)
        layout.addLayout(actions)
        details = QLabel("")
        details.setWordWrap(True)
        details.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        details.setVisible(False)
        details.setAccessibleName(msg('Motivo y excepciones de la sesión seleccionada'))
        layout.addWidget(details)
        def update_details():
            gid = self._selected_gid(table)
            group = self._groups.get(gid)
            details.setText((msg('Excepción manual confirmada: laboratorio en aula regular.') if group.lab_override
                             else msg(group.unassigned_reason) if gid not in self._assignments else "") if group else "")
            details.setVisible(bool(details.text()))
        table.itemSelectionChanged.connect(update_details)
        table.itemSelectionChanged.connect(self._update_actions)
        self.tabs.addTab(page, label)
        return table, edit, remove

    def _clear(self):
        self._refreshing = True
        self._assignments = {}
        self._search_keys = {}
        self._matching_gids = set()
        self._grid_dirty = True
        self._known_gids = set()
        self._groups = {}
        self._name_map = {}
        self._course_colors = {}
        self._classroom_assignments = {}
        self._gid_by_list_row.clear()
        self._gid_by_cls_row.clear()
        self._time_model = None
        self.summary_data = None
        self._quality_snapshot = None
        self.list_table.setRowCount(0)
        self.classroom_table.setRowCount(0)
        self.grid_table.clearSpans()
        self.grid_table.setRowCount(0)
        self.grid_table.setColumnCount(0)
        self.classroom_selector.clear()
        self._room_filter.clear()
        self._room_filter.addItem(msg('Todas'), None)
        self._day_filter.clear()
        self._day_filter.addItem(msg('Todos'), None)
        self._list_search.clear()
        self._status_filter.setCurrentIndex(0)
        self._refreshing = False
        self._summary_label.setText(msg('Genere un horario para consultar sus sesiones y exportar los resultados.'))
        self._grid_hint.clear()
        self._btn_summary.setEnabled(False)
        self._btn_clear_schedule.setEnabled(False)
        self._apply_filters()

    def display_schedule(self, assignments: dict, time_model: TimeModel,
                         groups=None, course_name_by_code: dict = None, classrooms=None):
        self._clear()
        self._refreshing = True
        self._time_model = time_model
        self._assignments = dict(assignments or {})
        groups = list(groups or [])
        self._quality_snapshot = QualitySnapshot.capture(assignments or {}, groups, time_model, classrooms)
        self._groups = {g.group_id: g for g in groups}
        self._known_gids = set(self._assignments) | {g.group_id for g in groups}
        course_name_by_code = course_name_by_code or {}
        self._name_map = {g.group_id: g.course_name for g in groups if g.course_name}
        for gid in self._known_gids:
            self._name_map.setdefault(gid, course_name_by_code.get(self._code(gid), ""))
        codes = sorted({self._code(gid) for gid in self._known_gids})
        self._course_colors = {code: QColor("#" + course_color(code))
                               for code in codes}
        self._refresh_assignments()
        for classroom in sorted(self._classroom_assignments, key=_natural_key):
            self._room_filter.addItem(classroom, classroom)
        for day in time_model.days:
            self._day_filter.addItem(msg(day), time_model.to_day_index(day))
        self._refreshing = False
        self._display_list(self._assignments, time_model)
        self._display_classroom_view(self._assignments, time_model)
        self._display_grid_selector(list(self._classroom_assignments))
        self._update_summary(self._assignments)
        self._apply_filters()

    @staticmethod
    def _code(gid):
        return gid.rsplit("-G", 1)[0]

    def _refresh_assignments(self):
        # Domain text only: independent of language and pinned presentation marks.
        # Rebuild when schedule/name/room data changes, never per keystroke.
        self._search_keys = {
            gid: _search_key(" ".join((gid, self._name_map.get(gid, ""),
                                      self._assignments.get(gid, ("",))[0])))
            for gid in self._known_gids
        }
        self._classroom_assignments = {}
        for gid, (room, day, start, end) in self._assignments.items():
            self._classroom_assignments.setdefault(room, []).append((gid, day, start, end))

    def _set_table_rows(self, table, rows, name_col, widths):
        selected_gid = self._selected_gid(table)
        selected_column = max(0, table.currentColumn())
        sort_col = table.horizontalHeader().sortIndicatorSection()
        sort_order = table.horizontalHeader().sortIndicatorOrder()
        table.setSortingEnabled(False)
        table.setRowCount(0)
        table.setRowCount(len(rows))
        for row, (gid, values, sort_keys) in enumerate(rows):
            for col, (value, sort_key) in enumerate(zip(values, sort_keys)):
                item = _SortableItem(value, sort_key)
                item.setData(Qt.ItemDataRole.UserRole, gid)
                item.setToolTip(value)
                group = self._groups.get(gid)
                if group and group.lab_override:
                    item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, msg('Excepción manual confirmada: laboratorio en aula regular.'))
                elif group and gid not in self._assignments and group.unassigned_reason:
                    item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, msg(group.unassigned_reason))
                if gid not in self._assignments:
                    item.setBackground(QColor(COLORS["danger_soft"]))
                    item.setForeground(QColor(COLORS["danger"]))
                table.setItem(row, col, item)
        header = table.horizontalHeader()
        for col, width in enumerate(widths):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            table.setColumnWidth(col, width)
        header.setSectionResizeMode(name_col, QHeaderView.ResizeMode.Stretch)
        table.setSortingEnabled(True)
        table.sortItems(max(0, sort_col), sort_order)
        table.clearSelection()
        table.setCurrentItem(None)
        for row in range(table.rowCount()):
            if table.item(row, 0).data(Qt.ItemDataRole.UserRole) == selected_gid:
                table.setCurrentCell(row, selected_column)
                break

    def _display_list(self, assignments, tm, unassigned_groups=None, course_name_by_code=None):
        rows = []
        for gid in sorted(self._known_gids, key=_natural_key):
            assigned = gid in assignments
            room, day, start, end = assignments.get(gid, ("—", None, None, None))
            day_name = msg(tm.to_day_name(day)) if day is not None else "—"
            values = [self._code(gid), self._name_map.get(gid, ""), gid, room, day_name,
                      TimeModel.minutes_to_hhmm(start) if assigned else "—",
                      TimeModel.minutes_to_hhmm(end) if assigned else "—",
                      (msg('Excepción manual LAB') if getattr(self._groups.get(gid), 'lab_override', False) else msg('Asignado')) if assigned else msg('Sin asignar')]
            if getattr(self._groups.get(gid), "pinned", False):
                values[-1] = msg("Fijada · {state}", state=values[-1])
            keys = [_natural_key(v) for v in values]
            keys[4:7] = [day if assigned else 999, start if assigned else 9999, end if assigned else 9999]
            rows.append((gid, values, keys))
        self._set_table_rows(self.list_table, rows, 1, [90, 230, 135, 90, 105, 75, 75, 100])
        self._gid_by_list_row = {r: self.list_table.item(r, 0).data(Qt.ItemDataRole.UserRole)
                                 for r in range(self.list_table.rowCount())}

    def _display_classroom_view(self, assignments, tm):
        rows = []
        for gid, (room, day, start, end) in assignments.items():
            values = [room, gid, self._name_map.get(gid, ""), msg(tm.to_day_name(day)),
                      TimeModel.minutes_to_hhmm(start), TimeModel.minutes_to_hhmm(end)]
            keys = [_natural_key(v) for v in values]
            if getattr(self._groups.get(gid), "pinned", False):
                values[2] = msg("Fijada · {state}", state=values[2])
            # Secondary ordering remains chronological within a classroom.
            keys[0] = (_natural_key(room), day, start, _natural_key(gid))
            keys[3:] = [day, start, end]
            rows.append((gid, values, keys))
        self._set_table_rows(self.classroom_table, rows, 2, [100, 150, 270, 115, 90, 90])
        self._gid_by_cls_row = {r: self.classroom_table.item(r, 0).data(Qt.ItemDataRole.UserRole)
                                for r in range(self.classroom_table.rowCount())}

    def _display_grid_selector(self, classrooms):
        current = self.classroom_selector.currentText()
        self.classroom_selector.blockSignals(True)
        self.classroom_selector.clear()
        # Retain a selected empty classroom after its final session is removed.
        # Otherwise a locked global filter would label another room's grid.
        classrooms = set(classrooms)
        if self._room_filter.currentData() is not None:
            classrooms.add(self._room_filter.currentData())
        self.classroom_selector.addItems(sorted(classrooms, key=_natural_key))
        if current in classrooms:
            self.classroom_selector.setCurrentText(current)
        self.classroom_selector.blockSignals(False)
        self._grid_dirty = True

    def _request_grid_render(self, *_):
        self._grid_dirty = True
        if self.tabs.currentIndex() == 1:
            self._render_grid(self.classroom_selector.currentText())

    def _on_view_changed(self, *_):
        if self.tabs.currentIndex() == 1 and self._grid_dirty:
            self._render_grid(self.classroom_selector.currentText())
        self._update_result_label()

    def _render_grid(self, classroom):
        if self._refreshing or self._time_model is None:
            return
        self._grid_dirty = False
        tm = self._time_model
        entries = [entry for entry in self._classroom_assignments.get(classroom, [])
                   if entry[0] in self._matching_gids]
        grid = build_schedule_grid(entries, tm.day_start, tm.day_end)
        table = self.grid_table
        selected_block = (table.currentItem().data(GRID_BLOCK_ROLE)
                          if table.currentItem() and table.selectedItems() else None)
        table.clearSpans()
        table.clear()
        table.setRowCount(len(grid.boundaries) - 1)
        table.setColumnCount(len(tm.days) + 1)
        table.setHorizontalHeaderLabels([msg('Hora')] + [msg(day) for day in tm.days])
        for row, start in enumerate(grid.boundaries[:-1]):
            item = QTableWidgetItem(TimeModel.minutes_to_hhmm(start))
            item.setBackground(QColor(COLORS["primary_soft"]))
            item.setForeground(QColor(COLORS["on_primary_soft"]))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(f"{TimeModel.minutes_to_hhmm(start)}–{TimeModel.minutes_to_hhmm(grid.boundaries[row + 1])}")
            table.setItem(row, 0, item)
            table.setRowHeight(row, max(28, round(42 * (grid.boundaries[row + 1] - start) / 30)))
        for block in grid.blocks:
            if block.day not in tm.index_to_day:
                continue
            parts = []
            sections = []
            for gid, day, start, end in block.entries:
                display_gid = msg("Fijada · {state}", state=gid) if getattr(self._groups.get(gid), "pinned", False) else gid
                times = f"{TimeModel.minutes_to_hhmm(start)}–{TimeModel.minutes_to_hhmm(end)}"
                name = self._name_map.get(gid, '')
                sections.append((str(display_gid), times, name))
                parts.append(f"{display_gid}\n"
                             f"{times}\n{name}")
            conflict = len(block.entries) > 1
            text = (msg('Conflicto de aula\n') if conflict else "") + "\n\n".join(parts)
            item = QTableWidgetItem(text)
            item.setToolTip(text)
            item.setData(Qt.ItemDataRole.UserRole, tuple(entry[0] for entry in block.entries))
            # One session can appear on both sides of an overlapping session.
            # IDs alone would select the last matching segment after a redraw.
            block_identity = (block.day, grid.boundaries[block.row],
                              grid.boundaries[block.row + block.span],
                              tuple(entry[0] for entry in block.entries))
            item.setData(GRID_BLOCK_ROLE, block_identity)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, text)
            item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, text)
            item.setData(COURSE_CARD_ROLE, CourseCard(
                course_style(self._code(block.entries[0][0])), tuple(sections),
                str(msg('Conflicto de aula\n')).strip() if conflict else ""))
            item.setBackground(QColor(COURSE_CONFLICT_FILL) if conflict else
                               self._course_colors[self._code(block.entries[0][0])])
            item.setForeground(QColor(COURSE_CONFLICT_ACCENT) if conflict else QColor("#" + GRID_TEXT_COLOR))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            col = tm.days.index(tm.to_day_name(block.day)) + 1
            table.setItem(block.row, col, item)
            if selected_block is not None and block_identity == selected_block:
                table.setCurrentItem(item)
            if block.span > 1:
                table.setSpan(block.row, col, block.span, 1)
            # Short sessions still need room for their exact time and course label.
            line_height = table.fontMetrics().height()
            minimum = min(280, (4 * line_height + 25) * len(block.entries)
                          + (line_height + 6 if conflict else 0))
            height = sum(table.rowHeight(r) for r in range(block.row, block.row + block.span))
            if height < minimum:
                table.setRowHeight(block.row, table.rowHeight(block.row) + minimum - height)
        header = table.horizontalHeader()
        header.setMinimumSectionSize(65)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 65)
        for col in range(1, table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            day = tm.to_day_index(tm.days[col - 1])
            table.setColumnHidden(col, self._day_filter.currentData() not in (None, day))
        conflicts = sum(len(block.entries) > 1 for block in grid.blocks)
        if entries:
            suffix = msg(' · {p1} tramo(s) con conflicto', p1=conflicts) if conflicts else ""
            self._grid_hint.setText(msg('{p0} sesiones{p2}. Horas exactas en cada bloque; detalle completo al señalarlo.', p0=len(entries), p2=suffix))
        else:
            self._grid_hint.setText(msg('Sin sesiones para esta aula y estos filtros.'))
        self._update_result_label()

    def _filter_spec(self):
        return (self._status_filter.currentData(), self._room_filter.currentData(),
                self._day_filter.currentData(),
                tuple(_search_key(self._list_search.text().strip()).split()))

    def _matches_gid(self, gid, spec=None):
        status, room, day, words = self._filter_spec() if spec is None else spec
        assignment = self._assignments.get(gid)
        if status == "assigned" and assignment is None:
            return False
        if status == "unassigned" and assignment is not None:
            return False
        if room is not None and (assignment is None or assignment[0] != room):
            return False
        if day is not None and (assignment is None or assignment[1] != day):
            return False
        return all(word in self._search_keys.get(gid, "") for word in words)

    def _apply_filters(self, *_):
        if self._refreshing or not hasattr(self, "classroom_table"):
            return
        spec = self._filter_spec()
        self._matching_gids = {gid for gid in self._known_gids if self._matches_gid(gid, spec)}
        for table in (self.list_table, self.classroom_table):
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                hidden = item.data(Qt.ItemDataRole.UserRole) not in self._matching_gids
                if table.isRowHidden(row) != hidden:
                    table.setRowHidden(row, hidden)
            if table.currentRow() >= 0 and table.isRowHidden(table.currentRow()):
                table.clearSelection()
                table.setCurrentItem(None)
        room = self._room_filter.currentData()
        self.classroom_selector.setEnabled(room is None and bool(self._assignments))
        if room is not None:
            self.classroom_selector.blockSignals(True)
            self.classroom_selector.setCurrentText(room)
            self.classroom_selector.blockSignals(False)
        self._request_grid_render()
        self._btn_reset_filters.setEnabled(bool(self._list_search.text()) or
                                           any(combo.currentIndex() > 0 for combo in
                                               (self._room_filter, self._day_filter, self._status_filter)))
        self._update_actions()
        self._update_result_label()
        self.filters_changed.emit()

    def export_filter_description(self):
        """Localized PDF context; never translate data or include the grid selector."""
        day = self._day_filter.currentData()
        return {
            str(msg('Buscar')): self._list_search.text() or str(msg('(sin búsqueda)')),
            str(msg('Aula')): self._room_filter.currentData() or str(msg('Todas')),
            str(msg('Día')): str(msg(self._time_model.to_day_name(day))) if day is not None else str(msg('Todos')),
            str(msg('Estado')): str(msg({'all': 'Todos', 'assigned': 'Asignados',
                       'unassigned': 'Sin asignar'}[self._status_filter.currentData()])),
        }

    def filtered_assignments(self):
        """A copy of assigned sessions matching the shared consultation filters.

        The grid's local classroom selector and current tab do not narrow this
        scope. Use the shared Aula filter when exporting a single classroom.
        """
        spec = self._filter_spec()
        return {gid: value for gid, value in self._assignments.items()
                if self._matches_gid(gid, spec)}

    def _filter_list(self, text):
        if self._list_search.text() == text:
            self._apply_filters()
        else:
            self._list_search.setText(text)

    def _filter_cls(self, text):
        self._filter_list(text)

    def _reset_filters(self):
        self._refreshing = True
        self._list_search.clear()
        for combo in (self._room_filter, self._day_filter, self._status_filter):
            combo.setCurrentIndex(0)
        self._refreshing = False
        self._apply_filters()
        self._list_search.setFocus()

    def _update_result_label(self, *_):
        if not hasattr(self, "classroom_table"):
            return
        index = self.tabs.currentIndex()
        if index == 1:
            room = self.classroom_selector.currentText()
            visible = sum(gid in self._matching_gids and data[0] == room for gid, data in self._assignments.items())
            total = len(self._assignments)
        else:
            table = self.list_table if index == 0 else self.classroom_table
            visible = sum(not table.isRowHidden(r) for r in range(table.rowCount()))
            total = table.rowCount()
        text = plural('result_count', total, visible=visible)
        if total and not visible:
            text += msg('. No hay coincidencias; cambie o restablezca los filtros.')
        if index != 0 and self._status_filter.currentData() == "unassigned":
            text += msg(' Consulte las sesiones sin asignar en Lista detallada.')
        self._result_label.setText(text)

    @staticmethod
    def _selected_gid(table):
        row = table.currentRow()
        if row < 0 or table.isRowHidden(row) or not table.selectedItems():
            return None
        item = table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _update_actions(self):
        if not hasattr(self, "_btn_edit_cls"):
            return
        for table, edit, remove in ((self.list_table, self._btn_edit_list, self._btn_remove_list),
                                    (self.classroom_table, self._btn_edit_cls, self._btn_remove_cls)):
            gid = self._selected_gid(table)
            edit.setEnabled(gid is not None)
            remove.setEnabled(gid in self._assignments if gid else False)

    def _show_context_menu(self, table, pos, gid_map):
        row = table.rowAt(pos.y())
        if row < 0:
            return
        table.setCurrentCell(row, 0)
        gid = self._selected_gid(table)
        if not gid:
            return
        menu = QMenu(self)
        edit = QAction(msg('Editar curso {p1}', p1=self._code(gid)), menu)
        remove = QAction(msg('Quitar del horario'), menu)
        remove.setEnabled(gid in self._assignments)
        edit.triggered.connect(lambda: self.edit_course_requested.emit(self._code(gid)))
        remove.triggered.connect(lambda: self._confirm_remove_group(gid))
        menu.addAction(edit)
        menu.addAction(remove)
        menu.exec(table.viewport().mapToGlobal(pos))

    def _action_edit(self, table, gid_map):
        gid = self._selected_gid(table)
        if gid:
            self.edit_course_requested.emit(self._code(gid))

    def _action_remove(self, table, gid_map):
        gid = self._selected_gid(table)
        if gid in self._assignments:
            self._confirm_remove_group(gid)

    def set_pin_controls_visible(self, visible):
        for control in self._pin_controls:
            control.setVisible(visible)

    def refresh_pin_marks(self):
        selected = [self._selected_gid(table) for table in (self.list_table, self.classroom_table)]
        self._display_list(self._assignments, self._time_model)
        self._display_classroom_view(self._assignments, self._time_model)
        for table, gid in zip((self.list_table, self.classroom_table), selected):
            for row in range(table.rowCount()):
                if table.item(row, 0).data(Qt.ItemDataRole.UserRole) == gid:
                    table.setCurrentCell(row, 0)
                    break
        self._apply_filters()

    def _confirm_remove_group(self, gid):
        if getattr(self._groups.get(gid), 'pinned', False):
            QMessageBox.information(self, msg('Sesión fijada'), msg('Desfije la sesión antes de cambiar su asignación.'))
            return
        answer = QMessageBox.question(self, msg('Quitar sesión del horario'),
                                      msg('¿Quitar {p1} del horario?\nLa sesión quedará sin asignar y no se exportará.', p1=gid),
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self._remove_group(gid)

    def _remove_group(self, gid):
        handler = getattr(self, 'remove_handler', None)
        if handler is not None:
            return handler(gid)
        if gid not in self._assignments:
            return
        del self._assignments[gid]
        self.group_removed.emit(gid)
        self._refresh_assignments()
        self._display_list(self._assignments, self._time_model)
        self._display_classroom_view(self._assignments, self._time_model)
        self._display_grid_selector(list(self._classroom_assignments))
        self._update_summary(self._assignments)
        self._apply_filters()

    def _clear_schedule(self):
        if not self._known_gids:
            return
        if any(getattr(g, "pinned", False) for g in self._groups.values()):
            QMessageBox.information(self, msg("Sesión fijada"), msg("Desfije las sesiones antes de limpiar el horario."))
            return
        answer = QMessageBox.question(self, msg('Limpiar horario'),
                                      msg('¿Eliminar todas las asignaciones del horario actual?\nSe conservarán los cursos y las aulas para generar un horario nuevo.'),
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            handler = getattr(self, 'clear_handler', None)
            if handler is not None:
                return handler()
            self._clear()
            self.schedule_cleared.emit()

    def _update_summary(self, assignments, unassigned_groups=None):
        unassigned = self._known_gids - assignments.keys()
        cls_load, day_load = {}, {}
        for room, day, _, _ in assignments.values():
            cls_load[room] = cls_load.get(room, 0) + 1
            name = self._time_model.to_day_name(day)
            day_load[name] = day_load.get(name, 0) + 1
        self.summary_data = {
            "total": len(assignments), "unassigned": len(unassigned),
            "classrooms": len(cls_load), "courses": len({self._code(gid) for gid in assignments}),
            "cls_load": cls_load, "day_load": day_load,
            "unassigned_list": [(self._code(gid), self._name_map.get(gid, ""), gid)
                                 for gid in sorted(unassigned, key=_natural_key)]}
        if self._quality_snapshot is not None:
            # Reuse captured metadata after removals; filters never enter analysis.
            snapshot = replace(self._quality_snapshot, assignments=tuple(
                (gid, *slot) for gid, slot in sorted(assignments.items())))
            self.summary_data["quality"] = analyze_quality(snapshot)
        self._summary_label.setText(msg('{p0} sesiones asignadas · {p2} sin asignar · {p4} aulas utilizadas', p0=len(assignments), p2=len(unassigned), p4=len(cls_load)))
        self._btn_summary.setEnabled(bool(self._known_gids))
        self._btn_clear_schedule.setEnabled(bool(self._known_gids))

    def _show_summary(self):
        if self.summary_data:
            SummaryDialog(self, self.summary_data).exec()


class SummaryDialog(QDialog):

    def __init__(self, parent, data: dict):
        super().__init__(parent)
        self.setWindowTitle(msg('Resumen del Horario'))
        self.setModal(True)
        self.resize(820, 680)
        self._data = data
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # --- KPI cards ---
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(8)
        assigned   = self._data["total"]
        unassigned = self._data["unassigned"]
        total      = assigned + unassigned
        pct        = int(assigned / total * 100) if total else 0

        for label, value, tone in [
            (msg('Sesiones asignadas'),  f"{assigned} / {total}  ({pct}%)", "success"),
            (msg('Sin asignar'),       str(unassigned),                   "danger" if unassigned else "success"),
            (msg('Aulas utilizadas'),  str(self._data["classrooms"]),     "primary"),
            (msg('Cursos programados'),str(self._data["courses"]),        "accent"),
        ]:
            card = QFrame()
            card.setObjectName("summaryCard")
            card.setProperty("tone", tone)
            cl = QVBoxLayout(card)
            cl.setSpacing(2)
            vl = QLabel(value)
            vl.setObjectName("summaryValue")
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ll = QLabel(label)
            ll.setObjectName("summaryCaption")
            ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(vl)
            cl.addWidget(ll)
            kpi_row.addWidget(card)
        layout.addLayout(kpi_row)

        quality = self._data.get("quality")
        if quality:
            self._add_quality(layout, quality)

        # --- Load by day ---
        if not quality and self._data.get("day_load"):
            layout.addWidget(self._section_label(msg('Sesiones por día')))
            day_table = self._make_table([msg('Día'), msg('Sesiones asignadas')],
                                         [(msg(day), count) for day, count in sorted(self._data["day_load"].items(), key=lambda item: _DAY_ORDER.get(item[0], 99))])
            layout.addWidget(day_table)

        # --- Load by classroom ---
        if not quality and self._data.get("cls_load"):
            layout.addWidget(self._section_label(msg('Sesiones por aula')))
            cls_table = self._make_table(
                [msg('Aula'), msg('Sesiones asignadas')],
                sorted(self._data["cls_load"].items(), key=lambda x: -x[1])
            )
            layout.addWidget(cls_table)

        # --- Unassigned groups ---
        if self._data.get("unassigned_list"):
            lbl = self._section_label(msg('Sesiones sin asignar (ver Lista detallada)'))
            lbl.setObjectName("dangerText")
            layout.addWidget(lbl)
            ua_table = self._make_table(
                [msg('Código'), msg('Nombre'), msg('Grupo')],
                self._data["unassigned_list"]
            )
            layout.addWidget(ua_table)

        content = QWidget()
        content.setLayout(layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    @staticmethod
    def _fraction(numerator, denominator):
        return (f"{numerator} / {denominator} ({100 * numerator / denominator:.1f}%)"
                if denominator else msg('No aplica'))

    def _explanation(self, layout, text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setObjectName("mutedText")
        layout.addWidget(label)

    def _add_quality(self, layout, quality):
        layout.addWidget(self._section_label(msg('Calidad del horario completo')))
        self._explanation(layout, msg('Los filtros no cambian estos indicadores. Son descriptivos: no validan restricciones ni demuestran un óptimo.'))
        original = quality['coverage']['original_groups']
        self._explanation(layout, msg('Grupos originales: {complete} completos, {partial} parciales, {pending} pendientes y {unknown} desconocidos, de {total}. Las preferencias cuentan cada sesión dividida por separado.',
                                      complete=original['fully_assigned'], partial=original['partially_assigned'],
                                      pending=original['unassigned'], unknown=original['unknown'], total=original['total']))
        rows = []
        for key, label in [('day', msg('Día preferido')), ('time', msg('Hora preferida')), ('room', msg('Aula preferida'))]:
            value = quality['preferences'][key]
            rows.append((label, self._fraction(value['satisfied'], value['evaluated']),
                         value['pending'], value['unknown'], value['absent']))
        layout.addWidget(self._make_table(
            [msg('Preferencia'), msg('Cumplidas'), msg('Pendientes'), msg('Desconocidas'), msg('Sin preferencia')], rows))
        self._explanation(layout, msg('Coincidencia exacta de día, hora de inicio y aula. El denominador incluye sólo preferencias asignadas y conocidas; pendientes, desconocidas y ausentes se muestran aparte. Sin denominador: no aplica.'))
        layout.addWidget(self._section_label(msg('Distribución de carga por día')))
        layout.addWidget(self._make_table([msg('Día'), msg('Sesiones asignadas'), msg('Minutos de docencia')],
            [(msg(row['name']), row['assigned_sessions'], row['teaching_minutes']) for row in quality['day_load']]))
        self._explanation(layout, msg('Se suman minutos de cada sesión, incluso si son simultáneas. Se incluyen días sin carga; no se presupone que una distribución uniforme sea mejor.'))
        occupancy = quality['occupancy']
        layout.addWidget(self._section_label(msg('Ocupación temporal de aulas')))
        self._explanation(layout, msg('Minutos ocupados únicos / minutos disponibles, descontando almuerzo y exclusiones. Incluye aulas sin uso; no mide asientos ocupados ni compatibilidad de cursos.'))
        layout.addWidget(self._make_table([msg('Aula'), msg('Minutos ocupados / disponibles')],
            [(row['room'], self._fraction(row['occupied_minutes'], row['available_minutes'])) for row in occupancy['rooms']]
            + [(msg('Total'), self._fraction(occupancy['occupied_minutes'], occupancy['available_minutes']))]))
        exceptions = quality['manual_exceptions']
        self._explanation(layout, msg('Excepciones manuales activas de laboratorio / sesiones asignadas: {ratio}. Confirmadas: {ids}. Sin confirmar: {unconfirmed}. No evaluables: {unknown}. Registros inactivos: {inactive}.',
            ratio=self._fraction(len(exceptions['active_ids']), exceptions['assigned_sessions']),
            ids=', '.join(exceptions['active_ids']) or msg('Ninguna'),
            unconfirmed=', '.join(exceptions['unconfirmed_ids']) or msg('Ninguna'),
            unknown=', '.join(exceptions['unknown_ids']) or msg('Ninguna'),
            inactive=', '.join(exceptions['inactive_ids']) or msg('Ninguna')))
        if quality['data_issues']:
            self._explanation(layout, msg('Hay datos desconocidos o incompletos. Los indicadores no sustituyen la revisión de integridad.'))

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
        return lbl

    def _make_table(self, headers: list, rows: list) -> QTableWidget:
        t = QTableWidget(len(rows), len(headers), self)
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setWordWrap(False)
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(val if isinstance(val, str) else str(val))
                item.setToolTip(item.text())
                t.setItem(r, c, item)
        # A deterministic native header height avoids pre-show style size hints
        # clipping the final row once the application's stylesheet is applied.
        header_height = max(40, t.fontMetrics().height() + 24)
        t.horizontalHeader().setFixedHeight(header_height)
        height = min(sum(t.rowHeight(row) for row in range(len(rows)))
                     + header_height + 2 * t.frameWidth() + 4, 260)
        t.setFixedHeight(height)
        return t
