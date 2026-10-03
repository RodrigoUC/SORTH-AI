"""Qt/SDK-free MCP permission in the GUI's one optional-preferences record.

Fail closed. Cooperating writers lock the shared record; reads never change it.
"""
import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import uuid
from .optional_features import FEATURES

MAX_BYTES = 65536
MAX_DEPTH = 32


@contextmanager
def preferences_lock(path):
    """Nonblocking cross-process writer lock; never remove its stable inode.

    The sidecar holds no preferences or authority. An OS process exit releases
    the advisory lock, so callers must never delete it to force an unlock.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with Path(str(path) + '.lock').open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b'\0')
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise OSError('Preferences are being changed by another process') from error
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise OSError('Preferences are being changed by another process') from error
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def update_permission(record, value):
    """Rotate revocation identity on transitions or the first explicit legacy write."""
    if type(value) is not bool:
        raise ValueError('Expected a boolean permission')
    if ('mcp_generation' not in record or
            record['features'].get('mcp_server', False) != value):
        record['mcp_generation'] = uuid.uuid4().hex
    record['features']['mcp_server'] = value


def reject_constant(_):
    raise ValueError('Non-finite preference value')


def default_path():
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
    return root / 'SORTH' / 'optional-features.json'


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate preference key')
        result[key] = value
    return result


def read_record(path):
    path = Path(path)
    if not path.exists():
        return {'version': 1, 'features': {}}
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Preferences exceed the supported size')
    try:
        record = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except RecursionError as error:
        raise ValueError('Preferences exceed the supported nesting depth') from error
    pending = [(record, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > MAX_DEPTH:
            raise ValueError('Preferences exceed the supported nesting depth')
        if isinstance(value, dict):
            pending.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, list):
            pending.extend((child, depth + 1) for child in value)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Non-finite preference value')
    if (not isinstance(record, dict) or type(record.get('version')) is not int
            or record['version'] != 1 or not isinstance(record.get('features'), dict)
            or any(type(record['features'].get(feature.key, False)) is not bool for feature in FEATURES)):
        raise ValueError('Unsupported or damaged preferences')
    if 'mcp_generation' in record:
        generation = record['mcp_generation']
        if (not isinstance(generation, str) or len(generation) != 32
                or any(char not in '0123456789abcdef' for char in generation)):
            raise ValueError('Invalid MCP permission generation')
    return record


def permission_generation(path=None):
    """None means denied; old records migrate only on an explicit locked write."""
    try:
        record = read_record(default_path() if path is None else path)
        if record['features'].get('mcp_server') is True:
            return record.get('mcp_generation', 'legacy')
    except (OSError, ValueError, TypeError):
        return None
    return None


def enabled(path=None):
    return permission_generation(path) is not None


def set_enabled(path, value):
    """Atomic explicit CLI change, preserving unrelated settings; never repair silently."""
    if type(value) is not bool:
        raise ValueError('Expected a boolean permission')
    with preferences_lock(path):
        record = read_record(path)
        update_permission(record, value)
        _write_atomic(path, record)


def _write_atomic(path, record):
    data = (json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
    if len(data) > MAX_BYTES:
        raise ValueError('Preferences exceed the supported size')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description='Local MCP startup permission; no installation or model connection.')
    parser.add_argument('--preferences', type=Path, default=default_path())
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--enable', action='store_true')
    group.add_argument('--disable', action='store_true')
    args = parser.parse_args()
    try:
        if args.enable or args.disable:
            set_enabled(args.preferences, args.enable)
        record = read_record(args.preferences)
    except (OSError, ValueError, TypeError):
        print('Preferences unavailable; original preserved.', file=sys.stderr)
        return 2
    print('enabled' if record['features'].get('mcp_server') is True else 'disabled')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
