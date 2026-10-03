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
