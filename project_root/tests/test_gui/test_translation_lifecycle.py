"""Retired Python managers must not destroy Qt translators inside translation."""
import os
from pathlib import Path
import subprocess
import sys
import weakref

import pytest
from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QSettings

from src.gui.i18n import LanguageManager


def test_registered_objects_do_not_keep_retired_manager_alive(tmp_path):
    class Registered:
        def retranslate(self):
            pass

    manager = LanguageManager(QSettings(str(tmp_path / 'locale.ini'), QSettings.Format.IniFormat))
    registered = Registered()
    manager.register(registered)
    application = QCoreApplication.instance()
    translator = manager._translator
    assert translator.parent() is application
    application.removeTranslator(translator)
    manager_ref = weakref.ref(manager)
    del manager
    # Neither translator state nor registry cleanup callbacks create a cycle.
    assert manager_ref() is None
    assert not sip.isdeleted(translator)
    assert translator.translate('QPlatformTheme', 'Cancel') is None
    del registered  # Registry callback must also tolerate its manager's demise.


LIFECYCLE_SCRIPT = r'''
import faulthandler, gc, sys, weakref
from pathlib import Path
from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QSettings
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.gui.i18n import LanguageManager, _StandardTranslator
from src.gui.locales import Language, register_language

mode, directory = sys.argv[1], Path(sys.argv[2])
def make_manager(name):
    return LanguageManager(QSettings(str(directory / (name + '.ini')), QSettings.Format.IniFormat))

assert gc.isenabled()
if mode == 'before-application':
    retired = make_manager('retired')
    assert retired._translator is None
    app = QApplication([])
else:
    app = QApplication([])
    retired = make_manager('retired')
    app.removeTranslator(retired._translator)

class Registered:
    def retranslate(self):
        pass
registered = Registered()
if mode == 'registered':
    retired.register(registered)
if mode == 'external-cycle':
    retired.external_cycle = retired

retired_ref = weakref.ref(retired)
holder = [retired]
del retired
active = make_manager('active')
original = _StandardTranslator.translate
collected = []
def collecting(self, *args):
    if not collected:
        collected.append(True)
        # Qt's read lock is now held. This reproduces collection at the exact
        # unsafe boundary without relying on GC thresholds or disabling GC.
        holder.clear()
        gc.collect()
        assert retired_ref() is None
    return original(self, *args)
_StandardTranslator.translate = collecting

faulthandler.dump_traceback_later(5, exit=True)
assert QCoreApplication.translate('QPlatformTheme', 'Retry') == 'Reintentar'
assert collected and gc.isenabled()
assert active._translator.parent() is app
native = QMessageBox()
native.setStandardButtons(native.StandardButton.Retry | native.StandardButton.Discard | native.StandardButton.Cancel)
native.show()
app.processEvents()
for language, expected in [('en', ('Retry', 'Discard', 'Cancel')),
                           ('es', ('Reintentar', 'Descartar', 'Cancelar'))]:
    active.set_language(language, persist=False)
    app.processEvents()
    actual = tuple(native.button(button).text().replace('&', '') for button in
                   (native.StandardButton.Retry, native.StandardButton.Discard, native.StandardButton.Cancel))
    assert actual == expected, actual
register_language(Language('lifecycle-test', 'Test', 'fr_FR', {},
                           {'Cancel': 'Annuler', '&Cancel': '&Annuler'}, lambda n: 'other'))
active.set_language('lifecycle-test', persist=False)
app.processEvents()
assert native.button(native.StandardButton.Cancel).text().replace('&', '') == 'Annuler'
assert QCoreApplication.translate('QPlatformTheme', 'Cancel') == 'Annuler'
native.close()
app.removeTranslator(active._translator)
faulthandler.cancel_dump_traceback_later()
print('translation lifecycle passed', flush=True)
'''


