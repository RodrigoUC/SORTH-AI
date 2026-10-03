"""Readable, print-ready schedule exports with stable tabular contracts."""

from math import ceil
from pathlib import Path
from contextlib import contextmanager
import os
import re
import tempfile

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.pagebreak import Break
from copy import copy

from ..scheduling.schedule_grid import (
    COURSE_COLORS, GRID_TEXT_COLOR, build_schedule_grid, course_color,
)
from ..scheduling.time_model import TimeModel


_DETAIL_COLUMNS = [
    "Código Curso", "Nombre Curso", "Grupo", "Aula", "Día", "Hora Inicio", "Hora Fin",
]
_CLASSROOM_COLUMNS = [
    "Aula", "Código Curso", "Nombre Curso", "Grupo", "Día", "Hora Inicio", "Hora Fin",
]
_COLOR_PALETTE = COURSE_COLORS
_HEADER_FILL = PatternFill("solid", fgColor="1967D2")
_HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
_HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
_HOUR_FILL = PatternFill("solid", fgColor="EDF2F7")
_EMPTY_FILL = PatternFill("solid", fgColor="FAFCFE")
_STRIPE_FILL = PatternFill("solid", fgColor="F2F6FB")
_CONFLICT_FILL = PatternFill("solid", fgColor="FCE4D6")
_THIN_BORDER = Border(
    left=Side(style="thin", color="D7E0E9"),
    right=Side(style="thin", color="D7E0E9"),
    top=Side(style="thin", color="D7E0E9"),
    bottom=Side(style="thin", color="D7E0E9"),
)


