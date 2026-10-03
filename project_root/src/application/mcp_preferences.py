"""Qt/SDK-free MCP permission in the GUI's one optional-preferences record.

Fail closed. This permission is read at server startup, not a process supervisor.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .optional_features import FEATURES

MAX_BYTES = 65536


def default_path():
    if sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library' / 'Preferences'
    else:
        root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
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
    record = json.loads(raw, object_pairs_hook=unique_object)
    if (not isinstance(record, dict) or type(record.get('version')) is not int
            or record['version'] != 1 or not isinstance(record.get('features'), dict)
            or any(type(record['features'].get(feature.key, False)) is not bool for feature in FEATURES)):
        raise ValueError('Unsupported or damaged preferences')
    return record


def enabled(path=None):
    try:
        return read_record(default_path() if path is None else path)['features'].get('mcp_server') is True
    except (OSError, ValueError, TypeError):
        return False


def set_enabled(path, value):
    """Atomic explicit CLI change, preserving unrelated settings; never repair silently."""
    if type(value) is not bool:
        raise ValueError('Expected a boolean permission')
    record = read_record(path)
    record['features']['mcp_server'] = value
    data = (json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')
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
