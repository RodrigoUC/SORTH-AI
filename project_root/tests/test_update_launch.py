"""Windows attachment policy gates; no test launches a real executable."""
from contextlib import contextmanager
import ctypes
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from src.application import app_updates, update_launch


@pytest.mark.parametrize('platform,frozen', [('linux', False), ('linux', True), ('win32', False),
                                           ('darwin', True)])
def test_unsupported_runtime_never_verifies_or_launches(monkeypatch, platform, frozen):
    monkeypatch.setattr(update_launch, 'sys', SimpleNamespace(platform=platform, frozen=frozen))
    monkeypatch.setattr(app_updates, 'verify_download', lambda *a, **k: pytest.fail('Must remain offline'))
    monkeypatch.setattr(update_launch, '_attachment_services', lambda: pytest.fail('Must not launch'))
    with pytest.raises(app_updates.UpdateError) as caught:
        update_launch.launch_pending_update(object())
    assert caught.value.code == 'unsupported_platform'


@pytest.fixture
def launch_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(update_launch, 'sys', SimpleNamespace(platform='win32', frozen=True))
    path = tmp_path / 'SORTH installer.exe'
    path.write_bytes(b'synthetic executable, never launched')
    source = 'https://github.com/RodrigoUC/SORTH-AI/releases/download/v2.1.0/SORTH-setup.exe'
    download = SimpleNamespace(path=path, release=SimpleNamespace(installer=SimpleNamespace(url=source)))
    events = []

    def verify(candidate, *, cancelled):
        assert candidate is download and not cancelled()
        events.append('verify')
        return path

    monkeypatch.setattr(app_updates, 'verify_download', verify)
    monkeypatch.setattr(update_launch, '_require_internet_zone', lambda local: events.append(('zone', local)))
    return download, events


def test_launch_uses_attachment_service_then_rehashes_before_native_execute(monkeypatch, launch_environment):
    download, events = launch_environment

    @contextmanager
    def attachment():
        events.append('COM')
        yield SimpleNamespace(prepare=lambda *args: events.append(('prepare', args)),
                              execute=lambda: events.append('native-execute'))
        events.append('release')

    monkeypatch.setattr(update_launch, '_attachment_services', attachment)
    update_launch.launch_pending_update(download)
    assert events == ['verify', 'COM', ('prepare', (download.path, download.release.installer.url)),
                      ('zone', download.path), 'verify', 'native-execute', 'release']


@pytest.mark.parametrize('stage', ['COM', 'prepare', 'zone', 'rehash', 'execute'])
def test_every_security_failure_aborts_without_any_fallback(monkeypatch, launch_environment, stage):
    download, events = launch_environment

    def fail():
        raise app_updates.UpdateError('windows_security_blocked')

    @contextmanager
    def attachment():
        if stage == 'COM':
            fail()
        try:
            def prepare(*args):
                events.append('prepare')
                if stage == 'prepare':
                    fail()
            def execute():
                events.append('native-execute')
                if stage == 'execute':
                    fail()
            yield SimpleNamespace(prepare=prepare, execute=execute)
        finally:
            events.append('release')

    original = app_updates.verify_download
    def verify(*args, **kwargs):
        if stage == 'rehash' and 'prepare' in events:
            raise app_updates.UpdateError('integrity_error')
        return original(*args, **kwargs)

    monkeypatch.setattr(update_launch, '_attachment_services', attachment)
    monkeypatch.setattr(app_updates, 'verify_download', verify)
    if stage == 'zone':
        monkeypatch.setattr(update_launch, '_require_internet_zone', lambda local: fail())
    with pytest.raises(app_updates.UpdateError):
        update_launch.launch_pending_update(download)
    assert events.count('native-execute') == (1 if stage == 'execute' else 0)
    assert ('release' in events) is (stage != 'COM')


