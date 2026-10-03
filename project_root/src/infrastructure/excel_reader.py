# src/infrastructure/excel_reader.py

import pandas as pd
import unicodedata
import re
import zipfile
import posixpath
from xml.parsers import expat
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass
from typing import Dict
from openpyxl.xml.constants import XLSX, XLSM, XLTX, XLTM

from ..scheduling.classroom import Classroom
from ..scheduling.course import Course
from ..scheduling.time_model import TimeModel

# Mapping from Excel day abbreviation to full Spanish name
DAY_ABBR = {
    "L": "Lunes",
    "I": "Martes",
    "M": "Miércoles",
    "J": "Jueves",
    "V": "Viernes",
    "S": "Sábado",
}


@dataclass(frozen=True)
class ImportNotice:
    source: str
    parameters: dict

    def render(self, translate=None):
        return translate(self.source, **self.parameters) if translate else self.source.format(**self.parameters)

    def __str__(self):
        return self.render()


def notice(source, **parameters):
    return ImportNotice(source, parameters)


class ExcelImportError(ValueError):
    """Structured messages can be translated by the presentation layer."""

    def __init__(self, messages):
        self.notices = messages if isinstance(messages, list) else [messages]
        self.notices = [item if isinstance(item, ImportNotice) else notice(item) for item in self.notices]
        super().__init__(self.render())

    def render(self, translate=None):
        return "\n".join(item.render(translate) for item in self.notices)


@dataclass
class ExcelImport:
    classrooms: dict
    courses: list
    classroom_course_map: dict
    warnings: list[ImportNotice]


class ImportCancelled(Exception):
    """Cooperative cancellation; never reported as a malformed workbook."""


