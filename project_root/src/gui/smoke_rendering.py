"""Fail-closed text evidence for opt-in smoke runs; never changes app fonts."""
import hashlib
import json
import os
import string
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QEvent, QSize, Qt, qVersion
from PyQt6.QtGui import QFontDatabase, QFontInfo, QFontMetrics, QImage, QPainter
from PyQt6.QtWidgets import QApplication, QPushButton, QStyle, QStyleOptionButton, QWidget

# These are the shipped UI languages, not a claim about arbitrary course names.
REQUIRED_CHARACTERS = string.ascii_letters + string.digits + string.punctuation + 'ÁÉÍÓÚÜÑáéíóúüñ¿¡'
SAMPLE_TEXT = 'SORTH · Generar horario / Generate schedule · áéíóúüñ · 0123456789'


def _layout_signature(window):
    return tuple((widget.metaObject().className(), widget.objectName(),
                  widget.isVisible(), widget.geometry().getRect())
                 for widget in (window, *window.findChildren(QWidget)))


def settle_capture_layout(window):
    """Deliver pending layout work before an opt-in smoke screenshot.

    Caption changes invalidate native layouts asynchronously. QWidget.grab()
    paints the new text but does not guarantee those layout requests ran first.
    Drain only LayoutRequest events, never user input, timers or worker signals.
    A bounded fixed-point check rejects unstable evidence instead of sleeping or
    changing fonts, captions, window dimensions or production layout policy.
    """
    window.ensurePolished()
    previous = _layout_signature(window)
    stable = 0
    for delivery in range(1, 17):
        QCoreApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)
        current = _layout_signature(window)
        stable = stable + 1 if current == previous else 0
        if stable >= 2:
            return delivery
        previous = current
    raise RuntimeError('Qt capture layout did not settle; smoke images cannot be accepted.')


def _action_geometry(window):
    """Measure live button text against native content bounds, not stale hints."""
    entries = []
    for button in window.findChildren(QPushButton):
        if not button.isVisible() or not button.text():
            continue
        option = QStyleOptionButton()
        button.initStyleOption(option)
        contents = button.style().subElementRect(
            QStyle.SubElement.SE_PushButtonContents, option, button)
        text = button.fontMetrics().size(Qt.TextFlag.TextShowMnemonic, button.text())
        # SE_PushButtonContents still includes the icon/menu allocation. Match
        # QPushButton's native sizing inputs afresh, rather than trusting its
        # cached sizeHint or treating that whole rectangle as text-only.
        # Qt 6.11: src/widgets/widgets/qpushbutton.cpp, QPushButton::sizeHint.
        content = QSize(text)
        if not option.icon.isNull():
            content.setWidth(content.width() + option.iconSize.width() + 4)
            content.setHeight(max(content.height(), option.iconSize.height()))
        option.rect.setSize(content)
        if option.features & QStyleOptionButton.ButtonFeature.HasMenu:
            content.setWidth(content.width() + button.style().pixelMetric(
                QStyle.PixelMetric.PM_MenuButtonIndicator, option, button))
        required = button.style().sizeFromContents(
            QStyle.ContentsType.CT_PushButton, option, content, button)
        entries.append({'text': button.text(), 'geometry': list(button.geometry().getRect()),
                        'content_size': [contents.width(), contents.height()],
                        'text_size': [text.width(), text.height()],
                        'required_native_size': [required.width(), required.height()],
                        'font': button.font().toString(), 'logical_dpi': button.logicalDpiX(),
                        'fits': (contents.width() >= text.width() and contents.height() >= text.height()
                                 and button.width() >= required.width() and button.height() >= required.height())})
    return entries


def _raster(font, text):
    metrics = QFontMetrics(font)
    image = QImage(max(32, metrics.horizontalAdvance(text) + 16),
                   max(32, metrics.height() + 16), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.white)
    painter = QPainter(image)
    try:
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(8, 8 + metrics.ascent(), text)
    finally:
        painter.end()
    # Cropping to painted pixels makes identical missing-glyph boxes compare
    # equal even when fallback advances differ. A blank image is never evidence.
    points = [(x, y) for y in range(image.height()) for x in range(image.width())
              if image.pixelColor(x, y) != Qt.GlobalColor.white]
    if not points:
        return image, None, 0
    xs, ys = zip(*points)
    cropped = image.copy(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
    digest = hashlib.sha256(bytes(cropped.constBits().asstring(cropped.sizeInBytes()))).hexdigest()
    return image, digest, len(points)


def require_readable_text(window, output_dir, name):
    """Verify live widget fonts and actual raster output before accepting PNGs.

    This rejects an empty Qt font database, missing English/Spanish glyphs,
    blank text and repeated tofu rasters. It is a narrow smoke guard, not OCR,
    full visual acceptance, arbitrary-Unicode coverage or native-desktop proof.
    Diagnostic files are synthetic text and metadata only, never font binaries.
    """
    app = QApplication.instance()
    output_dir = Path(output_dir)
    report = {'ok': False, 'platform': app.platformName(), 'qt_version': qVersion(),
              'font_directory': os.environ.get('QT_QPA_FONTDIR'),
              'family_count': len(QFontDatabase.families()),
              'scope': 'English/Spanish UI glyph support, raster sanity and visible action caption geometry',
              'fonts': [], 'actions': []}
    try:
        if not report['family_count']:
            raise RuntimeError('Qt font database is empty; smoke images cannot be accepted.')
        report['layout_deliveries'] = settle_capture_layout(window)
        report['actions'] = _action_geometry(window)
        if any(not action['fits'] for action in report['actions']):
            raise RuntimeError('Visible action caption does not fit its native content bounds.')
        fonts = {app.font().toString(): app.font()}
        for widget in [window, *window.findChildren(QWidget)]:
            if widget.isVisible():
                fonts.setdefault(widget.font().toString(), widget.font())
        samples = []
        for description, font in fonts.items():
            metrics = QFontMetrics(font)
            missing = [character for character in REQUIRED_CHARACTERS
                       if not metrics.inFontUcs4(ord(character))]
            # i, W and the accented ñ must yield visible, distinct ink shapes.
            rasters = [_raster(font, character) for character in ('i', 'W', 'ñ')]
            distinct = len({digest for _, digest, _ in rasters if digest})
            entry = {'requested': description, 'resolved_family': QFontInfo(font).family(),
                     'missing_characters': missing, 'distinct_probe_rasters': distinct,
                     'probe_ink_pixels': [ink for _, _, ink in rasters]}
            report['fonts'].append(entry)
            if missing or distinct != 3 or not all(ink for _, _, ink in rasters):
                raise RuntimeError('Qt font lacks readable English/Spanish glyphs or distinct text rasters.')
            sample, _, ink = _raster(font, SAMPLE_TEXT)
            if not ink:
                raise RuntimeError('Qt text raster is blank.')
            samples.append(sample)
        canvas = QImage(max(sample.width() for sample in samples),
                        sum(sample.height() for sample in samples), QImage.Format.Format_ARGB32)
        canvas.fill(Qt.GlobalColor.white)
        painter = QPainter(canvas)
        try:
            y = 0
            for sample in samples:
                painter.drawImage(0, y, sample)
                y += sample.height()
        finally:
            painter.end()
        image_name = f'text-rendering-{name}.png'
        if not canvas.save(str(output_dir / image_name)):
            raise RuntimeError('Could not save the text-raster evidence.')
        report.update(ok=True, raster_image=image_name)
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        (output_dir / f'text-rendering-{name}.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