class ScheduleExporter:
    def __init__(self, time_model: TimeModel):
        self.time_model = time_model

    def to_excel(self, assignments: dict, output_path: str,
                 groups=None, course_name_by_code: dict = None,
                 include_grid: bool = True) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        name_map = self._build_name_map(assignments, groups, course_name_by_code)
        with self._atomic_output(output_path, ".xlsx") as temporary:
            with pd.ExcelWriter(temporary, engine="openpyxl") as writer:
                if include_grid:
                    self._write_grid_sheets(writer, assignments, name_map)
                self._write_detail_sheet(writer, assignments, name_map)
                self._write_by_classroom_sheet(writer, assignments, name_map)

    def to_csv(self, assignments: dict, output_path: str,
               groups=None, course_name_by_code: dict = None) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        name_map = self._build_name_map(assignments, groups, course_name_by_code)
        with self._atomic_output(output_path, ".csv") as temporary:
            self._detail_dataframe(assignments, name_map).to_csv(
                temporary, index=False, encoding="utf-8-sig",
            )

    @staticmethod
    @contextmanager
    def _atomic_output(output_path, suffix):
        """Keep an existing export intact until serialization and flush succeed.

        Close the named temporary file before libraries reopen it (Windows),
        and keep it on the destination filesystem for atomic replacement.
        """
        destination = Path(output_path)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent,
                                             prefix=".sorth-export-", suffix=suffix,
                                             delete=False) as handle:
                temporary = Path(handle.name)
            yield temporary
            with temporary.open("r+b") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def to_pdf(self, assignments: dict, output_path: str,
               groups=None, course_name_by_code: dict = None, *, filtered=False,
               total_assigned=None, pending_count=None, filters=None, labels=None) -> None:
        from .pdf_schedule_writer import write_schedule_pdf
        write_schedule_pdf(
            self, assignments, output_path,
            self._build_name_map(assignments, groups, course_name_by_code),
            groups=groups, filtered=filtered, total_assigned=total_assigned,
            pending_count=pending_count, filters=filters, labels=labels,
        )

    # The seven column names/order and minute strings are kept for downstream
    # consumers. Explicit columns also make an empty export a usable template.
    def _detail_dataframe(self, assignments: dict, name_map: dict) -> pd.DataFrame:
        return pd.DataFrame(
            [self._detail_row(gid, value, name_map)
             for gid, value in sorted(assignments.items(), key=self._detail_sort_key)],
            columns=_DETAIL_COLUMNS,
        )

    def _detail_row(self, gid, value, name_map):
        classroom, day, start_min, end_min = value
        code, group_num = self._group_parts(gid)
        row = {
            "Código Curso": code,
            "Nombre Curso": name_map.get(gid, ""),
            "Grupo": f"{code}-G{group_num}",
            "Aula": classroom,
            "Día": self.time_model.to_day_name(day),
            "Hora Inicio": TimeModel.minutes_to_hhmm(start_min),
            "Hora Fin": TimeModel.minutes_to_hhmm(end_min),
        }
        return {key: self._safe_text(value) for key, value in row.items()}

    def _write_detail_sheet(self, writer, assignments: dict, name_map: dict):
        self._detail_dataframe(assignments, name_map).to_excel(
            writer, sheet_name="Asignaciones", index=False,
        )
        self._style_table(writer.sheets["Asignaciones"], [18, 44, 20, 18, 16, 14, 14])

    def _write_by_classroom_sheet(self, writer, assignments: dict, name_map: dict):
        # Numeric day indices follow the TimeModel, unlike alphabetical labels.
        ordered = sorted(assignments.items(), key=lambda item: (
            self._natural_key(item[1][0]), item[1][1], item[1][2], item[1][3],
            self._natural_key(item[0]), str(item[1][0]), item[0],
        ))
        df = pd.DataFrame(
            [self._detail_row(gid, value, name_map) for gid, value in ordered],
            columns=_CLASSROOM_COLUMNS,
        )
        df.to_excel(writer, sheet_name="Por Aula", index=False)
        self._style_table(writer.sheets["Por Aula"], [18, 18, 44, 20, 16, 14, 14])

    def _style_table(self, ws, widths):
        ws.sheet_view.showGridLines = False
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            self._style_header(cell)
        ws.row_dimensions[1].height = 30
        for column, width in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(column)].width = width
        for row in ws.iter_rows(min_row=2):
            max_lines = 1
            for cell, width in zip(row, widths):
                cell.font = Font(name="Calibri", size=11, color=GRID_TEXT_COLOR)
                cell.alignment = Alignment(vertical="center", wrap_text=True)
                cell.number_format = "@"
                if cell.row % 2 == 0:
                    cell.fill = _STRIPE_FILL
                max_lines = max(max_lines, self._line_count(cell.value, width - 2))
            ws.row_dimensions[row[0].row].height = min(409, max(27, max_lines * 15 + 10))
        self._configure_print(ws, "1:1")

    # One visual sheet per classroom, with exact-minute row boundaries.
    def _write_grid_sheets(self, writer, assignments: dict, name_map: dict):
        by_classroom: dict[str, list] = {}
        for gid, (classroom, day, start, end) in assignments.items():
            by_classroom.setdefault(classroom, []).append((gid, day, start, end))
        course_codes = sorted({self._group_parts(gid)[0] for gid in assignments})
        course_colors = {
            code: course_color(code) for code in course_codes
        }
        used = {"Asignaciones", "Por Aula"}
        for classroom in sorted(by_classroom, key=lambda room: (self._natural_key(room), str(room))):
            room_label = str(classroom) if str(classroom).casefold().startswith("aula ") else f"Aula {classroom}"
            sheet_name = self._safe_sheet_name(room_label, used)
            used.add(sheet_name)
            self._write_single_grid(
                writer, sheet_name, classroom, by_classroom[classroom], name_map, course_colors,
            )

    def _write_single_grid(self, writer, sheet_name, classroom,
                           entries, name_map, course_colors):
        days = self.time_model.days
        # Print only the occupied time range; exact sessions use the same
        # projection as the viewer without pages of leading/trailing blanks.
        grid = build_schedule_grid(
            entries, min(entry[2] for entry in entries), max(entry[3] for entry in entries),
        )
        ws = writer.book.create_sheet(sheet_name)
        n_cols = len(days) + 1
        header_row = 3
        first_data_row = header_row + 1
        ws.sheet_view.showGridLines = False
        ws.freeze_panes = "B4"
        ws.sheet_properties.tabColor = "1967D2"
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n_cols)
        room_label = str(classroom) if str(classroom).casefold().startswith("aula ") else f"Aula {classroom}"
        ws.cell(1, 1, self._safe_text(f"Horario · {room_label}"))
        ws.cell(1, 1).font = Font(name="Calibri", size=16, bold=True, color=GRID_TEXT_COLOR)
        ws.cell(1, 1).alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[1].height = max(34, self._line_count(classroom, 100) * 20)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=n_cols)
        ws.cell(2, 1, "Horas exactas · Un color por curso · CONFLICTO indica sesiones simultáneas")
        ws.cell(2, 1).font = Font(name="Calibri", size=10, color="526577")
        ws.cell(2, 1).alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[2].height = 30
        for column, label in enumerate(["Hora"] + days, 1):
            cell = ws.cell(header_row, column, self._safe_text(label))
            self._style_header(cell)
        ws.row_dimensions[header_row].height = 27
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for row, minute in enumerate(grid.boundaries[:-1], first_data_row):
            cell = ws.cell(row, 1, TimeModel.minutes_to_hhmm(minute))
            cell.fill = _HOUR_FILL
            cell.font = Font(name="Calibri", bold=True, size=10, color=GRID_TEXT_COLOR)
            cell.alignment = center
            cell.border = _THIN_BORDER
            ws.row_dimensions[row].height = 34
            for column in range(2, n_cols + 1):
                cell = ws.cell(row, column)
                cell.fill = _EMPTY_FILL
                cell.alignment = center
                cell.border = _THIN_BORDER

        printable_blocks = []
        for block in grid.blocks:
            day_name = self.time_model.to_day_name(block.day)
            column = days.index(day_name) + 2
            row = block.row + first_data_row
            texts = [self._grid_entry_text(entry, name_map) for entry in block.entries]
            conflict = len(block.entries) > 1
            text = "\n\n".join(texts)
            if conflict:
                text = f"CONFLICTO: {len(block.entries)} sesiones\n\n{text}"
            code = self._group_parts(block.entries[0][0])[0]
            fill = _CONFLICT_FILL if conflict else PatternFill(
                "solid", fgColor=course_colors.get(code, COURSE_COLORS[0]),
            )
            for block_row in range(row, row + block.span):
                ws.cell(block_row, column).fill = fill
            cell = ws.cell(row, column, self._safe_text(text))
            cell.font = Font(name="Calibri", bold=True, size=10,
                             color="9C2F21" if conflict else GRID_TEXT_COLOR)
            cell.alignment = center
            # Excel does not autofit merged cells. Allocate enough total height
            # for wrapped labels, including sub-half-hour and conflict blocks.
            height = ceil((self._line_count(text, 24) * 14 + 12) / block.span)
            for block_row in range(row, row + block.span):
                ws.row_dimensions[block_row].height = min(
                    409, max(ws.row_dimensions[block_row].height, height),
                )
            printable_blocks.append((row, row + block.span - 1, column,
                                     self._line_count(text, 24) * 14 + 12))

        self._paginate_grid(ws, printable_blocks, first_data_row)

        ws.column_dimensions["A"].width = 10
        for column in range(2, n_cols + 1):
            ws.column_dimensions[get_column_letter(column)].width = 27
        self._configure_print(ws, "1:3")

    @staticmethod
    def _paginate_grid(ws, blocks, first_row):
        """Keep merged labels inside each printed page, repeating continuations.

        A conservative 400-point body leaves room for repeated headings and
        margins on landscape A4 even before width scaling. Plan row heights
        before merging: native spreadsheet engines otherwise cut a merged
        label at an automatic page boundary.
        """
        last_row = ws.max_row
        start = first_row
        while start <= last_row:
            chosen = start
            chosen_heights = {}
            for end in range(start, last_row + 1):
                heights = {row: ws.row_dimensions[row].height or 34
                           for row in range(start, end + 1)}
                for top, bottom, _, text_height in blocks:
                    lo, hi = max(start, top), min(end, bottom)
                    if lo <= hi:
                        minimum = min(409, ceil(text_height / (hi - lo + 1)))
                        for row in range(lo, hi + 1):
                            heights[row] = max(heights[row], minimum)
                if sum(heights.values()) > 400 and end > start:
                    break
                chosen, chosen_heights = end, heights
            for row, height in chosen_heights.items():
                ws.row_dimensions[row].height = height
            for top, bottom, column, _ in blocks:
                lo, hi = max(start, top), min(chosen, bottom)
                if lo > hi:
                    continue
                if lo != top:
                    source, target = ws.cell(top, column), ws.cell(lo, column)
                    target.value = source.value
                    target.font = copy(source.font)
                    target.alignment = copy(source.alignment)
                if hi > lo:
                    ws.merge_cells(start_row=lo, start_column=column,
                                   end_row=hi, end_column=column)
            if chosen < last_row:
                ws.row_breaks.append(Break(id=chosen))
            start = chosen + 1

    def _grid_entry_text(self, entry, name_map):
        gid, _, start, end = entry
        parts = [gid, name_map.get(gid, ""),
                 f"{TimeModel.minutes_to_hhmm(start)}–{TimeModel.minutes_to_hhmm(end)}"]
        return "\n".join(str(part) for part in parts if part)

    @staticmethod
    def _style_header(cell):
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = _HEADER_ALIGN
        cell.border = _THIN_BORDER

    @staticmethod
    def _configure_print(ws, repeat_rows):
        ws.print_title_rows = repeat_rows
        ws.print_area = ws.dimensions
        ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_margins = PageMargins(left=0.25, right=0.25, top=0.4, bottom=0.4,
                                      header=0.2, footer=0.2)
        ws.oddFooter.left.text = "SORTH"
        ws.oddFooter.right.text = "Página &P de &N"

    @staticmethod
    def _line_count(value, width):
        return sum(max(1, ceil(len(line) / width)) for line in str(value or "").split("\n"))

    @staticmethod
    def _safe_text(value):
        """Neutralize spreadsheet formula prefixes without altering ordinary text.

        CSV quoting alone does not prevent formula evaluation. A leading
        apostrophe is intentionally retained in both formats for parity, even
        when an importer trims whitespace before interpreting a formula.
        """
        if not isinstance(value, str) or not value:
            return value
        candidate = value.lstrip(" \t\r\n\v\f\ufeff")
        unsafe = value.startswith(("\t", "\r", "\n")) or candidate.startswith(("=", "+", "-", "@"))
        # XML 1.0 cannot encode these pasted control characters. Normalize
        # identically in CSV so both exported tables retain the same values.
        value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", value)
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        return "'" + value if unsafe else value

    @staticmethod
    def _natural_key(value):
        """Human ordering for numbered courses, groups, and classrooms."""
        return tuple((1, int(part)) if part.isdigit() else (0, part.casefold())
                     for part in re.split(r"(\d+)", str(value)))

    def _detail_sort_key(self, item):
        gid, (classroom, day, start, end) = item
        code, group = self._group_parts(gid)
        # Preserve the course/group organization, then show its sessions in
        # weekly order rather than trusting the part suffix or input order.
        return (self._natural_key(code), self._natural_key(group), day, start, end,
                self._natural_key(gid), self._natural_key(classroom), gid)

    @staticmethod
    def _group_parts(gid):
        code, group = gid.rsplit("-G", 1)
        return code, group.split("-P", 1)[0]

    def _build_name_map(self, assignments: dict, groups, course_name_by_code) -> dict:
        name_map = {}
        for group in groups or []:
            if group.course_name:
                name_map[group.group_id] = group.course_name
        course_name_by_code = course_name_by_code or {}
        for gid in assignments:
            if gid not in name_map:
                code = self._group_parts(gid)[0]
                if code in course_name_by_code:
                    name_map[gid] = course_name_by_code[code]
        return name_map

    @staticmethod
    def _safe_sheet_name(name: str, used: set) -> str:
        name = re.sub(r"[\\/*?:\[\]\x00-\x1f]", "-", str(name)).strip("'")
        name = name[:31].rstrip("'") or "Hoja"
        used_names = {item.casefold() for item in used}
        if name.casefold() not in used_names:
            return name
        index = 2
        while True:
            suffix = f"_{index}"
            candidate = f"{name[:31 - len(suffix)]}{suffix}"
            if candidate.casefold() not in used_names:
                return candidate
            index += 1
