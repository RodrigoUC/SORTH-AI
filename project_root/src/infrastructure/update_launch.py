"""Confirmed Windows updates retain Attachment Manager policy and native prompts.

The GUI calls this only after safe close and release of session ownership. No
CreateProcess/Popen/ShellExecute fallback is allowed. Native acceptance remains
subject to Windows policy, antivirus services and the user's security decisions.
"""
from configparser import ConfigParser, Error as ConfigError
from contextlib import contextmanager
import ctypes
from pathlib import Path
import sys
from uuid import UUID

from . import app_updates

# Interface ABI and class ID: Microsoft's Windows SDK ShObjIdl_core.h/ShObjIdl.h.
# https://learn.microsoft.com/windows/win32/api/shobjidl_core/nn-shobjidl_core-iattachmentexecute
_CLSID = '4125dd96-e03a-4103-8f70-e0597d803b9c'
_IID = '73db1241-1e85-4581-8e4f-a81e1d0f8c57'
_CLIENT = '4ec05d20-53e0-4c68-82ad-1cc9b33f0afd'
_HRESULT = ctypes.c_int32


class _GUID(ctypes.Structure):
    _fields_ = [('data1', ctypes.c_uint32), ('data2', ctypes.c_uint16),
                ('data3', ctypes.c_uint16), ('data4', ctypes.c_ubyte * 8)]


def _guid(value):
    return _GUID.from_buffer_copy(UUID(value).bytes_le)


def installer_launch_supported() -> bool:
    return sys.platform == 'win32' and bool(getattr(sys, 'frozen', False))


def _require_ok(status, *, prompt=False):
    # Only CheckPolicy documents S_FALSE as permission to ask the user.
    # Setters, Save and Execute must return S_OK; cancellation never proceeds.
    if status not in ((0, 1) if prompt else (0,)):
        raise app_updates.UpdateError('windows_security_blocked')


def _load_windows_apis():
    # Search only the system directory, never the download/current directory.
    ole = ctypes.WinDLL('ole32.dll', winmode=0x00000800)
    kernel = ctypes.WinDLL('kernel32.dll', winmode=0x00000800)
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    ole.CoInitializeEx.restype = _HRESULT
    ole.CoCreateInstance.argtypes = [ctypes.POINTER(_GUID), ctypes.c_void_p,
                                    ctypes.c_uint32, ctypes.POINTER(_GUID),
                                    ctypes.POINTER(ctypes.c_void_p)]
    ole.CoCreateInstance.restype = _HRESULT
    ole.CoUninitialize.argtypes = []
    ole.CoUninitialize.restype = None
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int32
    return ole, kernel, ctypes.WINFUNCTYPE


class _AttachmentExecute:
    """Small, fixed IAttachmentExecute vtable binding; no arbitrary commands."""
    def __init__(self, pointer, kernel, prototype):
        self.pointer, self.kernel, self.prototype = pointer, kernel, prototype

    def _call(self, index, types=(), *args):
        vtable = ctypes.cast(self.pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        method = self.prototype(_HRESULT, ctypes.c_void_p, *types)(vtable[index])
        return method(self.pointer, *args)

    def prepare(self, path, source):
        _require_ok(self._call(3, (ctypes.c_wchar_p,), 'SORTH'))
        client = _guid(_CLIENT)
        _require_ok(self._call(4, (ctypes.POINTER(_GUID),), ctypes.byref(client)))
        _require_ok(self._call(5, (ctypes.c_wchar_p,), str(path)))
        # The original validated GitHub URL is the primary zone determinant.
        # Never substitute a local path, a signed redirect, or a trusted zone.
        _require_ok(self._call(7, (ctypes.c_wchar_p,), source))
        _require_ok(self._call(9), prompt=True)
        _require_ok(self._call(11))  # Save: policy/AV and zone evidence.

    def execute(self):
        process = ctypes.c_void_p()
        try:
            # A non-null HANDLE* requests synchronous launch. A null pointer
            # assumes a long-lived message pump, which has already ended here.
            # Execute owns any policy prompt; there is no runas verb or flags.
            _require_ok(self._call(12, (ctypes.c_void_p, ctypes.c_wchar_p,
                                       ctypes.POINTER(ctypes.c_void_p)),
                                   None, None, ctypes.byref(process)))
        finally:
            if process.value:
                self.kernel.CloseHandle(process)

    def release(self):
        self._call(2)


@contextmanager
def _attachment_services():
    ole, kernel, prototype = _load_windows_apis()
    # CoInitializeEx S_FALSE still requires matching CoUninitialize. A changed
    # apartment mode (RPC_E_CHANGED_MODE) or any failure refuses installation.
    _require_ok(ole.CoInitializeEx(None, 2), prompt=True)  # COINIT_APARTMENTTHREADED
    service = None
    try:
        pointer = ctypes.c_void_p()
        clsid, iid = _guid(_CLSID), _guid(_IID)
        _require_ok(ole.CoCreateInstance(ctypes.byref(clsid), None, 1,
                                        ctypes.byref(iid), ctypes.byref(pointer)))
        if not pointer.value:
            raise app_updates.UpdateError('windows_security_unavailable')
        service = _AttachmentExecute(pointer, kernel, prototype)
        yield service
    finally:
        try:
            if service is not None:
                service.release()
        finally:
            ole.CoUninitialize()


def _require_internet_zone(path):
    """Verify AES persisted Internet/restricted origin, without inventing it.

    Missing ADS support, disabled zone persistence, malformed evidence or a
    Trusted-site mapping all fail closed. We never unblock or lower file zones.
    https://learn.microsoft.com/openspecs/windows_protocols/ms-fscc/6e3f7352-d11c-4d76-8c39-2516a9df36e8
    """
    try:
        with Path(str(path) + ':Zone.Identifier').open('rb') as stream:
            data = stream.read(8193)
        if len(data) > 8192:
            raise ValueError('Zone evidence exceeds limit')
        parser = ConfigParser(interpolation=None, strict=True)
        parser.read_string(data.decode('utf-8-sig'))
        if parser.defaults() or parser.get('ZoneTransfer', 'ZoneId') not in ('3', '4'):
            raise ValueError('Internet-zone evidence required')
    except (OSError, UnicodeError, ConfigError, ValueError):
        raise app_updates.UpdateError('windows_security_unavailable') from None


def launch_pending_update(download: app_updates.DownloadResult):
    """Reverify, apply Windows attachment security, reverify and request launch."""
    if not installer_launch_supported():
        raise app_updates.UpdateError('unsupported_platform')
    path = app_updates.verify_download(download, cancelled=lambda: False)
    try:
        with _attachment_services() as service:
            service.prepare(path, download.release.installer.url)
            _require_internet_zone(path)
            # Save can invoke scanners that alter/delete the file. Its success
            # is not a substitute for the exact release's hash and path checks.
            if app_updates.verify_download(download, cancelled=lambda: False) != path:
                raise app_updates.UpdateError('integrity_error')
            service.execute()
    except (OSError, AttributeError, TypeError, ValueError):
        raise app_updates.UpdateError('windows_security_unavailable') from None