@pytest.mark.parametrize('evidence,allowed', [
    (b'[ZoneTransfer]\r\nZoneId=3\r\nHostUrl=https://github.com/example\r\n', True),
    (b'[ZoneTransfer]\nZoneId=4\n', True),
    (b'[ZoneTransfer]\nZoneId=2\n', False),
    (b'[ZoneTransfer]\nZoneId=0\n', False),
    (b'[ZoneTransfer]\nZoneId=03\n', False),
    (b'[ZoneTransfer]\nZoneId=3\nZoneId=2\n', False),
    (b'[ZoneTransfer]\nZoneId=3\nzoneid=3\n', False),
    (b'[DEFAULT]\nZoneId=3\n[ZoneTransfer]\n', False),
    (b'invalid', False), (b'x' * 8193, False), (None, False),
])
def test_zone_evidence_is_bounded_valid_and_never_lowered(tmp_path, evidence, allowed):
    path = tmp_path / 'installer.exe'
    zone = Path(str(path) + ':Zone.Identifier')
    if evidence is not None:
        zone.write_bytes(evidence)
    if allowed:
        update_launch._require_internet_zone(path)
    else:
        with pytest.raises(app_updates.UpdateError):
            update_launch._require_internet_zone(path)
    assert zone.read_bytes() == evidence if evidence is not None else not zone.exists()


@pytest.mark.parametrize('failure_index', [3, 4, 5, 7, 9, 11, 12])
def test_native_failure_or_user_decline_stops_remaining_calls(monkeypatch, failure_index):
    calls, closed = [], []
    service = update_launch._AttachmentExecute(None, SimpleNamespace(CloseHandle=closed.append), None)

    def call(index, types=(), *args):
        calls.append(index)
        return -2147023673 if index == failure_index else 0  # HRESULT_FROM_WIN32(ERROR_CANCELLED)

    monkeypatch.setattr(service, '_call', call)
    with pytest.raises(app_updates.UpdateError):
        service.prepare(Path('/exact.exe'), 'https://github.com/validated')
        service.execute()
    assert calls[-1] == failure_index
    assert 12 not in calls if failure_index != 12 else calls.count(12) == 1
    assert not closed


def test_native_prompt_policy_continues_to_execute_with_handle_pointer(monkeypatch):
    calls, closed = [], []
    service = update_launch._AttachmentExecute(None,
        SimpleNamespace(CloseHandle=lambda handle: closed.append(handle.value)), None)

    def call(index, types=(), *args):
        calls.append(index)
        if index == 12:
            assert args[0] is None and args[1] is None
            ctypes.cast(args[2], ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.c_void_p(123)
        return 1 if index == 9 else 0

    monkeypatch.setattr(service, '_call', call)
    service.prepare(Path('/exact.exe'), 'https://github.com/validated')
    service.execute()
    assert calls == [3, 4, 5, 7, 9, 11, 12]
    assert closed == [123]


@pytest.mark.parametrize('initialize,create', [(0, 0), (1, 0), (-2147417850, 0), (0, -1), (0, 1)])
def test_com_initialization_ownership_and_create_failure(monkeypatch, initialize, create):
    calls = []

    def create_instance(clsid, outer, context, iid, pointer):
        calls.append('create')
        assert outer is None and context == 1
        ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.c_void_p(123)
        return create

    ole = SimpleNamespace(CoInitializeEx=lambda _, mode: calls.append(('init', mode)) or initialize,
                          CoCreateInstance=create_instance,
                          CoUninitialize=lambda: calls.append('uninit'))
    monkeypatch.setattr(update_launch, '_load_windows_apis', lambda: (ole, object(), object()))
    monkeypatch.setattr(update_launch, '_AttachmentExecute',
                        lambda *args: SimpleNamespace(release=lambda: calls.append('release')))
    if initialize not in (0, 1) or create != 0:
        with pytest.raises(app_updates.UpdateError):
            with update_launch._attachment_services():
                pytest.fail('Failed COM initialization must not yield a launcher')
    else:
        with update_launch._attachment_services():
            calls.append('use')
    assert ('uninit' in calls) is (initialize in (0, 1))
    assert ('release' in calls) is (initialize in (0, 1) and create == 0)
    assert ('create' in calls) is (initialize in (0, 1))


def test_unavailable_windows_api_never_falls_back(monkeypatch, launch_environment):
    download, events = launch_environment
    monkeypatch.setattr(update_launch, '_load_windows_apis',
                        lambda: (_ for _ in ()).throw(OSError('Unavailable Windows API')))
    with pytest.raises(app_updates.UpdateError) as caught:
        update_launch.launch_pending_update(download)
    assert caught.value.code == 'windows_security_unavailable'
    assert events == ['verify']


def test_launcher_has_no_plain_process_or_security_bypass_fallback():
    source = Path(update_launch.__file__).read_text(encoding='utf-8')
    assert 'import subprocess' not in source
    assert 'os.startfile' not in source
    assert 'ShellExecuteW(' not in source
    assert 'ShellExecuteExW(' not in source
    assert 'SEE_MASK_NOZONECHECKS' not in source


def test_fixed_vtable_binding_uses_sdk_slots_types_and_owns_handle():
    callbacks, calls, closed = [], [], []
    table = (ctypes.c_void_p * 15)()

    def install(index, types, implementation):
        callback = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, *types)(implementation)
        callbacks.append(callback)
        table[index] = ctypes.cast(callback, ctypes.c_void_p).value

    for index in (3, 5, 7):
        install(index, (ctypes.c_wchar_p,),
                lambda this, text, index=index: calls.append((index, text)) or 0)
    install(4, (ctypes.POINTER(update_launch._GUID),),
            lambda this, guid: calls.append((4, bytes(guid.contents))) or 0)
    for index in (2, 9, 11):
        install(index, (), lambda this, index=index: calls.append((index,)) or (1 if index == 9 else 0))

    def execute(this, hwnd, verb, process):
        calls.append((12, hwnd, verb, bool(process)))
        process[0] = ctypes.c_void_p(987)
        return 0

    install(12, (ctypes.c_void_p, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p)), execute)

    class Interface(ctypes.Structure):
        _fields_ = [('vtable', ctypes.POINTER(ctypes.c_void_p))]

    interface = Interface(table)
    service = update_launch._AttachmentExecute(ctypes.cast(ctypes.byref(interface), ctypes.c_void_p),
        SimpleNamespace(CloseHandle=lambda handle: closed.append(handle.value)), ctypes.CFUNCTYPE)
    path, source = Path('/exact installer.exe'), 'https://github.com/RodrigoUC/SORTH-AI/validated.exe'
    service.prepare(path, source)
    service.execute()
    service.release()
    assert calls == [(3, 'SORTH'), (4, bytes(update_launch._guid(update_launch._CLIENT))),
                     (5, str(path)), (7, source), (9,), (11,), (12, None, None, True), (2,)]
    assert ctypes.sizeof(update_launch._GUID) == 16
    assert closed == [987]


