"""Source smoke and launcher contracts; never evidence of frozen Windows success."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
LEGACY_STAGES = {
    'icon_svg_png_decode', 'bundled_excel_import', 'background_schedule',
    'excel_csv_export', 'pdf_export', 'sqlite_roundtrip', 'language_switch_es_en',
    'qt_render', 'course_dialog_edit_save', 'new_window_restore',
    'reopened_export_content', 'invalid_input_preserves_session',
    'large_workbook_schedule_export',
}
THEME_STAGES = {
    'theme_builtin_preview_cancel', 'theme_builtin_apply',
    'theme_unsafe_json_rejected', 'theme_custom_import_apply',
    'theme_custom_fresh_process_restart', 'theme_corrupt_fresh_process_fallback',
    'theme_preserves_session_and_preferences',
}


def source_smoke(output, env, *extra):
    return subprocess.run([sys.executable, str(ROOT / 'gui_app.py'), '--smoke-test',
                           '--smoke-output', str(output), *extra],
                          env=env, capture_output=True, text=True, timeout=100)


def checked_smoke_report(child, output):
    report_path = output / 'smoke-result.json'
    diagnostics = (f'Exit {child.returncode}\nstdout: {child.stdout}\nstderr: {child.stderr}\n'
                   + (report_path.read_text(encoding='utf-8') if report_path.exists() else 'No smoke report.'))
    assert child.returncode == 0, diagnostics
    assert report_path.is_file(), diagnostics
    return json.loads(report_path.read_text(encoding='utf-8'))


def test_source_smoke_covers_themes_without_touching_external_profile(tmp_path):
    external = tmp_path / 'normal-profile'
    external.mkdir()
    sentinel = external / 'do-not-change.json'
    sentinel.write_bytes(b'{"mcp_server": false, "reduced_motion": false}')
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA',
                'XDG_CONFIG_HOME', 'XDG_DATA_HOME'):
        env[key] = str(external)
    output = tmp_path / 'smoke output with spaces'
    child = source_smoke(output, env)
    report = checked_smoke_report(child, output)
    assert report['ok'] and report['frozen'] is False
    for relative in report['preference_paths'].values():
        path = (output / relative).resolve()
        assert path.is_relative_to(output / 'smoke-profile') and path.is_file()
    assert LEGACY_STAGES | THEME_STAGES <= set(report['stages'])
    assert report['assigned'] == report['groups'] == 42
    assert report['large_fixture']['assigned'] == 500
    assert [item['phase'] for item in report['theme_restarts']] == ['custom', 'fallback']
    for item in report['theme_restarts']:
        assert item['ok'] and item['frozen'] is False and item['pid'] != os.getpid()
        assert item['preference_paths'] == report['preference_paths']
        assert (output / f"theme-{item['phase']}-restart.png").stat().st_size > 0
    assert not (output / 'synthetic.sorth-theme.json').exists()
    assert sorted(path.name for path in external.iterdir()) == [sentinel.name]
    assert sentinel.read_bytes() == b'{"mcp_server": false, "reduced_motion": false}'
    # Refuse to reuse previous output instead of accepting old restart reports.
    again = source_smoke(output, env)
    assert again.returncode != 0
    assert json.loads((output / 'smoke-result.json').read_text(encoding='utf-8')) == report


def test_smoke_refuses_preexisting_profile_before_any_preference_write(tmp_path):
    output = tmp_path / 'output'
    profile = output / 'smoke-profile'
    profile.mkdir(parents=True)
    sentinel = profile / 'existing.json'
    sentinel.write_bytes(b'preserve exactly')
    child = source_smoke(output, dict(os.environ, QT_QPA_PLATFORM='offscreen'))
    assert child.returncode != 0
    assert list(profile.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b'preserve exactly'
    assert not (output / 'smoke-session.db').exists()


def test_restart_probe_rejects_missing_synthetic_profile(tmp_path):
    output = tmp_path / 'output'
    child = source_smoke(output, dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                         '--smoke-theme-probe', 'custom')
    report = json.loads((output / 'theme-custom-restart.json').read_text(encoding='utf-8'))
    assert child.returncode != 0 and not report['ok']
    assert 'existing synthetic smoke profile' in report['error']
    assert not (output / 'smoke-profile').exists()


@pytest.mark.parametrize('frozen', [False, True])
@pytest.mark.parametrize('failure', [None, 'mismatched_frozen', 'same_process', 'exit', 'timeout'])
def test_restart_launcher_requires_fresh_successful_matching_evidence(tmp_path, monkeypatch,
                                                                    frozen, failure):
    from PyQt6 import QtCore
    from src.application.packaged_workflow import _theme_restart
    started = []
    killed = []
    environments = []
    class Process:
        ExitStatus = SimpleNamespace(NormalExit=0)
        def setProcessEnvironment(self, environment):
            environments.append(environment.value('PYINSTALLER_RESET_ENVIRONMENT'))
        def start(self, executable, arguments):
            started.append((executable, arguments))
        def waitForStarted(self, timeout):
            return True
        def waitForFinished(self, timeout):
            if failure == 'timeout':
                return False
            report = {'ok': True, 'phase': 'custom',
                      'frozen': not frozen if failure == 'mismatched_frozen' else frozen,
                      'pid': os.getpid() if failure == 'same_process' else os.getpid() + 1}
            (tmp_path / 'theme-custom-restart.json').write_text(json.dumps(report), encoding='utf-8')
            return True
        def kill(self):
            killed.append(True)
        def errorString(self):
            return 'injected timeout'
        def readAllStandardError(self):
            return b''
        def exitStatus(self):
            return 0
        def exitCode(self):
            return 1 if failure == 'exit' else 0
    monkeypatch.setattr(QtCore, 'QProcess', Process)
    if failure:
        with pytest.raises(RuntimeError):
            _theme_restart(tmp_path, 'custom', frozen)
    else:
        assert _theme_restart(tmp_path, 'custom', frozen)['ok']
    executable, arguments = started[0]
    assert executable == sys.executable
    assert arguments[:1] == (['--smoke-test'] if frozen else [str(ROOT / 'gui_app.py')])
    assert arguments[-2:] == ['--smoke-theme-probe', 'custom']
    assert killed == ([True] if failure == 'timeout' else [])
    assert environments == (['1'] if frozen else [])


def test_named_qsettings_constructor_ignores_default_format(tmp_path):
    """Qt's named overload is NativeFormat even when the default is INI.

    Only inspect constructor metadata; never read or write native setting values.
    """
    from PyQt6.QtCore import QSettings
    previous = QSettings.defaultFormat()
    try:
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        named = QSettings('SORTH-smoke-constructor-contract', tmp_path.name)
        assert named.format() == QSettings.Format.NativeFormat
        explicit = QSettings(str(tmp_path / 'probe.ini'), QSettings.Format.IniFormat)
        assert explicit.format() == QSettings.Format.IniFormat
        assert Path(explicit.fileName()).resolve() == tmp_path / 'probe.ini'
    finally:
        QSettings.setDefaultFormat(previous)


def test_smoke_window_injects_every_settings_consumer_without_named_constructor(tmp_path):
    """Run with native/named construction forbidden, including on Linux CI."""
    script = r'''
import json
from pathlib import Path
import sys
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from src.application import packaged_smoke
from src.gui import features, i18n, motion, main_window

class ExplicitOnlySettings(QSettings):
    def __init__(self, *args, **kwargs):
        if len(args) != 2 or args[1] != QSettings.Format.IniFormat:
            raise RuntimeError('Native settings constructor forbidden in smoke')
        super().__init__(*args, **kwargs)

for module in (packaged_smoke, features, i18n, motion):
    module.QSettings = ExplicitOnlySettings
app = QApplication([])
output = Path(sys.argv[1]); output.mkdir()
packaged_smoke.configure_smoke_profile(output, create=True)
originals = main_window.MotionController, main_window.FeaturePreferences
window = packaged_smoke.create_smoke_window(output, restore_session=False)
paths = packaged_smoke.smoke_preference_paths(window, output)
if (main_window.MotionController, main_window.FeaturePreferences) != originals:
    raise RuntimeError('Smoke factories leaked beyond the window constructor')
if not window._motion.reduced or window._features.enabled('mcp_server'):
    raise RuntimeError('Synthetic preferences were not loaded')
window._motion.set_reduced(False)
i18n.language_manager().set_language('en')
settings = packaged_smoke.smoke_settings(output)
if str(settings.value('interface/reduced_motion')).lower() not in ('false', '0'):
    raise RuntimeError('Motion write escaped the explicit store')
if settings.value('interface/language') != 'en':
    raise RuntimeError('Language write escaped the explicit store')
window.close()
original_window = main_window.MainWindow
def fail_construction(*args, **kwargs):
    raise RuntimeError('injected construction failure')
main_window.MainWindow = fail_construction
try:
    try:
        packaged_smoke.create_smoke_window(output, restore_session=False)
    except RuntimeError as error:
        if str(error) != 'injected construction failure':
            raise
    else:
        raise RuntimeError('Construction failure was swallowed')
finally:
    main_window.MainWindow = original_window
if (main_window.MotionController, main_window.FeaturePreferences) != originals:
    raise RuntimeError('Smoke factories leaked after construction failed')
print(json.dumps(paths))
'''
    output = tmp_path / 'profile probe'
    child = subprocess.run([sys.executable, '-c', script, str(output)], cwd=ROOT,
                           env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                           capture_output=True, text=True, timeout=30)
    assert child.returncode == 0, child.stderr
    paths = json.loads(child.stdout.strip().splitlines()[-1])
    assert set(paths) == {'language', 'motion', 'feature_legacy', 'features', 'appearance'}
    for name, relative in paths.items():
        path = (output / relative).resolve()
        assert path.is_relative_to(output / 'smoke-profile')
        if name != 'appearance':
            assert path.is_file()
    assert paths['language'] == paths['motion'] == paths['feature_legacy']
    assert (output / paths['language']).suffix == '.ini'
    assert (output / paths['features']).name == 'optional-features.json'


def test_smoke_containment_guard_rejects_misdirected_adapter_before_write(tmp_path, monkeypatch):
    from PyQt6.QtCore import QSettings
    from src.application import packaged_smoke
    for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA',
                'XDG_CONFIG_HOME', 'XDG_DATA_HOME'):
        monkeypatch.setenv(key, str(tmp_path / 'external'))
    class MisdirectedSettings(QSettings):
        def fileName(self):
            return str(tmp_path / 'outside-profile.ini')
        def setValue(self, *args):
            pytest.fail('Containment must be checked before any settings write')
    monkeypatch.setattr(packaged_smoke, 'QSettings', MisdirectedSettings)
    with pytest.raises(RuntimeError, match='escaped the isolated profile'):
        packaged_smoke.configure_smoke_profile(tmp_path, create=True)
    assert not (tmp_path / 'outside-profile.ini').exists()
    assert not list((tmp_path / 'smoke-profile').rglob('*.json'))


def test_missing_smoke_report_exposes_subprocess_failure(tmp_path):
    child = subprocess.CompletedProcess([], 1, '', 'Smoke preferences escaped the isolated profile.')
    with pytest.raises(AssertionError, match='Smoke preferences escaped the isolated profile'):
        checked_smoke_report(child, tmp_path)
