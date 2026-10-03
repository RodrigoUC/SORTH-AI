"""One atomic, versioned appearance record, independent of all domain settings.

The complete custom palette is owned here; deleting/moving its import file never
changes startup appearance. Reads do not rewrite corrupt/unknown data. Recovery
requires explicit consent and preserves the exact original in a sibling backup.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

from PyQt6.QtCore import QIODevice, QLockFile, QSaveFile

from .theme_contract import ThemeSpec, MAX_THEME_BYTES, parse_theme, validate_theme

MAX_PREFERENCE_BYTES = MAX_THEME_BYTES + 1024


class ThemePersistenceError(OSError):
    """Preferences were not committed; the caller must keep its prior appearance."""


def default_theme_path():
    if sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')
        if not root.is_absolute():
            root = Path.home() / 'AppData' / 'Local'
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library' / 'Preferences'
    else:
        root = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
        if not root.is_absolute():
            root = Path.home() / '.config'
    return root / 'SORTH' / 'appearance.json'


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate appearance preference key')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('Non-finite appearance preference value')


def _original():
    from .theme import builtin_themes
    return builtin_themes()[0]


def _read(path):
    try:
        with path.open('rb') as stream:
            raw = stream.read(MAX_PREFERENCE_BYTES + 1)
            stat = os.fstat(stream.fileno())
    except FileNotFoundError:
        return None, None
    # Track size and mtime as well as bounded content, including oversized files.
    snapshot = (len(raw), stat.st_size, stat.st_mtime_ns, hashlib.sha256(raw).digest())
    return raw, snapshot


def _decode(raw):
    if len(raw) > MAX_PREFERENCE_BYTES:
        raise ValueError('Appearance preferences exceed the supported size')
    record = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object,
                        parse_constant=_reject_constant)
    if (not isinstance(record, dict) or set(record) != {'version', 'selected', 'theme'}
            or type(record['version']) is not int or record['version'] != 1):
        raise ValueError('Unsupported appearance preference record')
    from .theme import builtin_themes
    builtins = {choice.key: choice.spec for choice in builtin_themes()}
    key = record['selected']
    if not isinstance(key, str) or key not in (*builtins, 'custom'):
        raise ValueError('Unknown selected appearance')
    # Delegate every palette rule (including strict size/contrast) to one owner.
    spec = parse_theme(json.dumps(record['theme'], ensure_ascii=False,
                                  separators=(',', ':'), allow_nan=False))
    if key != 'custom' and spec.to_dict() != builtins[key].to_dict():
        raise ValueError('Built-in appearance does not match its canonical palette')
    return key, spec


def _atomic_write(path, chunks):
    output = QSaveFile(str(path))
    output.setDirectWriteFallback(False)
    if not output.open(QIODevice.OpenModeFlag.WriteOnly):
        raise ThemePersistenceError('Could not open atomic appearance transaction')
    try:
        for chunk in chunks:
            if output.write(chunk) != len(chunk):
                raise ThemePersistenceError('Could not write complete appearance preferences')
        if not output.commit():
            raise ThemePersistenceError('Could not commit appearance preferences')
    finally:
        output.cancelWriting()


@contextmanager
def _writer_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(path) + '.lock')
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        raise ThemePersistenceError('Appearance preferences are being changed by another process')
    try:
        yield
    finally:
        lock.unlock()


class ThemePreferences:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_theme_path()
        self.current_key, self.current = _original().key, _original().spec
        self.recovery_issue = None
        self.last_backup_path = None
        self._snapshot = None
        try:
            raw, self._snapshot = _read(self.path)
            if raw is not None:
                self.current_key, self.current = _decode(raw)
        except (OSError, ValueError, TypeError, RecursionError) as error:
            self.recovery_issue = str(error)

    def save(self, spec: ThemeSpec, key='custom', *, recover=False):
        spec = validate_theme(spec.to_dict())
        from .theme import builtin_themes
        choices = {choice.key: choice.spec for choice in builtin_themes()}
        if key != 'custom' and (key not in choices or spec.to_dict() != choices[key].to_dict()):
            raise ValueError('Selected built-in appearance must match its canonical palette')
        record = {'version': 1, 'selected': key, 'theme': spec.to_dict()}
        data = (json.dumps(record, ensure_ascii=False, separators=(',', ':'),
                           allow_nan=False) + '\n').encode('utf-8')
        # Validate the exact normalized bytes before opening a write transaction.
        _decode(data)
        try:
            with _writer_lock(self.path):
                raw, snapshot = _read(self.path)
                if snapshot != self._snapshot:
                    raise ThemePersistenceError('Appearance preferences changed externally; reopen Appearance before saving')
                if self.recovery_issue and not recover:
                    raise ThemePersistenceError('Appearance preferences require explicit preserve-and-replace recovery')
                if self.recovery_issue and raw is not None:
                    backup = self.path.with_name(self.path.name + '.preserved-' + uuid.uuid4().hex + '.bak')
                    # Stream rather than truncate a possibly oversized corrupt file.
                    with self.path.open('rb') as source:
                        _atomic_write(backup, iter(lambda: source.read(65536), b''))
                    if _read(self.path)[1] != snapshot:
                        raise ThemePersistenceError('Appearance preferences changed during recovery; original preserved but not replaced')
                    self.last_backup_path = backup
                _atomic_write(self.path, (data,))
                # Commit is the success boundary. A later read failure must not
                # report that the committed preference was rejected.
                self.current_key, self.current = key, spec
                self.recovery_issue = None
                try:
                    _, self._snapshot = _read(self.path)
                except OSError:
                    self._snapshot = ('committed-but-not-reread',)
        except ThemePersistenceError:
            raise
        except (OSError, ValueError) as error:
            raise ThemePersistenceError(str(error)) from error
        self.current_key, self.current = key, spec
        self.recovery_issue = None
