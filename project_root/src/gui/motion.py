"""Small, interruptible Qt transitions; never gate application state on motion."""

from PyQt6 import sip
from PyQt6.QtCore import QObject, QEvent, QEasingCurve, QPropertyAnimation, QSettings
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from .i18n import msg

TRANSITION_MS = 150
SETTINGS_KEY = 'interface/reduced_motion'


class MotionController(QObject):
    """One temporary effect, regardless of table size or number of tab changes.

    New content is already interactive when revealed. Repeated navigation cancels
    the old effect; hidden/deleted widgets and reduced motion finish immediately.
    The effect is removed on completion, so ordinary table painting stays native.
    """

    def __init__(self, parent, settings=None):
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings('SORTH', 'SORTH')
        value = self.settings.value(SETTINGS_KEY, False)
        self.reduced = str(value).lower() in ('true', '1')
        self._target = None
        self._effect = None
        self.animation = QPropertyAnimation(self)
        self.animation.setPropertyName(b'opacity')
        self.animation.setDuration(TRANSITION_MS)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self.finish)

    def set_reduced(self, reduced):
        self.reduced = bool(reduced)
        self.settings.setValue(SETTINGS_KEY, self.reduced)
        self.settings.sync()
        if self.reduced:
            self.finish()

    def reveal(self, widget):
        self.finish()
        if self.reduced or widget is None or sip.isdeleted(widget) or not widget.isVisible():
            return
        # Never replace an effect owned by a caller.
        if widget.graphicsEffect() is not None:
            return
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.9)
        self._target, self._effect = widget, effect
        widget.setGraphicsEffect(effect)
        widget.installEventFilter(self)
        effect.destroyed.connect(self._effect_destroyed)
        self.animation.setTargetObject(effect)
        self.animation.setStartValue(0.9)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def _effect_destroyed(self):
        # The target may have been deleted while an animation was active.
        if self._effect is not None:
            self.finish()

    def finish(self):
        self.animation.stop()
        self.animation.setTargetObject(None)
        widget, effect = self._target, self._effect
        self._target = self._effect = None
        if widget is not None and not sip.isdeleted(widget):
            widget.removeEventFilter(self)
            if effect is not None and not sip.isdeleted(effect) and widget.graphicsEffect() is effect:
                widget.setGraphicsEffect(None)

    def eventFilter(self, watched, event):
        if watched is self._target and event.type() in (QEvent.Type.Hide, QEvent.Type.Resize):
            self.finish()
        return False


def update_busy_indicator(progress, busy, reduced):
    """No fake percentage: reduced motion uses a static, text-labelled track."""
    if reduced:
        progress.setRange(0, 1)
        progress.setValue(0)
        progress.setFormat(msg('En curso'))
        progress.setTextVisible(True)
    else:
        progress.setRange(0, 0)
        progress.setTextVisible(False)
    progress.setVisible(bool(busy))
