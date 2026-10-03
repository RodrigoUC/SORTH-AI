"""Console entrypoint for the self-contained optional SORTH MCP companion.

Dispatch before SDK imports. --worker performs one bounded pure calculation;
--probe never starts stdio, reads preferences, or changes local authorization.
"""
import argparse
import json
from pathlib import Path
import re
import sys


def _identity():
    if not getattr(sys, 'frozen', False):
        return None
    try:
        with (Path(sys._MEIPASS) / 'build-identity.json').open('rb') as stream:
            value = json.loads(stream.read(4097))
        if (not isinstance(value, dict)
                or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', value['version'])
                or not re.fullmatch(r'[0-9a-f]{40}', value['source_commit'])
                or value['build_id'] != value['version'] + '-' + value['source_commit'][:12]):
            return None
        return {key: value[key] for key in ('version', 'source_commit', 'build_id')}
    except (OSError, ValueError, TypeError, KeyError):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description='SORTH optional local MCP companion')
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--serve', action='store_true')
    modes.add_argument('--probe', action='store_true')
    modes.add_argument('--worker', action='store_true')
    parser.add_argument('--preferences')
    args = parser.parse_args(argv)
    if args.preferences is not None and not args.serve:
        parser.error('--preferences is only valid with --serve')
    if args.worker:
        from src.mcp_adapter.worker import main as worker
        worker()
        return 0
    if args.probe:
        from src.mcp_adapter.availability import SUPPORTED_VERSION, check
        identity = _identity()
        status = check(packaged=True)
        if getattr(sys, 'frozen', False) and identity is None:
            status = 'runtime_error'
        report = {'status': status, 'component': 'sorth-mcp',
                  'frozen': bool(getattr(sys, 'frozen', False)),
                  'sdk_version': SUPPORTED_VERSION, **(identity or {})}
        print(json.dumps(report, sort_keys=True))
        return 0 if status == 'available' else 2
    from src.mcp_adapter.server import main as serve
    arguments = ['--preferences', args.preferences] if args.preferences is not None else []
    return serve(arguments, packaged=True)


if __name__ == '__main__':
    raise SystemExit(main())