@pytest.mark.parametrize('mode', ['plain', 'registered', 'external-cycle', 'before-application'])
def test_collection_inside_native_translation_is_bounded_and_preserves_labels(tmp_path, mode):
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run([sys.executable, '-B', '-c', LIFECYCLE_SCRIPT, mode, str(tmp_path)],
                            cwd=root, env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                            capture_output=True, text=True, timeout=12)
    assert result.returncode == 0, result.stderr
    assert 'translation lifecycle passed' in result.stdout



OWNER_LIFETIME_SCRIPT = r'''
import gc, sys, weakref
from PyQt6 import sip
from PyQt6.QtWidgets import QApplication, QWidget
from src.gui.i18n import msg, language_manager
from src.gui import i18n_widgets

mode = sys.argv[1]
app = QApplication([])
manager = language_manager()
manager.set_language('es', persist=False)
gc.disable()
def make_child():
    owner = QWidget()
    owner.cycle = owner
    return i18n_widgets.QLabel(msg('Código'), owner), weakref.ref(owner)
label, owner_ref = make_child()
other = i18n_widgets.QLabel(msg('Nombre'))
original_render = i18n_widgets._render
observed = []
def render(value):
    result = original_render(value)
    if not observed:
        observed.append(True)
        if mode == 'gc-owner':
            gc.collect()
            assert owner_ref() is not None and not sip.isdeleted(label)
        elif mode == 'explicit-owner-delete':
            sip.delete(label.parent())
            assert sip.isdeleted(label)
        elif mode == 'render-error-deleted':
            sip.delete(label)
            raise RuntimeError('translation failure sentinel')
        elif mode == 'render-error':
            raise RuntimeError('translation failure sentinel')
    return result
i18n_widgets._render = render
try:
    manager.set_language('en', persist=False)
except RuntimeError as error:
    assert mode in {'render-error', 'render-error-deleted'}, (mode, repr(error))
    assert str(error) == 'translation failure sentinel'
else:
    assert mode in {'gc-owner', 'explicit-owner-delete'}, mode
    assert other.text() == 'Name'
    assert not other.signalsBlocked()
    if mode == 'gc-owner':
        assert label.text() == 'Code' and not label.signalsBlocked()
        # Retention ends with the batch; it must not keep retired windows alive.
        gc.collect()
        assert owner_ref() is None and sip.isdeleted(label)
    else:
        assert sip.isdeleted(label)
assert observed
if not sip.isdeleted(label):
    assert not label.signalsBlocked()
gc.enable()
print('translation owner lifecycle passed', flush=True)
'''


@pytest.mark.parametrize('mode', ['gc-owner', 'explicit-owner-delete', 'render-error', 'render-error-deleted'])
def test_widget_owners_survive_translation_and_deleted_blockers_are_dismissed(mode):
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run([sys.executable, '-B', '-c', OWNER_LIFETIME_SCRIPT, mode],
                            cwd=root, env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                            capture_output=True, text=True, timeout=12)
    assert result.returncode == 0, result.stderr
    assert 'translation owner lifecycle passed' in result.stdout


