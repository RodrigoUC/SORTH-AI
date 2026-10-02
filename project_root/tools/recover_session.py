"""Create a verified recovery candidate; never replace a live session.

Close every SORTH process first. Run from the source environment:
    python tools/recover_session.py --source BACKUP.db --output RECOVERED.db
Use a new output directory. Keep the full original data directory (including
WAL/SHM files) private and intact until the recovered session is verified.
"""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.infrastructure.session_repository import SessionRepository


def recover_candidate(source: Path, output: Path) -> Path:
    source, output = source.resolve(), output.absolute()
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite {output}')
    # The snapshot API opens the source read-only, includes committed WAL, and
    # checks SQLite integrity. All migrations/validation occur on our own copy.
    staged = SessionRepository._snapshot(source, output.parent, '.recovery-')
    try:
        repo = SessionRepository(str(staged))
        if repo.load_session() is None:
            raise ValueError('No saved session in this backup; choose another backup.')
        # Atomic no-clobber publication also protects against a competing output.
        os.link(staged, output)
        return output
    finally:
        staged.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        output = recover_candidate(args.source, args.output)
    except Exception as error:
        parser.exit(1, f'Recovery failed; the source was not replaced: {error}\n')
    print(f'Verified recovery candidate: {output}')
    print('Original data preserved. Close SORTH and preserve its entire data folder before manual activation.')


if __name__ == '__main__':
    main()
