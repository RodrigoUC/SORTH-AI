"""Native table painting for readable, individually bounded course blocks.

The model retains full plain text, tooltips, accessibility text and session IDs.
Only painting changes: no child widgets, schedule geometry or input handling.
"""

from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen, QTextLayout, QTextOption
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate

from .theme import COLORS
from ..scheduling.course_style import CourseStyle, GRID_TEXT_COLOR


COURSE_CARD_ROLE = int(Qt.ItemDataRole.UserRole) + 1
GRID_BLOCK_ROLE = int(Qt.ItemDataRole.UserRole) + 2


@dataclass(frozen=True)
class CourseCard:
    style: CourseStyle
    sections: tuple[tuple[str, str, str], ...]
    conflict_label: str = ""


class ScheduleGridDelegate(QStyledItemDelegate):
    """Keep native keyboard/selection behavior while preserving category colors."""

    GUTTER = 3
    INSET = 13

    def paint(self, painter, option, index):
        card = index.data(COURSE_CARD_ROLE)
        if not isinstance(card, CourseCard):
            super().paint(painter, option, index)
            return

        painter.save()
        painter.setClipRect(option.rect)
        painter.fillRect(option.rect, QColor(COLORS["surface"]))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(option.rect).adjusted(self.GUTTER, self.GUTTER,
                                          -self.GUTTER, -self.GUTTER)
        accent = QColor(COLORS["danger"] if card.conflict_label else "#" + card.style.accent)
        fill = QColor(COLORS["danger_soft"] if card.conflict_label else "#" + card.style.fill)
        foreground = QColor(COLORS["danger"] if card.conflict_label else "#" + GRID_TEXT_COLOR)
        painter.setBrush(fill)
        painter.setPen(QPen(accent, 1))
        painter.drawRoundedRect(rect, 4, 4)
        self._draw_marker(painter, rect, accent, 0 if card.conflict_label else card.style.marker)

        # A selection ring never replaces the course fill or its marker. White
        # separation keeps the violet ring legible even on a violet category.
        if option.state & (QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus):
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(COLORS["surface"]), 4))
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QPen(QColor(COLORS["focus"]), 2))
            painter.drawRoundedRect(rect, 4, 4)

        text_rect = rect.adjusted(self.INSET, 7, -8, -7)
        painter.setClipRect(text_rect)
        y = text_rect.top()
        normal = QFont(option.font)
        bold = QFont(normal)
        bold.setBold(True)
        if card.conflict_label:
            y = self._draw_text(painter, text_rect, y, card.conflict_label, bold,
                                accent, max_lines=1) + 3
        for position, (title, times, name) in enumerate(card.sections):
            if position:
                y += 7
            y = self._draw_text(painter, text_rect, y, title, bold, foreground, max_lines=1)
            y = self._draw_text(painter, text_rect, y, times, normal, foreground, max_lines=1)
            if name:
                y = self._draw_text(painter, text_rect, y + 3, name, normal, foreground,
                                    max_lines=2 if len(card.sections) == 1 else 1)
        painter.restore()

    @staticmethod
    def _draw_marker(painter, rect, accent, marker):
        """Solid, dashed, dotted or double edge; labels remain the identity."""
        x, top, bottom = rect.left() + 4.5, rect.top() + 7, rect.bottom() - 7
        pen = QPen(accent, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        if marker == 1:
            pen.setDashPattern([3, 1.5])
        elif marker == 2:
            pen.setDashPattern([1, 1.5])
        elif marker == 3:
            pen.setWidthF(1.2)
        painter.setPen(pen)
        painter.drawLine(QPointF(x, top), QPointF(x, bottom))
        if marker == 3:
            painter.drawLine(QPointF(x + 3, top), QPointF(x + 3, bottom))

    @staticmethod
    def _draw_text(painter, rect, y, text, font, color, max_lines):
        """Fit plain Unicode text, eliding only paint, never model/accessibility."""
        metrics = QFontMetricsF(font)
        line_height = metrics.height()
        available = min(max_lines, int((rect.bottom() - y + 1) / line_height))
        if available < 1:
            return y
        text = " ".join(text.split())
        layout = QTextLayout(text, font)
        wrap = QTextOption()
        wrap.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(wrap)
        layout.beginLayout()
        lines = []
        for _ in range(available):
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(max(1, rect.width()))
            lines.append(line)
        layout.endLayout()
        painter.setFont(font)
        painter.setPen(color)
        utf16 = text.encode("utf-16-le")
        for number, line in enumerate(lines):
            start = line.textStart() * 2
            end = start + line.textLength() * 2
            # Qt offsets are UTF-16, whereas Python slices are code points.
            content = utf16[start:end].decode("utf-16-le").strip()
            if number == len(lines) - 1 and end < len(utf16):
                remaining = utf16[start:].decode("utf-16-le")
                content = metrics.elidedText(remaining, Qt.TextElideMode.ElideRight,
                                             int(rect.width()))
            painter.drawText(QPointF(rect.left(), y + metrics.ascent()), content)
            y += line_height
        return y