NATIVE_OWNER_LIFETIME_SCRIPT = r'''
import gc, sys, time, traceback, weakref
from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QWidget, QDialog, QTableWidget
from src.gui.i18n import msg, language_manager
from src.gui import i18n_widgets as iw

kind, entry, mode = sys.argv[1:]
case = f'{kind}/{entry}/{mode}'
app = QApplication([])
manager = language_manager()
manager.set_language('es', persist=False)
owner = QWidget()
owner.cycle = owner
# Include an intermediate dialog/window: window() alone would retain that
# dialog, but not its owning QWidget, which can still delete the whole tree.
parent = QDialog(owner)
owner_ref = weakref.ref(owner)
parent_ref = weakref.ref(parent)
if kind in {'QLabel', 'QAction'}:
    child = getattr(iw, kind)(msg('Código'), parent)
    button = None
elif kind == 'QTableWidgetItem':
    table = QTableWidget(1, 1, parent)
    child = iw.QTableWidgetItem(msg('Código'))
    table.setItem(0, 0, child)
    del table
    button = None
else:
    widget_class = getattr(iw, kind)
    if entry in {'nested-native', 'style-native', 'sibling-native', 'sibling-style'}:
        class NestedButtonBox(widget_class):
            armed = False
            nested = False
            def changeEvent(self, event):
                super().changeEvent(event)
                if (self.armed and not self.nested and event.type() in
                        (QEvent.Type.LanguageChange, QEvent.Type.StyleChange)):
                    self.nested = True
                    QCoreApplication.sendEvent(getattr(self, 'peer', self),
                                               QEvent(QEvent.Type.LanguageChange))
        child = NestedButtonBox(parent)
    else:
        child = widget_class(parent)
    child.setStandardButtons(child.StandardButton.Save | child.StandardButton.Cancel)
    child.setButtonText(child.StandardButton.Save, msg('Guardar'))
    button = child.button(child.StandardButton.Save)
    if entry.startswith('sibling-'):
        child.peer = iw.QDialogButtonBox(iw.QDialogButtonBox.StandardButton.Save |
                                           iw.QDialogButtonBox.StandardButton.Cancel, parent)
    child.armed = True
# Keep the cycle rooted until the precise tested rendering/fitting boundary.
holder = [owner]
del owner, parent
observed = []
original_render = iw._render
expected = None

def boundary():
    if observed:
        return
    observed.append(True)
    holder.clear()
    if mode in {'gc-owner', 'gc-fit'}:
        gc.collect()
        assert owner_ref() is not None and not sip.isdeleted(child), \
            f'{case}: owner/child was collected inside the update'
    elif mode == 'delete-owner':
        sip.delete(owner_ref())
        assert sip.isdeleted(child)
    elif mode == 'delete-button':
        sip.delete(button)
    elif mode == 'delete-child':
        sip.delete(child)
    elif mode == 'render-error-deleted':
        sip.delete(child)
        raise RuntimeError('native translation failure sentinel')
    elif mode == 'render-error':
        raise RuntimeError('native translation failure sentinel')
    else:
        raise AssertionError(mode)

def render(value):
    result = original_render(value)
    if mode != 'gc-fit':
        boundary()
    return result

iw._render = render
if mode == 'gc-fit' and entry in {'timer', 'delayed-timer'}:
    original_hint = button.minimumSizeHint
    def hint():
        boundary()
        return original_hint()
    button.minimumSizeHint = hint
elif mode == 'gc-fit':
    original_fit = child._fit_actions
    def fit():
        boundary()
        original_fit()
    child._fit_actions = fit
# A Qt virtual dispatch reports Python errors to sys.excepthook, rather than
# raising them to sendEvent's caller. Capture that boundary without swallowing
# renderer failures in production or letting Qt abort this test subprocess.
errors = []
def report_error(kind, error, error_traceback):
    errors.append((kind, str(error)))
    traceback.print_exception(kind, error, error_traceback, file=sys.stderr)
sys.excepthook = report_error
assert gc.isenabled()
try:
    if entry in {'native', 'nested-native', 'sibling-native'}:
        QCoreApplication.sendEvent(child, QEvent(QEvent.Type.LanguageChange))
    elif entry in {'style-native', 'sibling-style'}:
        child.setStyleSheet('QPushButton { font-size: 20pt; }')
    elif entry in {'timer', 'delayed-timer'}:
        child._fit_signature = None
        completed = []
        # This observer runs after the already-connected production callback.
        # Do not call fitting ourselves: exercise an actual native timeout.
        child._metric_timer.timeout.connect(lambda: completed.append(True))
        child._metric_timer.start(20 if entry == 'delayed-timer' else 0)
        deadline = time.monotonic() + 2
        app.processEvents()
        # One processEvents pass is not a zero-timer completion barrier on
        # Windows. Yield Qt event turns until the callback actually returns.
        while not completed and not errors and time.monotonic() < deadline:
            QTest.qWait(1)
        assert completed, (f'{case}: metric timer did not complete within 2s; '
                           f'checkpoint={bool(observed)}, errors={errors!r}')
    elif entry == 'direct':
        child.retranslate()
    elif entry == 'setter':
        if button is None:
            child.setText(msg('Código'))
        else:
            child.setButtonText(child.StandardButton.Save, msg('Guardar'))
    else:
        raise AssertionError(entry)
except RuntimeError as error:
    errors.append((type(error), str(error)))
assert observed, f'{case}: rendering/fitting checkpoint was not reached'
assert gc.isenabled()
if mode.startswith('render-error'):
    assert errors == [(RuntimeError, 'native translation failure sentinel')], errors
else:
    assert not errors, errors
    if mode in {'gc-owner', 'gc-fit'}:
        assert not sip.isdeleted(child)
        if button is None:
            assert child.text() == 'Código'
        else:
            assert button.text() == 'Guardar'
    elif mode in {'delete-owner', 'delete-child'}:
        assert sip.isdeleted(child)
    else:
        assert sip.isdeleted(button)
        assert child.button(child.StandardButton.Cancel).text() == 'Cancelar'
# No global owner retention, GC disabling, or leaked decorator traceback refs.
gc.collect()
assert owner_ref() is None and parent_ref() is None, f'{case}: owner retained after update'
assert sip.isdeleted(child), f'{case}: child survived post-update owner collection'
print('native owner lifecycle passed', flush=True)
'''


