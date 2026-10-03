"""Create a verified recovery candidate; never replace a live session.

Close every SORTH process first. Run from the source environment:
    python tools/recover_session.py --source BACKUP.db --output RECOVERED.db
Use a new output directory. Keep the full original data directory (including
WAL/SHM files) private and intact until the recovered session is verified.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.application.recovery_command import recover_candidate


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