@pytest.mark.skipif(sys.platform != 'win32', reason='Real Windows COM and NTFS zone evidence are required')
def test_windows_native_attachment_save_marks_harmless_text_without_execution(tmp_path):
    """Exercise the real ABI/Save path, never execution or security approvals.

    Microsoft distinguishes Save (HRESULT) from explanatory SaveWithUI, which
    itself does not call Prompt. Run only the former on harmless text, in an
    isolated apartment with a timeout for unavailable/stalled security services.
    https://learn.microsoft.com/windows/win32/api/shobjidl_core/nf-shobjidl_core-iattachmentexecute-savewithui
    This is not SmartScreen/installer acceptance and does not run an installer.
    """
    path = tmp_path / 'sorth-native-attachment-fixture.txt'
    original = b'SORTH synthetic attachment provenance test. No executable content.\r\n'
    path.write_bytes(original)
    script = r'''
from pathlib import Path
import sys
from src.application import app_updates, update_launch

path = Path(sys.argv[1])
before = path.read_bytes()
calls = []
native_call = update_launch._AttachmentExecute._call

def save_only(self, index, types=(), *args):
    # Deliberately prohibit Prompt, Execute, SaveWithUI and every other slot.
    if index not in {2, 3, 4, 5, 7, 9, 11}:
        raise AssertionError('Native test must never execute or show approval UI')
    calls.append(index)
    return native_call(self, index, types, *args)

update_launch._AttachmentExecute._call = save_only
with update_launch._attachment_services() as attachment:
    # Provenance metadata only: the test creates its own harmless local bytes.
    # There is no HTTP download or call to launch_pending_update/Execute.
    attachment.prepare(path, app_updates.RELEASES_URL)
    update_launch._require_internet_zone(path)
    if path.read_bytes() != before:
        raise AssertionError('Attachment Save changed the synthetic text')
if calls != [3, 4, 5, 7, 9, 11, 2]:
    raise AssertionError('Unexpected native attachment method order')
print('native-attachment-save-and-zone-verified')
'''
    completed = subprocess.run([sys.executable, '-c', script, str(path)],
                               cwd=Path(__file__).resolve().parents[1],
                               capture_output=True, text=True, timeout=45, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == 'native-attachment-save-and-zone-verified'
    assert path.read_bytes() == original
    update_launch._require_internet_zone(path)