@pytest.mark.parametrize('kind', ['QDialogButtonBox', 'ResponsiveDialogButtonBox', 'QMessageBox'])
@pytest.mark.parametrize('entry', ['native', 'direct', 'setter'])
@pytest.mark.parametrize('mode', ['gc-owner', 'delete-owner', 'delete-child', 'delete-button',
                                 'render-error', 'render-error-deleted'])
def test_native_button_translation_lifetime(tmp_path, kind, entry, mode):
    _run_native_owner_lifetime(tmp_path, kind, entry, mode)


@pytest.mark.parametrize('kind', ['QLabel', 'QAction', 'QTableWidgetItem'])
@pytest.mark.parametrize('entry', ['direct', 'setter'])
@pytest.mark.parametrize('mode', ['gc-owner', 'delete-owner', 'delete-child',
                                 'render-error', 'render-error-deleted'])
def test_direct_localized_property_lifetime(tmp_path, kind, entry, mode):
    _run_native_owner_lifetime(tmp_path, kind, entry, mode)


@pytest.mark.parametrize('entry', ['direct', 'native', 'timer', 'delayed-timer'])
def test_responsive_translation_retains_owner_through_fitting(tmp_path, entry):
    _run_native_owner_lifetime(tmp_path, 'ResponsiveDialogButtonBox', entry, 'gc-fit')


@pytest.mark.parametrize('kind', ['QDialogButtonBox', 'ResponsiveDialogButtonBox', 'QMessageBox'])
@pytest.mark.parametrize('entry', ['nested-native', 'style-native', 'sibling-native', 'sibling-style'])
@pytest.mark.parametrize('mode', ['gc-owner', 'delete-owner', 'delete-child',
                                 'render-error', 'render-error-deleted'])
def test_nested_native_translation_waits_for_outer_event(tmp_path, kind, entry, mode):
    _run_native_owner_lifetime(tmp_path, kind, entry, mode)


def _run_native_owner_lifetime(tmp_path, kind, entry, mode):
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, '-B', '-X', 'faulthandler', '-c', NATIVE_OWNER_LIFETIME_SCRIPT,
         kind, entry, mode], cwd=root,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'XDG_CONFIG_HOME': str(tmp_path)},
        capture_output=True, text=True, timeout=12)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'native owner lifecycle passed' in result.stdout


