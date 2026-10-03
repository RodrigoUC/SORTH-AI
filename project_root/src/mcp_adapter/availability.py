"""Local import/construction smoke test. Never starts stdio, tools or a listener.

Run in a bounded subprocess so a broken dependency cannot freeze settings.
"""
import importlib.metadata
import json
import sys

SUPPORTED_VERSION = '1.30.0'


def check(*, packaged=False):
    if getattr(sys, 'frozen', False) and not packaged:
        return 'frozen_unsupported'
    try:
        version = importlib.metadata.version('mcp')
    except importlib.metadata.PackageNotFoundError:
        return 'missing_sdk'
    except Exception:
        return 'runtime_error'
    if version != SUPPORTED_VERSION:
        return 'incompatible_sdk'
    try:
        import openpyxl
        if openpyxl.__version__ != "3.1.5":
            return "runtime_error"
        from .server import build_server
        if packaged:
            build_server(packaged=True)
        else:
            build_server()
    except Exception:
        return 'runtime_error'
    return 'available'


def main():
    print(json.dumps({'status': check()}))


if __name__ == '__main__':
    main()
