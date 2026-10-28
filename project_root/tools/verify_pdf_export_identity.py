"""Verify actual frozen smoke PDF headers against the executable's build version."""
import argparse
import json
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def verify_exports(directory: Path, version: str) -> dict:
    """Read both language exports; every page must identify the reviewed build."""
    result = {}
    for name in ('schedule-es.pdf', 'schedule-en.pdf'):
        path = directory / name
        reader = PdfReader(path)
        if not reader.pages:
            raise ValueError(f'{name}: empty PDF')
        for number, page in enumerate(reader.pages, 1):
            header = (page.extract_text() or '').partition('\n')[0]
            if not header.startswith(f'SORTH {version} | '):
                raise ValueError(f'{name}: page {number} identifies another application version')
        result[name] = len(reader.pages)
    return {'ok': True, 'version': version, 'pages': result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output is not None:
        args.output.unlink(missing_ok=True)
    try:
        result = verify_exports(args.directory, args.version)
        code = 0
    except (OSError, ValueError, PdfReadError) as error:
        result = {'ok': False, 'error': str(error)}
        code = 1
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