STYLE_TRANSLATION_SCRIPT = r'''
import sys
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QStyleFactory
from src.gui.i18n_widgets import ResponsiveDialogButtonBox

app = QApplication([])
class ReentrantButtonBox(ResponsiveDialogButtonBox):
    in_metric_event = False
    armed = False
    fitted = 0
    translated = 0
    def changeEvent(self, event):
        if self.armed and event.type() in (QEvent.Type.StyleChange, QEvent.Type.FontChange):
            self.in_metric_event = True
            try:
                # Reproduce native LanguageChange while style/font propagation
                # is still on the stack, before event() returns from super().
                QCoreApplication.sendEvent(self, QEvent(QEvent.Type.LanguageChange))
                self.translated += 1
                super().changeEvent(event)
            finally:
                self.in_metric_event = False
        else:
            super().changeEvent(event)
    def _fit_actions(self):
        assert not self.in_metric_event, 'layout fitting during native metric replacement'
        self.fitted += 1
        super()._fit_actions()

owner = QWidget()
layout = QVBoxLayout(owner)
box = ReentrantButtonBox(ResponsiveDialogButtonBox.StandardButton.Save |
                         ResponsiveDialogButtonBox.StandardButton.Cancel, owner)
layout.addWidget(box)
owner.show()
app.processEvents()
box.armed = True
before = box.fitted
if sys.argv[1] == 'stylesheet':
    owner.setStyleSheet('QPushButton { font-size: 20pt; }')
else:
    style = sys.argv[1]
    assert style in QStyleFactory.keys()
    app.setStyle(style)
assert box.translated > 0
assert box._metric_change_pending
for _ in range(3):
    app.processEvents()
assert not box._metric_change_pending
assert box.fitted > before
assert box.button(box.StandardButton.Save).text() == 'Guardar'
assert box.button(box.StandardButton.Cancel).text() == 'Cancelar'
owner.close()
print('native style translation passed', flush=True)
'''


@pytest.mark.parametrize('style', ['stylesheet', 'Fusion', 'Windows'])
def test_native_style_retranslation_defers_layout_until_metric_change_finishes(tmp_path, style):
    from PyQt6.QtWidgets import QStyleFactory
    if style != 'stylesheet' and style not in QStyleFactory.keys():
        pytest.skip(f'{style} style is unavailable')
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, '-B', '-X', 'faulthandler', '-c', STYLE_TRANSLATION_SCRIPT, style],
        cwd=root,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'XDG_CONFIG_HOME': str(tmp_path)},
        capture_output=True, text=True, timeout=12)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'native style translation passed' in result.stdout


REENTRANT_CAPTION_SCRIPT = r'''
import sys
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWidgets import QApplication
from src.gui import i18n_widgets as iw

app = QApplication([])
box = getattr(iw, sys.argv[1])()
box.setStandardButtons(box.StandardButton.Save | box.StandardButton.Cancel)
box.setButtonText(box.StandardButton.Cancel, 'Keep my literal cancel caption')
buttons = tuple(box.buttons())
original = iw._render
observed = []
def render(value):
    result = original(value)
    if not observed and getattr(value, 'source', None) == 'Guardar':
        observed.append(True)
        QCoreApplication.sendEvent(box, QEvent(QEvent.Type.LanguageChange))
    return result
iw._render = render
QCoreApplication.sendEvent(box, QEvent(QEvent.Type.LanguageChange))
assert observed
assert box.button(box.StandardButton.Cancel).text() == 'Keep my literal cancel caption'
assert tuple(box.buttons()) == buttons
assert iw._native_translations is None
print('reentrant custom caption passed', flush=True)
'''


@pytest.mark.parametrize('kind', ['QDialogButtonBox', 'ResponsiveDialogButtonBox', 'QMessageBox'])
def test_language_event_during_render_preserves_previously_applied_custom_caption(tmp_path, kind):
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, '-B', '-X', 'faulthandler', '-c', REENTRANT_CAPTION_SCRIPT, kind],
        cwd=root,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'XDG_CONFIG_HOME': str(tmp_path)},
        capture_output=True, text=True, timeout=12)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'reentrant custom caption passed' in result.stdout
