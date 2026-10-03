"""Deterministically release per-test Qt widgets outside native event stacks."""
from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QEvent


def dispose_test_widgets(app, previous_widgets):
    """Delete newly created top levels, preserving earlier fixture owners.

    close()/reject() only hide most Qt widgets. Python signal cycles can keep
    their native trees alive until GC runs inside a later QApplication.setStyle
    traversal. Delete them at the test boundary, while no native style callback
    is active. Keep wrappers alive throughout disposal and do not pump unrelated
    events or flush deferred deletion belonging to pre-existing fixtures.
    """
    widgets = [widget for widget in app.topLevelWidgets()
               if widget not in previous_widgets]
    for widget in widgets:
        if not sip.isdeleted(widget):
            widget.deleteLater()
    for widget in widgets:
        if not sip.isdeleted(widget):
            QCoreApplication.sendPostedEvents(widget, QEvent.Type.DeferredDelete)
