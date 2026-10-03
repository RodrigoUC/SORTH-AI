"""Keep one QApplication/event dispatcher alive for the entire GUI test run.

Qt's process/thread-wide animation driver must not outlive and then be reused
with a destroyed QApplication. Module-scoped app fixtures reuse this owner.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope='session', autouse=True)
def _qt_application_lifetime():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _qt_test_widget_lifetime(_qt_application_lifetime):
    from tests.qt_lifecycle import dispose_test_widgets

    app = _qt_application_lifetime
    # Module/session fixtures have already been constructed. Retain their
    # wrappers too, so incidental GC cannot destroy an existing fixture owner.
    previous_widgets = set(app.topLevelWidgets())
    yield
    dispose_test_widgets(app, previous_widgets)
