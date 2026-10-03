"""Test boundaries dispose cyclic widgets before the next native style sweep."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = r'''
import gc
import sys
import weakref
from PyQt6 import sip
from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtWidgets import QApplication, QWidget
from src.gui.schedule_viewer_widget import ScheduleViewerWidget
from tests.qt_lifecycle import dispose_test_widgets

app = QApplication([])
persistent = QWidget()
persistent.show()
app_timer = QTimer(app)
app_timer.setInterval(100000)
app_timer.start()
baseline = set(app.topLevelWidgets())
viewer = ScheduleViewerWidget()
viewer.cycle = viewer
viewer.show()
app.processEvents()
viewer.close()
retired = weakref.ref(viewer)
del viewer

class CollectOnStyle(QObject):
    armed = True
    def eventFilter(self, obj, event):
        if self.armed and event.type() == QEvent.Type.StyleChange:
            self.armed = False
            print('entered style collection', flush=True)
            gc.collect()
            print('collected during style', flush=True)
        return False

if sys.argv[1] == 'dispose':
    # Keep a wrapper to prove native destruction does not rely on Python GC.
    wrapper = retired()
    dispose_test_widgets(app, baseline)
    assert sip.isdeleted(wrapper)
    assert not sip.isdeleted(persistent)
    assert not sip.isdeleted(app_timer) and app_timer.isActive()
    del wrapper
else:
    assert retired() is not None and not sip.isdeleted(retired())
    print('unsafe retired tree alive', flush=True)

collector = CollectOnStyle()
app.installEventFilter(collector)
app.setStyle('Windows')
assert not collector.armed
assert retired() is None or sip.isdeleted(retired())
assert not sip.isdeleted(persistent)
assert app_timer.isActive()
print('style replacement finished', flush=True)
'''


@pytest.mark.parametrize('mode', ['dispose', 'unsafe-control'])
def test_cyclic_test_widget_native_style_lifetime(tmp_path, mode):
    result = subprocess.run(
        [sys.executable, '-X', 'faulthandler', '-c', SCRIPT, mode],
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'XDG_CONFIG_HOME': str(tmp_path)},
        capture_output=True, text=True, timeout=20)
    evidence = result.stdout + result.stderr
    assert 'entered style collection' in evidence, evidence
    if mode == 'dispose':
        assert 'collected during style' in evidence, evidence
        assert result.returncode == 0, evidence
        assert 'style replacement finished' in evidence
    else:
        # The unsafe control may crash or happen to survive depending on Qt's
        # widget iteration order/platform allocator. It must establish that the
        # retired native tree reached the next style sweep. Only this explicitly
        # unsafe subprocess may fail; the corrected path must always complete.
        assert 'unsafe retired tree alive' in evidence, evidence
