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
    report = json.loads((output / 'smoke-result.json').read_text(encoding='utf-8'))
    assert child.returncode == 0, (report, child.stderr)
    assert report['ok'] and report['frozen'] is False
    assert LEGACY_STAGES | THEME_STAGES <= set(report['stages'])
    assert report['assigned'] == report['groups'] == 42
    assert report['large_fixture']['assigned'] == 500
    assert [item['phase'] for item in report['theme_restarts']] == ['custom', 'fallback']
    for item in report['theme_restarts']:
        assert item['ok'] and item['frozen'] is False and item['pid'] != os.getpid()
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
