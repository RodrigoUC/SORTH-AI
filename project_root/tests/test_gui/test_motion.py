"""Native event-loop checks for bounded, optional presentation-only motion."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6 import sip
from PyQt6.QtCore import QAbstractAnimation, QElapsedTimer, QEvent, QSettings, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QWidget

from src.gui.main_window import MainWindow
from src.gui.motion import MotionController, SETTINGS_KEY, TRANSITION_MS
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / 'motion.ini'), QSettings.Format.IniFormat)


@pytest.fixture
def window(app, tmp_path, monkeypatch, settings):
    # Never write a test preference to the user's real application settings.
    monkeypatch.setattr('src.gui.motion.QSettings', lambda *args: settings)
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    window.show()
    app.processEvents()
    yield window
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_transition_completes_and_removes_effect(window):
    window.tabs.setCurrentIndex(1)
    effect = window.schedule_viewer.graphicsEffect()
    assert effect is not None
    assert effect.opacity() == pytest.approx(0.9)
    window._motion.animation.setCurrentTime(TRANSITION_MS // 2)
    assert 0.9 < effect.opacity() < 1.0
    # Wait for completion while processing events; loaded CI timers may arrive late.
    deadline = QElapsedTimer()
    deadline.start()
    while window._motion.animation.state() != QAbstractAnimation.State.Stopped and deadline.elapsed() < 1500:
        QTest.qWait(10)
    assert window.schedule_viewer.graphicsEffect() is None, {
        'state': window._motion.animation.state(),
        'time': window._motion.animation.currentTime(),
        'target': window._motion._target,
        'effect': window._motion._effect,
        'actual': window.schedule_viewer.graphicsEffect(),
        'animation_target': window._motion.animation.targetObject(),
    }
    assert window._motion.animation.state() == QAbstractAnimation.State.Stopped


def test_rapid_navigation_has_at_most_one_effect(window):
    pages = [window.course_manager, window.schedule_viewer]
    pages += [window.schedule_viewer.tabs.widget(i) for i in range(3)]
    for i in range(50):
        window.tabs.setCurrentIndex(i % 2)
        window.schedule_viewer.tabs.setCurrentIndex(i % 3)
        assert sum(page.graphicsEffect() is not None for page in pages) <= 1
    window._motion.finish()
    assert all(page.graphicsEffect() is None for page in pages)


def test_animation_does_not_delay_keyboard_or_change_filter(window):
    window.tabs.setCurrentIndex(1)
    field = window.schedule_viewer._list_search
    field.setFocus()
    # Hold the transition mid-flight so slow CI also exercises active motion.
    window._motion.animation.pause()
    QTest.keyClicks(field, 'BIO')
    assert field.text() == 'BIO'
    assert field.hasFocus()
    assert window._motion.animation.state() == QAbstractAnimation.State.Paused


def test_toggle_mid_transition_persists_and_cancels(window, settings):
    window.tabs.setCurrentIndex(1)
    window.chk_reduce_motion.setChecked(True)
    assert window.schedule_viewer.graphicsEffect() is None
    assert settings.value(SETTINGS_KEY, type=bool)
    controller = MotionController(window, settings=settings)
    assert controller.reduced
    window.tabs.setCurrentIndex(0)
    assert window.course_manager.graphicsEffect() is None
    window.chk_reduce_motion.setChecked(False)
    window.tabs.setCurrentIndex(1)
    assert window.schedule_viewer.graphicsEffect() is not None


def test_repeated_busy_toggles_keep_truthful_static_feedback(window):
    window._classrooms = {'A1': Classroom('A1', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR')])
    window._set_busy(True)
    assert window._progress.isVisible()
    for i in range(20):
        reduced = i % 2 == 0
        window.chk_reduce_motion.setChecked(reduced)
        assert window._busy
        assert not window.btn_generate.isEnabled()
        assert window._progress.maximum() == (1 if reduced else 0)
        if reduced:
            assert window._progress.text() == 'En curso'
            assert '%' not in window._progress.text()
    window._set_busy(False)
    assert not window._progress.isVisible()
    assert window.btn_generate.isEnabled()


def test_hide_resize_and_destruction_are_safe(app, settings):
    owner = QWidget()
    page = QWidget(owner)
    owner.show()
    page.show()
    motion = MotionController(owner, settings)
    motion.reveal(page)
    page.hide()
    assert page.graphicsEffect() is None
    page.show()
    motion.reveal(page)
    page.resize(200, 100)
    assert page.graphicsEffect() is None
    motion.reveal(page)
    sip.delete(page)
    QTest.qWait(TRANSITION_MS + 20)
    assert motion.animation.state() == QAbstractAnimation.State.Stopped
    motion.finish()
    sip.delete(owner)


def test_close_cancels_pending_effect(window):
    window.tabs.setCurrentIndex(1)
    window.close()
    assert window._motion.animation.state() == QAbstractAnimation.State.Stopped
    assert window.schedule_viewer.graphicsEffect() is None


def test_invalid_saved_preference_is_safe(app, settings):
    settings.setValue(SETTINGS_KEY, 'invalid')
    owner = QWidget()
    motion = MotionController(owner, settings)
    assert not motion.reduced
    sip.delete(owner)


def test_status_preference_text_has_header_contrast(window):
    from PyQt6.QtGui import QColor, QPalette
    from src.gui.theme import COLORS
    assert window.chk_reduce_motion.palette().color(QPalette.ColorRole.WindowText) == QColor(COLORS['on_header_muted'])


def test_result_refresh_on_current_tab_is_animated(window):
    course = Course('BIO', 1, 60, 'REGULAR')
    window._classrooms = {'A1': Classroom('A1', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([course])
    window.tabs.setCurrentIndex(1)
    window._motion.finish()
    assignments = {'BIO-G1': ('A1', 1, 480, 540)}
    window._on_schedule_done(assignments, course.generate_groups())
    assert window.current_schedule == assignments
    assert window.schedule_viewer.graphicsEffect() is not None
    window.chk_reduce_motion.setChecked(True)
    window._on_schedule_done(assignments, course.generate_groups())
    assert window.schedule_viewer.graphicsEffect() is None
