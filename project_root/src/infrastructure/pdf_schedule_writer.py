"""Selectable, print-ready classroom timetables. No Qt or office dependency.

The PDF is composed in memory and replaced atomically only after a successful
build. It never changes the schedule or infers completeness from a filtered set.
"""
from io import BytesIO
import os
from pathlib import Path
import re
import tempfile
from string import Formatter
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer

from ..scheduling.schedule_grid import build_schedule_grid, course_color
from ..scheduling.time_model import TimeModel


_FONT = 'SORTH-DejaVu'
_VERSION = '2.0.0'


def _font():
    if _FONT not in pdfmetrics.getRegisteredFontNames():
        path = Path(__file__).resolve().parents[2] / 'assets' / 'fonts' / 'DejaVuSans.ttf'
        pdfmetrics.registerFont(TTFont(_FONT, str(path)))
    return pdfmetrics.getFont(_FONT)


def write_schedule_pdf(exporter, assignments, output_path, name_map, *,
                       groups=None, filtered=False, total_assigned=None,
                       pending_count=None, filters=None, labels=None):
    """Export one row per session, ordered by classroom/day/exact start.

    Global counts are mandatory for filtered output. Unknown pending counts are
    labelled unknown, never zero. Unsupported glyphs fail before touching the
    destination rather than silently replacing a course name with black boxes.
    """
    def tr(source, **parameters):
        # Pure catalog contract: missing/malformed entries fall back to Spanish.
        # Application data is interpolated only after selecting a template.
        template = (labels or {}).get(source, source)
        def fields(value):
            return {key for _, key, _, _ in Formatter().parse(value) if key}
        try:
            if not isinstance(template, str) or fields(template) != fields(source):
                template = source
            return template.format(**parameters)
        except (ValueError, KeyError, IndexError):
            return source.format(**parameters)

    if total_assigned is None:
        if filtered:
            raise ValueError(tr('El PDF filtrado requiere el total global de asignaciones.'))
        total_assigned = len(assignments)
    if total_assigned < len(assignments) or (not filtered and total_assigned != len(assignments)):
        raise ValueError(tr('El alcance y el total de asignaciones no coinciden.'))
    if pending_count is None and groups is not None:
        pending_count = len({g.group_id for g in groups}) - total_assigned
    if pending_count is not None and pending_count < 0:
        raise ValueError(tr('El número de sesiones pendientes no puede ser negativo.'))
    font = _font()
    style = ParagraphStyle('body', fontName=_FONT, fontSize=9, leading=12,
                           textColor=colors.HexColor('#182536'), splitLongWords=True)
    title_style = ParagraphStyle('room', parent=style, fontSize=12, leading=16)

    def p(value, text_style=style):
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', str(value))
        missing = sorted({ord(c) for c in value if not c.isspace()
                          and ord(c) not in font.face.charToGlyph})
        # Complex-script shaping is not part of ReportLab's default layout.
        # Fail explicitly instead of producing a misleading visual label.
        if missing or re.search(r'[\u0590-\u08ff\u0900-\u0dff]', value):
            raise ValueError(tr('El PDF no admite algunos caracteres o escrituras de los datos. Use Excel/CSV para conservarlos.'))
        return Paragraph(escape(value).replace('\n', '<br/>'), text_style)

    scope = tr('Vista filtrada') if filtered else tr('Todas las asignaciones')
    state = (tr('Estado global: pendientes no informados') if pending_count is None else
             tr('Horario PARCIAL: {pending} pendientes', pending=pending_count) if pending_count else
             tr('Horario completo: 0 pendientes'))
    summary = tr('{scope} | {count} exportadas de {total} asignadas | {state}',
                 scope=scope, count=len(assignments), total=total_assigned, state=state)
    # This fixed header is repeated on every page; data-dependent long text is
    # placed in flowable tables, where it can wrap and paginate.
    header = p(summary)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=30,
                            rightMargin=30, topMargin=76, bottomMargin=32,
                            title=tr('SORTH - Horario por aula'), author='SORTH')

    def page(canvas, document):
        canvas.saveState()
        canvas.setFont(_FONT, 13)
        canvas.setFillColor(colors.HexColor('#183153'))
        canvas.drawString(30, document.pagesize[1] - 28, tr('SORTH {version} | Horario por aula', version=_VERSION))
        _, height = header.wrap(document.width, 60)
        header.drawOn(canvas, 30, document.pagesize[1] - 40 - height)
        canvas.setFont(_FONT, 8)
        canvas.drawString(30, 17, tr('Horas exactas HH:mm | Texto seleccionable | SORTH'))
        canvas.drawRightString(document.pagesize[0] - 30, 17, tr('Página {page}', page=document.page))
        canvas.restoreState()

    def chunks(paragraph, width, height=180):
        """Bound row height without reducing type or losing continuation labels."""
        parts = []
        while paragraph.wrap(width, 100000)[1] > height:
            split = paragraph.split(width, height)
            if len(split) < 2:
                raise ValueError(tr('Un texto es demasiado largo para la página PDF.'))
            parts.append(split[0])
            paragraph = split[1]
        parts.append(paragraph)
        return parts

    # Filters are explicit even when all controls are at their defaults. A full
    # export explicitly says that the viewer's filters did not apply.
    filter_text = (tr('No aplicados (se exportan todas las asignaciones).') if not filtered else
                   '\n'.join(f'{key}: {value}' for key, value in (filters or {}).items()) or
                   tr('Filtros no informados por el solicitante.'))
    story = [p(tr('Alcance y leyenda'), title_style), Spacer(1, 6)]
    story.extend(chunks(p(tr('Filtros: {filters}', filters=filter_text)), doc.width))
    story += [Spacer(1, 8), p(tr('Un color por curso; los nombres completos aparecen en cada fila. CONFLICTO identifica sesiones simultáneas. EXCEPCIÓN LAB identifica una autorización de aula registrada. Continuación repite día, horas y grupo cuando un nombre ocupa varias páginas. Los pendientes corresponden al horario global, no sólo a esta vista.')), Spacer(1, 14)]
    overrides = {g.group_id for g in groups or [] if g.lab_override}
    by_room = {}
    for gid, (room, day, start, end) in assignments.items():
        if day not in exporter.time_model.index_to_day:
            raise ValueError(tr('Día no válido para {group}.', group=gid))
        by_room.setdefault(room, []).append((gid, day, start, end))
    if not by_room:
        story.append(p(tr('Sin sesiones asignadas en este alcance.')))
    widths = [85, 106, 132, doc.width - 403, 80]
    for room_index, room in enumerate(sorted(by_room, key=lambda r: (exporter._natural_key(r), str(r)))):
        if room_index:
            story.append(PageBreak())
        entries = by_room[room]
        grid = build_schedule_grid(entries, min(e[2] for e in entries), max(e[3] for e in entries))
        conflicts = {e[0] for block in grid.blocks if len(block.entries) > 1 for e in block.entries}
        room_paragraph = p(tr('Aula: {room} | Sesiones: {count}', room=room, count=len(entries)), title_style)
        if room_paragraph.wrap(doc.width - 16, 10000)[1] > 96:
            raise ValueError(tr('El nombre del aula es demasiado largo para el encabezado PDF.'))
        rows = [[room_paragraph, '', '', '', ''],
                [p(tr(x)) for x in ('Día', 'Inicio - Fin', 'Grupo / sesión', 'Nombre completo del curso', 'Avisos')]]
        fills = []
        for gid, day, start, end in sorted(entries, key=lambda e: (e[1], e[2], e[3], exporter._natural_key(e[0]))):
            flags = [tr('CONFLICTO')] if gid in conflicts else []
            if gid in overrides:
                flags.append(tr('EXCEPCIÓN LAB'))
            label = name_map.get(gid) or tr('(Sin nombre de curso)')
            values = [tr(exporter.time_model.to_day_name(day)),
                      f'{TimeModel.minutes_to_hhmm(start)} - {TimeModel.minutes_to_hhmm(end)}',
                      gid, label, '\n'.join(flags) or '-']
            cells = [chunks(p(value), width - 12) for value, width in zip(values, widths)]
            for part in range(max(map(len, cells))):
                row = [items[min(part, len(items) - 1)] for items in cells]
                if part and len(cells[3]) > part:
                    row[4] = p(('\n'.join(flags) + '\n' if flags else '') + tr('Continuación'))
                rows.append(row)
                fills.append(('BACKGROUND', (0, len(rows)-1), (-1, len(rows)-1),
                              colors.HexColor('#FCE8EC' if flags else '#' + course_color(exporter._group_parts(gid)[0]))))
        table = Table(rows, colWidths=widths, repeatRows=2, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#EDF2F7')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LINEBELOW', (0, 1), (-1, 1), 0.7, colors.HexColor('#7688A1')),
            ('LINEBELOW', (0, 2), (-1, -1), 0.25, colors.HexColor('#7688A1')),
        ] + fills))
        story.append(table)
    doc.build(story, onFirstPage=page, onLaterPages=page)
    destination = Path(output_path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.sorth-pdf-', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(buffer.getvalue())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
