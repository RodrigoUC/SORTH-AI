import json
from pathlib import Path
import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox
from src.gui import features
from src.gui.features import FeaturePreferences, FEATURES
from src.gui.settings_dialog import SettingsDialog
from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository

OFF = {feature.key: False for feature in FEATURES}
ON = {feature.key: True for feature in FEATURES}


def preferences(tmp_path):
    settings = QSettings(str(tmp_path/'legacy.ini'), QSettings.Format.IniFormat)
    return FeaturePreferences(settings, path=tmp_path/'features.json')


def test_real_malformed_ini_never_mutates_or_migrates(tmp_path):
    path = tmp_path/'legacy.ini'
    original = b'[broken\nforeign=x\n'
    path.write_bytes(original)
    settings = QSettings(str(path), QSettings.Format.IniFormat)
    prefs = FeaturePreferences(settings, path=tmp_path/'features.json')
    assert prefs.load_error and prefs.values() == OFF
    with pytest.raises(OSError):
        prefs.save(ON)
    settings.sync()
    assert path.read_bytes() == original
    assert not prefs.path.exists() and prefs.values() == OFF
    prefs.recover_defaults()
    assert path.read_bytes() == original and prefs.values() == OFF


@pytest.mark.parametrize('raw', [b'{broken', b'{"version":99,"features":{}}',
                                b'{"version":1,"version":1,"features":{}}',
                                b'{"version":1,"features":{"pinned_sessions":"true"}}'])
def test_corrupt_future_json_requires_explicit_recovery(tmp_path, raw):
    prefs = preferences(tmp_path)
    prefs.path.write_bytes(raw)
    prefs = preferences(tmp_path)
    assert prefs.load_error
    with pytest.raises(OSError):
        prefs.save(ON)
    assert prefs.path.read_bytes() == raw and prefs.values() == OFF
    backup = prefs.recover_defaults()
    assert backup.read_bytes() == raw
    assert json.loads(prefs.path.read_bytes())['features'] == OFF


@pytest.mark.parametrize('failure', ['open', 'write', 'commit'])
def test_atomic_io_failure_keeps_exact_bytes_and_committed_flags(tmp_path, monkeypatch, failure):
    prefs = preferences(tmp_path)
    prefs.save({**prefs.values(), 'pinned_sessions': True, 'project_scenarios': False})
    original, committed = prefs.path.read_bytes(), prefs.values()
    real = features.QSaveFile
    class FailedSave:
        def __init__(self, path):
            self.inner = real(path)
        def setDirectWriteFallback(self, value):
            assert value is False
            self.inner.setDirectWriteFallback(value)
        def open(self, flags):
            return False if failure == 'open' else self.inner.open(flags)
        def write(self, data):
            return self.inner.write(data[:3]) if failure == 'write' else self.inner.write(data)
        def commit(self):
            return False if failure == 'commit' else self.inner.commit()
        def cancelWriting(self):
            self.inner.cancelWriting()
    monkeypatch.setattr(features, 'QSaveFile', FailedSave)
    with pytest.raises(OSError):
        prefs.save(ON)
    assert prefs.path.read_bytes() == original and prefs.values() == committed
    assert preferences(tmp_path).values() == committed


def test_unknown_fields_preserved_and_unrelated_legacy_untouched(tmp_path):
    prefs = preferences(tmp_path)
    prefs.settings.setValue('interface/reduced_motion', True)
    prefs.settings.sync()
    original = Path(prefs.settings.fileName()).read_bytes()
    prefs.path.write_text(json.dumps({'version': 1, 'features': {'future': {'a': 1}}, 'future_root': [1,2]}))
    prefs.save(ON)
    saved = json.loads(prefs.path.read_bytes())
    assert saved['features']['future'] == {'a': 1} and saved['future_root'] == [1,2]
    assert Path(prefs.settings.fileName()).read_bytes() == original
    assert not prefs.enabled('future')


def test_recovery_cancel_preserves_bad_bytes_and_accept_resets_only_tools(tmp_path, monkeypatch):
    q = QSettings(str(tmp_path/'prefs.ini'), QSettings.Format.IniFormat)
    path = Path(q.fileName()+'.features.json')
    path.write_bytes(b'broken')
    window = MainWindow(SessionRepository(str(tmp_path/'session.db')), restore_session=False, feature_settings=q)
    dialog = SettingsDialog(window)
    assert not dialog.recover_button.isHidden()
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.Cancel)
    dialog.recover_preferences()
    assert path.read_bytes() == b'broken'
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.Yes)
    dialog.recover_preferences()
    assert window._features.values() == OFF
    assert list(tmp_path.glob('*.preserved-*.bak'))[0].read_bytes() == b'broken'
    dialog.close();window.close()