class ExcelReader:
    # Bound work before openpyxl inflates workbook XML/shared strings. Oversized
    # inputs are rejected, never partially imported or silently truncated.
    MAX_FILE_BYTES = 25 * 1024 * 1024
    MAX_EXPANDED_BYTES = 100 * 1024 * 1024
    MAX_ARCHIVE_MEMBERS = 1000
    MAX_DATA_ROWS = 10000
    MAX_DATA_COLUMNS = 128
    MAX_SHEET_CELLS = 500000

    def _check_workbook_size(self):
        self._checkpoint()
        if self._source_bytes is None:
            # Direct reader callers need the same immutable bytes for the
            # preflight and pandas. The GUI already supplies its snapshot.
            with open(self.file_path, 'rb') as source:
                data = source.read(self.MAX_FILE_BYTES + 1)
            self._checkpoint()
            if len(data) > self.MAX_FILE_BYTES:
                raise ExcelImportError("El libro supera el límite de importación. Divídalo en archivos más pequeños.")
            self._source_bytes = data
        size = len(self._source_bytes)
        if size > self.MAX_FILE_BYTES:
            raise ExcelImportError("El libro supera el límite de importación. Divídalo en archivos más pequeños.")
        with zipfile.ZipFile(self._source()) as archive:
            entries = archive.infolist()
            if (len(entries) > self.MAX_ARCHIVE_MEMBERS or
                    sum(entry.file_size for entry in entries) > self.MAX_EXPANDED_BYTES):
                raise ExcelImportError("El libro supera el límite de importación. Divídalo en archivos más pequeños.")
            self._check_sheet_sizes(archive)

    def _check_sheet_sizes(self, archive):
        """Reject sparse rectangular amplification before pandas/openpyxl load.

        Inspect actual row/cell references rather than trusting the worksheet
        dimension hint. Only the two imported sheets are subject to these
        shape limits; extra sheets retain their existing ignored behavior.
        """
        content_ns = 'http://schemas.openxmlformats.org/package/2006/content-types}'
        content_root = content_ns + 'Types'
        workbook_paths = []
        workbook_defaults = set()
        part_names = set()
        extensions = set()
        def content_type(tag, attributes, parents):
            if not parents:
                if tag != content_root:
                    raise ValueError('Invalid content type namespace')
                return
            if parents != (content_root,) or tag not in (content_ns + 'Override', content_ns + 'Default'):
                raise ValueError('Invalid content type element')
            content = attributes.get('ContentType')
            if tag == content_ns + 'Override':
                part = attributes['PartName']
                if not part.startswith('/') or part.startswith('//'):
                    raise ValueError('Invalid absolute content type part name')
                if part in part_names:
                    raise ValueError('Duplicate content type part')
                part_names.add(part)
                if content in (XLSX, XLSM, XLTX, XLTM):
                    workbook_paths.append(part[1:])
            else:
                extension = attributes['Extension']
                if extension in extensions:
                    raise ValueError('Duplicate default content type')
                extensions.add(extension)
                if content in (XLSX, XLSM, XLTX, XLTM):
                    workbook_defaults.add(content)
        self._scan_xml(archive, '[Content_Types].xml', content_type)
        if len(workbook_paths) > 1 or (not workbook_paths and len(workbook_defaults) != 1):
            raise ValueError('Missing or ambiguous workbook part')
        workbook_path = workbook_paths[0] if workbook_paths else 'xl/workbook.xml'
        ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
        relationship_id = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
        sheet_ids = []
        sheet_names = set()
        def workbook_sheet(tag, attributes, parents):
            if not parents and tag != ns + 'workbook':
                raise ValueError('Invalid workbook namespace')
            if tag.rsplit('}', 1)[-1] == 'sheet':
                if tag != ns + 'sheet' or parents != (ns + 'workbook', ns + 'sheets'):
                    raise ValueError('Invalid workbook sheet element')
                if attributes.get('name') in ('Aulas', 'Cursos'):
                    if attributes['name'] in sheet_names:
                        raise ValueError('Duplicate imported worksheet name')
                    sheet_names.add(attributes['name'])
                    sheet_ids.append(attributes[relationship_id])
        self._scan_xml(archive, workbook_path, workbook_sheet)
        directory, filename = posixpath.split(workbook_path)
        relationships_path = posixpath.join(directory, '_rels', filename + '.rels')
        targets = {}
        seen_ids = set()
        relation_ns = 'http://schemas.openxmlformats.org/package/2006/relationships}'
        relation_root = relation_ns + 'Relationships'
        def relationship(tag, attributes, parents):
            if not parents:
                if tag != relation_root:
                    raise ValueError('Invalid relationship namespace')
                return
            if tag != relation_ns + 'Relationship' or parents != (relation_root,):
                raise ValueError('Invalid relationship element')
            identifier = attributes['Id']
            if identifier in seen_ids:
                raise ValueError('Duplicate workbook relationship ID')
            seen_ids.add(identifier)
            if identifier in sheet_ids:
                targets[identifier] = attributes
        self._scan_xml(archive, relationships_path, relationship)
        for sheet_id in sheet_ids:
            self._checkpoint()
            relation = targets[sheet_id]
            if relation.get('Type') != 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet':
                raise ValueError('Invalid imported worksheet relationship type')
            if relation.get('TargetMode') == 'External':
                raise ValueError('An imported worksheet must be inside the workbook')
            target = relation['Target']
            path = (target[1:] if target.startswith('/') else
                    posixpath.normpath(posixpath.join(directory, target)))
            row = column = max_row = max_column = 0
            row_columns = set()
            data_parent = (ns + 'worksheet',)
            row_parent = data_parent + (ns + 'sheetData',)
            cell_parent = row_parent + (ns + 'row',)
            def worksheet_element(tag, attributes, parents):
                nonlocal row, column, max_row, max_column
                if not parents and tag != ns + 'worksheet':
                    raise ValueError('Invalid worksheet namespace')
                # openpyxl parses every direct row child as a cell, regardless
                # of its tag, and processes namespaced rows at any depth. Fail
                # closed on malformed structure so both parsers see exactly
                # the cells whose dimensions we check.
                if ((tag == ns + 'sheetData' and parents != data_parent) or
                        (parents == row_parent and tag != ns + 'row') or
                        (tag == ns + 'row' and parents != row_parent) or
                        (parents == cell_parent and tag != ns + 'c') or
                        (tag == ns + 'c' and parents != cell_parent)):
                    raise ValueError('Invalid worksheet row or cell structure')
                if tag == ns + 'row':
                    self._checkpoint()
                    next_row = int(attributes.get('r', row + 1))
                    if next_row <= row:
                        raise ValueError('Worksheet rows must be unique and increasing')
                    row = next_row
                    column = 0
                    row_columns.clear()
                    max_row = max(max_row, row)
                elif tag == ns + 'c':
                    reference = attributes.get('r')
                    if reference:
                        match = re.fullmatch(r'([A-Za-z]{1,3})([1-9][0-9]*)', reference)
                        if not match:
                            raise ValueError('Invalid worksheet cell reference')
                        column = 0
                        for letter in match[1].upper():
                            column = column * 26 + ord(letter) - ord('A') + 1
                        max_row = max(max_row, int(match[2]))
                    else:
                        column += 1
                    if column in row_columns:
                        raise ValueError('Duplicate worksheet cell column')
                    row_columns.add(column)
                    max_column = max(max_column, column)
                else:
                    return
                if (max_row > self.MAX_DATA_ROWS + 1 or
                        max_column > self.MAX_DATA_COLUMNS or
                        max_row * max_column > self.MAX_SHEET_CELLS):
                    raise ExcelImportError("El libro supera el límite de importación. Divídalo en archivos más pequeños.")
            self._scan_xml(archive, path, worksheet_element)

    def _scan_xml(self, archive, path, on_start):
        """Streaming SAX-style scan without a tree, DTDs or entity expansion."""
        parser = expat.ParserCreate(namespace_separator='}')
        stack = []
        def start_element(tag, attributes):
            if len(stack) >= 64:
                raise ValueError('Workbook XML nesting exceeds the supported depth')
            on_start(tag, attributes, tuple(stack))
            stack.append(tag)
        parser.StartElementHandler = start_element
        parser.EndElementHandler = lambda tag: stack.pop()
        def reject_entities(*args):
            raise ValueError('Workbook XML must not contain DTDs or entities')
        parser.StartDoctypeDeclHandler = reject_entities
        parser.EntityDeclHandler = reject_entities
        parser.ExternalEntityRefHandler = reject_entities
        with archive.open(path) as source:
            while True:
                self._checkpoint()
                chunk = source.read(64 * 1024)
                parser.Parse(chunk, not chunk)
                if not chunk:
                    break


    def __init__(self, file_path: str, *, source_bytes=None, cancelled=None):
        self.file_path = file_path
        self._source_bytes = source_bytes
        self._cancelled = cancelled or (lambda: False)
        self._sheets = None

    def _source(self):
        return BytesIO(self._source_bytes) if self._source_bytes is not None else self.file_path

    def _checkpoint(self):
        if self._cancelled():
            raise ImportCancelled()


    def _read_sheet(self, name):
        # Read a single snapshot, preserving raw headers so duplicate names are
        # detected before pandas silently renames them with a .1 suffix.
        if self._sheets is None:
            if Path(self.file_path).suffix.lower() != ".xlsx":
                raise ExcelImportError("Use un archivo .xlsx. En Excel, elija Guardar como → Libro de Excel (.xlsx).")
            try:
                self._check_workbook_size()
                with pd.ExcelFile(self._source(), engine="openpyxl") as workbook:
                    self._checkpoint()
                    missing = [n for n in ("Aulas", "Cursos") if n not in workbook.sheet_names]
                    if missing:
                        raise ExcelImportError(
                            notice("Faltan las hojas: {missing}. Use esos nombres exactos. Hojas encontradas: {found}",
                                   missing=", ".join(missing), found=", ".join(workbook.sheet_names)))
                    raw = {}
                    for n in ("Aulas", "Cursos"):
                        self._checkpoint()
                        raw[n] = pd.read_excel(workbook, sheet_name=n, header=None, dtype=object,
                                               keep_default_na=False, nrows=self.MAX_DATA_ROWS + 2)
                        self._checkpoint()
                    if any(len(data) > self.MAX_DATA_ROWS + 1 for data in raw.values()):
                        raise ExcelImportError("El libro supera el límite de importación. Divídalo en archivos más pequeños.")
            except (ExcelImportError, ImportCancelled):
                raise
            except FileNotFoundError as exc:
                raise ExcelImportError("No se encontró el archivo. Selecciónelo nuevamente.") from exc
            except PermissionError as exc:
                raise ExcelImportError("No se pudo abrir el archivo. Revise sus permisos o guarde una copia .xlsx.") from exc
            except Exception as exc:
                raise ExcelImportError("No se pudo leer el libro. Ábralo en Excel y guarde una copia .xlsx sin contraseña.") from exc
            sheets = {}
            for sheet, data in raw.items():
                self._checkpoint()
                if data.empty:
                    raise ExcelImportError(notice("Hoja {sheet}: agregue los encabezados en la fila 1.", sheet=sheet))
                headers = [str(v).strip() for v in data.iloc[0]]
                normalized = [self._normalize(v) for v in headers]
                duplicates = sorted({v for v in normalized if v and normalized.count(v) > 1})
                if duplicates:
                    raise ExcelImportError(notice("Hoja {sheet}, fila 1: columnas duplicadas: {columns}. Deje una sola columna de cada tipo.", sheet=sheet, columns=", ".join(duplicates)))
                required = ["# de aula"] if sheet == "Aulas" else ["curso"]
                missing = [v for v in required if v not in normalized]
                if missing:
                    raise ExcelImportError(notice("Hoja {sheet}, fila 1: falta la columna {columns}. Revise el encabezado.", sheet=sheet, columns=", ".join(missing)))
                frame = data.iloc[1:].copy()
                frame.columns = [v if v else f"__extra_{i}" for i, v in enumerate(normalized)]
                if sheet == "Cursos":
                    # Validation and every materializer consume the same keys.
                    # Preserve legacy unambiguous aliases, but never validate
                    # one column and silently load another.
                    frame = frame.rename(columns=self._resolve_course_columns(frame.columns))
                sheets[sheet] = frame
            self._sheets = sheets
        return self._sheets[name]

    def load_validated(self) -> ExcelImport:
        """Validate the complete input before the caller replaces live data.

        Blank preference values retain historical defaults. Malformed nonblank
        values are errors; harmless fallbacks are reported before confirmation.
        """
        warnings = []
        errors = []
        seen = set()
        for index, row in self._read_sheet("Aulas").iterrows():
            self._checkpoint()
            name = self._identifier(row.get("# de aula"))
            if not name:
                if any(str(row.get(c, "")).strip() for c in ("descripcion", "campus", "capacidad")):
                    errors.append(notice("Aulas, fila {row}: falta # DE AULA.", row=index + 1))
                continue
            if name in seen:
                errors.append(notice("Aulas, fila {row}: el aula '{room}' está duplicada.", row=index + 1, room=name))
            seen.add(name)
            value = row.get("capacidad", "")
            if self._blank(value):
                warnings.append(notice("Aulas, fila {row}: '{room}' no tiene capacidad; se usará 0.", row=index + 1, room=name))
            else:
                try:
                    number = float(value)
                    if isinstance(value, bool) or not number.is_integer() or number < 0:
                        raise ValueError
                except (ValueError, TypeError, OverflowError):
                    errors.append(notice("Aulas, fila {row}: CAPACIDAD debe ser un entero mayor o igual a 0.", row=index + 1))
        course_count = 0
        for index, row in self._read_sheet("Cursos").iterrows():
            self._checkpoint()
            code = self._identifier(row.get("curso"))
            if not code:
                if any(not self._blank(row.get(c)) for c in ("nombre", "horas", "aula", "dias")):
                    errors.append(notice("Cursos, fila {row}: falta Curso (código).", row=index + 1))
                continue
            course_count += 1
            hours = row.get("horas")
            if not self._blank(hours):
                match = re.fullmatch(r"\s*(\d{2})(\d{2})\s*-\s*(\d{2})(\d{2})\s*", str(hours))
                values = tuple(map(int, match.groups())) if match else None
                if (not values or values[0] > 23 or values[2] > 23 or
                    values[1] > 59 or values[3] > 59 or
                    values[0] * 60 + values[1] >= values[2] * 60 + values[3]):
                    errors.append(notice("Cursos, fila {row}: Horas debe ser HHMM-HHMM, con fin posterior al inicio (ej. 0800-1055).", row=index + 1))
            days = row.get("dias")
            if not self._blank(days) and any(v.strip().upper() not in DAY_ABBR for v in str(days).split(",")):
                errors.append(notice("Cursos, fila {row}: Días admite L, I, M, J, V, S separados por comas; I=martes y M=miércoles.", row=index + 1))
            room = self._identifier(row.get("aula"))
            if room and room != "-" and room not in seen:
                warnings.append(notice("Cursos, fila {row}: el aula '{room}' no aparece en Aulas; se importará sin esa preferencia.", row=index + 1, room=room))
        if not seen:
            errors.append("Aulas: agregue al menos un aula con # DE AULA.")
        if not course_count:
            errors.append("Cursos: agregue al menos una fila con Curso (código).")
        if errors:
            messages = [notice("Corrija el archivo y vuelva a cargarlo:")] + errors[:20]
            if len(errors) > 20:
                messages.append(notice("… y {count} errores más.", count=len(errors) - 20))
            raise ExcelImportError(messages)
        classrooms = self.load_classrooms()
        known = set(classrooms)
        return ExcelImport(classrooms, self.load_courses(known), self.load_course_classroom_map(known), warnings)

    @staticmethod
    def _blank(value):
        return value is None or pd.isna(value) or str(value).strip() in ("", "-")

    @staticmethod
    def _identifier(value):
        if value is None or pd.isna(value):
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_classrooms(self) -> Dict[str, Classroom]:
        """
        Read sheet 'Aulas' and build Classroom objects.
        Columns: # DE AULA, DESCRIPCIÓN, CAMPUS, CAPACIDAD, CAPACIDAD 80%
        Room type: starts with 'L' → LAB, otherwise → REGULAR.
        """
        df = self._read_sheet("Aulas")

        classrooms = {}
        for _, row in df.iterrows():
            self._checkpoint()
            raw_name = row.get("# de aula")
            if pd.isna(raw_name):
                continue

            name = self._identifier(raw_name)
            if not name:
                continue

            capacity_raw = row.get("capacidad")
            capacity = int(float(capacity_raw)) if not self._blank(capacity_raw) else 0

            description_raw = row.get("descripcion")
            description = str(description_raw).strip() if pd.notna(description_raw) else ""

            campus_raw = row.get("campus")
            campus = str(campus_raw).strip() if pd.notna(campus_raw) else ""

            room_type = "LAB" if name.startswith("L") else "REGULAR"

            classrooms[name] = Classroom(
                name=name,
                capacity=capacity,
                room_type=room_type,
                description=description,
                campus=campus,
            )

        return classrooms

    def load_courses(self, known_classrooms: set[str] | None = None) -> list[Course]:
        """
        Read sheet 'Cursos' and build Course objects.

        Columns: Curso, Nombre de Curso, Cantidad de Grupos, Horas, Aula, Días

        Each row represents one suggested group of a course.
        Multiple rows with the same course code → multiple groups.

        Horas format: 'HHMM-HHMM' (e.g. '0800-1055') or '-' / blank → None
        Días format:  single abbreviation or comma-separated (e.g. 'L', 'L,M')

        If known_classrooms is provided, any Aula reference not in that set
        is silently ignored (treated as no classroom preference).
        """
        if known_classrooms is None:
            known_classrooms = set(self.load_classrooms().keys())

        df = self._read_sheet("Cursos")

        # Normalize column names for robust matching
        col_map = self._build_col_map(df.columns)

        course_rows: dict[str, list[dict]] = {}

        for _, row in df.iterrows():
            self._checkpoint()
            code_raw = self._get(row, col_map, "curso")
            if code_raw is None:
                continue
            code = str(code_raw).strip()
            if not code:
                continue

            name_raw = self._get(row, col_map, "nombre")
            name = str(name_raw).strip() if name_raw is not None else None

            horas_raw = self._get(row, col_map, "horas")
            start_min, end_min = self._parse_horas(horas_raw)

            aula_raw = self._get(row, col_map, "aula")
            aula = self._identifier(aula_raw) if aula_raw is not None else None
            if aula and aula.lower() in ("nan", "-", ""):
                aula = None
            # Ignore aula references that don't exist in the classrooms sheet
            if aula and aula not in known_classrooms:
                aula = None

            dias_raw = self._get(row, col_map, "dias")
            days = self._parse_dias(dias_raw)

            course_rows.setdefault(code, []).append({
                "name": name,
                "start_min": start_min,
                "end_min": end_min,
                "aula": aula,
                "days": days,
            })

        classrooms_info = self.load_classrooms()

        courses = []
        for code, rows in course_rows.items():
            self._checkpoint()
            name = next((r["name"] for r in rows if r["name"]), None)
            number_of_groups = len(rows)
            duration_min = self._most_common_duration(rows)
            suggested_classroom = self._most_common_aula(rows)
            preferred_day = self._most_common_day(rows)
            preferred_start_min = self._most_common_start(rows)

            # Infer room type from the suggested classroom's actual type.
            # Fall back to code-suffix heuristic only when no known classroom.
            if suggested_classroom and suggested_classroom in classrooms_info:
                room_type = classrooms_info[suggested_classroom].room_type
            else:
                room_type = self._infer_room_type(code)

            # Per-group suggestions: preserve each row's individual aula/day/hour
            group_suggestions = [
                {
                    "aula": r["aula"],
                    "preferred_day": r["days"][0] if r["days"] else None,
                    "preferred_start_min": r["start_min"],
                }
                for r in rows
            ]

            courses.append(Course(
                code=code,
                name=name,
                number_of_groups=number_of_groups,
                duration_min=duration_min,
                required_room_type=room_type,
                suggested_classroom=suggested_classroom,
                preferred_day=preferred_day,
                preferred_start_min=preferred_start_min,
                group_suggestions=group_suggestions,
            ))

        return courses

    def load_course_classroom_map(self, known_classrooms: set[str] | None = None) -> dict[str, list[str]]:
        """
        Return a mapping: classroom_name -> [course_codes] based on the Aula
        column in the Cursos sheet. Used to set classroom restrictions.
        Only includes classrooms present in known_classrooms (if provided).
        """
        if known_classrooms is None:
            known_classrooms = set(self.load_classrooms().keys())

        df = self._read_sheet("Cursos")
        col_map = self._build_col_map(df.columns)

        classroom_courses: dict[str, list[str]] = {}
        for _, row in df.iterrows():
            self._checkpoint()
            code_raw = self._get(row, col_map, "curso")
            aula_raw = self._get(row, col_map, "aula")

            if code_raw is None or aula_raw is None:
                continue

            code = str(code_raw).strip()
            aula = self._identifier(aula_raw)

            if not code or not aula or aula.lower() in ("nan", "-", ""):
                continue
            if aula not in known_classrooms:
                continue

            classroom_courses.setdefault(aula, [])
            if code not in classroom_courses[aula]:
                classroom_courses[aula].append(code)

        return classroom_courses

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_horas(self, value) -> tuple[int | None, int | None]:
        """
        Parse 'HHMM-HHMM' into (start_min, end_min).
        Returns (None, None) for blank or '-' values.
        """
        if value is None or pd.isna(value):
            return None, None
        s = str(value).strip()
        if s in ("", "-"):
            return None, None
        if "-" in s:
            parts = s.split("-")
            if len(parts) == 2:
                try:
                    start = TimeModel.hhmm_to_minutes(parts[0].strip())
                    end   = TimeModel.hhmm_to_minutes(parts[1].strip())
                    return start, end
                except (ValueError, IndexError):
                    pass
        return None, None

    def _parse_dias(self, value) -> list[str]:
        """
        Parse day abbreviation(s) into full Spanish day names.
        Accepts single value ('L') or comma-separated ('L,M').
        Returns empty list if blank/null.
        """
        if value is None or pd.isna(value):
            return []
        s = str(value).strip()
        if not s or s == "-":
            return []
        result = []
        for abbr in s.split(","):
            abbr = abbr.strip().upper()
            if abbr in DAY_ABBR:
                result.append(DAY_ABBR[abbr])
        return result

    def _infer_room_type(self, code: str) -> str:
        upper = code.strip().upper()
        if upper.endswith("L") or upper.endswith("P"):
            return "LAB"
        return "REGULAR"

    # ------------------------------------------------------------------
    # Column mapping
    # ------------------------------------------------------------------

    def _resolve_course_columns(self, columns):
        """Resolve legacy aliases once; exact headers keep their precedence.

        More than one fallback, or one header claiming multiple fields, is
        ambiguous and must be corrected before importing any rows.
        """
        resolved = {}
        for key in ("curso", "nombre", "horas", "aula", "dias"):
            matches = [key] if key in columns else [col for col in columns if key in col]
            if len(matches) > 1 or (matches and matches[0] in resolved):
                raise ExcelImportError(notice(
                    "Hoja {sheet}, fila 1: columnas duplicadas: {columns}. Deje una sola columna de cada tipo.",
                    sheet="Cursos", columns=", ".join(matches)))
            if matches:
                resolved[matches[0]] = key
        return resolved

    def _build_col_map(self, columns) -> dict[str, str]:
        """
        Build a normalized name → original name mapping for DataFrame columns.
        """
        mapping = {}
        for col in columns:
            normalized = self._normalize(str(col))
            mapping[normalized] = col
        return mapping

    def _normalize(self, text: str) -> str:
        text = text.strip().lower()
        text = unicodedata.normalize("NFKD", text)
        return "".join(ch for ch in text if not unicodedata.combining(ch))

    def _get(self, row, col_map: dict, key: str):
        """
        Read a canonical column resolved before validation.
        Returns None if column not found or value is NaN.
        """
        key = self._normalize(key)
        if key in col_map:
            # "Curso" must win over "Nombre de Curso", regardless of order.
            # A blank exact match must remain blank, not fall back to a name.
            val = row[col_map[key]]
            return None if pd.isna(val) else val
        return None

    # ------------------------------------------------------------------
    # Aggregation helpers (most common value across group rows)
    # ------------------------------------------------------------------

    def _most_common_duration(self, rows: list[dict]) -> int:
        durations = []
        for r in rows:
            if r["start_min"] is not None and r["end_min"] is not None:
                durations.append(r["end_min"] - r["start_min"])
        if not durations:
            return 60  # default 1 hour
        return max(set(durations), key=durations.count)

    def _most_common_aula(self, rows: list[dict]) -> str | None:
        aulas = [r["aula"] for r in rows if r["aula"]]
        if not aulas:
            return None
        return max(set(aulas), key=aulas.count)

    def _most_common_day(self, rows: list[dict]) -> str | None:
        days = [d for r in rows for d in r["days"]]
        if not days:
            return None
        return max(set(days), key=days.count)

    def _most_common_start(self, rows: list[dict]) -> int | None:
        starts = [r["start_min"] for r in rows if r["start_min"] is not None]
        if not starts:
            return None
        return max(set(starts), key=starts.count)
