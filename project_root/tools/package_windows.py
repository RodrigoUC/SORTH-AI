"""Create review-only unsigned Windows ZIP and checksums without publishing."""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LEGAL_FILES = ('LICENSE', 'LICENSING.md', 'CREDITS.md', 'SUPPORT.md', 'SECURITY.md',
               'docs/LICENSING_REVIEW.md', 'docs/SOURCE_AVAILABILITY.md')


FORBIDDEN_SUFFIXES = {'.db', '.sqlite', '.sqlite3', '.pyc'}


def package(app_dir: Path, manual: Path, output_dir: Path, commit: str) -> Path:
    app_dir, manual, output_dir = map(Path, (app_dir, manual, output_dir))
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('A full 40-character source commit SHA is required.')
    if not (app_dir / 'SORTH.exe').is_file():
        raise ValueError('SORTH.exe is missing; build and smoke-test the onedir app first.')
    if not manual.is_file() or manual.read_bytes()[:5] != b'%PDF-':
        raise ValueError('Generate a valid current manual PDF before packaging.')
    files = sorted(path for path in app_dir.rglob('*') if path.is_file())
    for path in files:
        if path.is_symlink() or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise ValueError(f'Refusing to package local session/cache data: {path.name}')
    legal = [REPOSITORY_ROOT / name for name in LEGAL_FILES]
    legal.extend(sorted(path for path in (REPOSITORY_ROOT / 'third_party').rglob('*') if path.is_file()))
    if not legal or any(not path.is_file() or path.is_symlink() for path in legal):
        raise ValueError('Required license/notice files are missing or symlinked.')
    if not (REPOSITORY_ROOT / 'third_party/wheel-inventory.json').is_file():
        raise ValueError('Verified third-party wheel inventory is missing.')
    inventory = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    info = {
        'source_commit': commit,
        'distribution': 'Windows x64 onedir review build',
        'signed': False,
        'security_validation': 'No claim of malware clearance or SmartScreen reputation',
        'python': platform.python_version(),
        'build_platform': platform.platform(),
        'dependencies': inventory.splitlines(),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f'SORTH-windows-x64-{commit[:12]}-unsigned.zip'
    if archive.exists():
        raise ValueError('Output archive already exists; use a fresh output directory.')

    def write_member(zf, name, data):
        item = zipfile.ZipInfo('SORTH/' + name, date_time=(1980, 1, 1, 0, 0, 0))
        item.compress_type = zipfile.ZIP_DEFLATED
        item.external_attr = 0o100644 << 16
        zf.writestr(item, data)

    with zipfile.ZipFile(archive, 'w') as zf:
        for path in files:
            write_member(zf, path.relative_to(app_dir).as_posix(), path.read_bytes())
        for path in legal:
            write_member(zf, path.relative_to(REPOSITORY_ROOT).as_posix(), path.read_bytes())
        write_member(zf, 'MANUAL_USUARIO.pdf', manual.read_bytes())
        write_member(zf, 'build-info.json', json.dumps(info, ensure_ascii=False, indent=2).encode('utf-8'))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output_dir / 'SHA256SUMS.txt').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    (output_dir / 'build-info.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir', type=Path, default=Path('dist/SORTH'))
    parser.add_argument('--manual', type=Path, default=Path('build/docs/MANUAL_USUARIO.pdf'))
    parser.add_argument('--output', type=Path, default=Path('build/artifacts'))
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    print(package(args.app_dir, args.manual, args.output, args.commit))


if __name__ == '__main__':
    main()
