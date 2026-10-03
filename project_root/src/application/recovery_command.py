"""No-Python recovery entry point for the frozen application.

Never opens the user's default repository. Only creates a new candidate from an
explicit source; all original session/WAL files remain untouched.
"""
import argparse
import json
import os
from pathlib import Path
from ..infrastructure.session_repository import SessionRepository


def recover_candidate(source: Path, output: Path) -> Path:
    source, output = Path(source).resolve(), Path(output).absolute()
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite {output}')
    staged = SessionRepository._snapshot(source, output.parent, '.recovery-')
    try:
        repo = SessionRepository(str(staged))
        if repo.load_session() is None:
            raise ValueError('No saved session in this backup; choose another backup.')
        os.link(staged, output)
        return output
    finally:
        staged.unlink(missing_ok=True)


def run(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recover-session', action='store_true', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    # Windowed executables have no reliable console. Always provide a report,
    # reserve it without overwriting anything before touching the candidate.
    with args.report.open('x', encoding='utf-8') as report:
        try:
            output = recover_candidate(args.source, args.output)
            result = {'ok': True, 'candidate': str(output),
                      'schema_version': SessionRepository.SCHEMA_VERSION,
                      'activated': False,
                      'note': 'Original data preserved. Check candidate contents before manual activation.'}
            code = 0
        except Exception as error:
            result = {'ok': False, 'activated': False, 'error': str(error)}
            code = 1
        json.dump(result, report, ensure_ascii=False, indent=2)
        return code
