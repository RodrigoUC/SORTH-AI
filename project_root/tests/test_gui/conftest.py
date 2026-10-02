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
