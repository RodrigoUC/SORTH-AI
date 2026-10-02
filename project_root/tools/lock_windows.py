"""Write a hashed CPython 3.12/Windows x64 lock from an inspected wheel directory.

Fails if a Windows dependency is missing, including markers that pip download
may evaluate against the host rather than its --platform target.
"""
import argparse
import hashlib
from email.parser import Parser
from pathlib import Path
import zipfile

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.tags import cpython_tags, compatible_tags
from packaging.utils import canonicalize_name, parse_wheel_filename


def make_lock(wheel_dir: Path, output: Path):
    packages = {}
    supported = set(cpython_tags((3, 12), abis=["cp312"], platforms=["win_amd64"]))
    supported.update(compatible_tags((3, 12), interpreter="cp312", platforms=["win_amd64"]))
    for wheel in sorted(Path(wheel_dir).glob('*.whl')):
        name, version, _, tags = parse_wheel_filename(wheel.name)
        if not supported.intersection(tags):
            raise ValueError(f'Incompatible CPython 3.12/Windows x64 wheel: {wheel.name}')
        if name in packages:
            raise ValueError(f'Duplicate package wheel: {name}')
        with zipfile.ZipFile(wheel) as archive:
            metadata = Parser().parsestr(archive.read(next(
                path for path in archive.namelist() if path.endswith('.dist-info/METADATA'))).decode('utf-8'))
        packages[name] = (version, wheel, metadata.get_all('Requires-Dist', []))
    if not packages:
        raise ValueError('No wheels found.')
    environment = default_environment()
    environment.update(sys_platform='win32', platform_system='Windows', os_name='nt',
                       python_version='3.12', python_full_version='3.12.10',
                       platform_machine='AMD64', extra='')
    for name, (_, _, requirements) in packages.items():
        for text in requirements:
            dependency = Requirement(text)
            if dependency.marker and not dependency.marker.evaluate(environment):
                continue
            key = canonicalize_name(dependency.name)
            if key not in packages or packages[key][0] not in dependency.specifier:
                raise ValueError(f'Missing/incompatible Windows dependency: {name} requires {dependency}')
    lines = ['# CPython 3.12, Windows x64 only. Generated with tools/lock_windows.py.',
             '# Includes runtime, tests, PDF generation and PyInstaller; reviewed wheel SHA-256 hashes.',
             '# Install: python -m pip install --require-hashes -r requirements-windows.lock', '']
    for name, (version, wheel, _) in sorted(packages.items()):
        lines.append(f'{name}=={version} --hash=sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}')
    Path(output).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return len(packages)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel-dir', required=True, type=Path)
    parser.add_argument('--output', default=Path('requirements-windows.lock'), type=Path)
    args = parser.parse_args()
    print(f'Locked {make_lock(args.wheel_dir, args.output)} packages.')
