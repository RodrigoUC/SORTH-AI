"""Create/verify the dormant offline companion and its compiled GUI trust anchor.

Build tooling only. Digests detect replacement relative to the GUI's embedded
identity; neither a hash nor this unsigned package is a publisher signature.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import pprint
import re
import stat
import zipfile

try:
    from .build_identity import identity
    from .collect_license_notices import lock_digest
except ImportError:
    from build_identity import identity
    from collect_license_notices import lock_digest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'.db', '.sqlite', '.sqlite3', '.pyc', '.pyo'}
FORBIDDEN_MODULES = {'pyqt6', 'pyside6', 'pandas', 'numpy', 'openai', 'anthropic', 'torch'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                *(f'LPT{i}' for i in range(1, 10))}
    if (not name or len(name) > 240 or '\\' in name or ':' in name or path.is_absolute()
            or any(ord(character) < 32 for character in name)
            or any(part.split('.')[0].upper() in reserved for part in path.parts)
            or any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in name.split('/'))):
        raise ValueError('Unsafe payload member path')
    if path.suffix.lower() in FORBIDDEN:
        raise ValueError('Refusing session/cache data in companion')
    if any(p.split('.')[0].lower() in FORBIDDEN_MODULES for p in path.parts):
        raise ValueError('GUI/model dependency found in companion')
    return path


def verify_notices(notices, lock=ROOT / 'requirements-mcp-windows.lock'):
    """Require exact locked wheel inventory and byte-preserved upstream notices."""
    notices = Path(notices)
    inventory = json.loads((notices / 'wheel-inventory.json').read_text(encoding='utf-8'))
    if inventory.get('lock_sha256') != lock_digest(lock):
        raise ValueError('Companion license inventory is stale')
    expected = {}
    for line in Path(lock).read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        match = re.fullmatch(r'([\w.-]+)==([^ ]+) --hash=sha256:([a-f0-9]{64})', line)
        if not match:
            raise ValueError('Invalid companion lock entry')
        name, version, sha = match.groups()
        expected[re.sub(r'[-_.]+', '-', name).lower()] = (version, sha)
    actual = {}
    for row in inventory['packages']:
        name = re.sub(r'[-_.]+', '-', row['name']).lower()
        if name in actual:
            raise ValueError('Duplicate companion inventory row')
        actual[name] = (row['version'], row['sha256'])
        path = safe_name(row['notice_file'])
        content = (notices / path).read_bytes()
        if not row['upstream_notice_files']:
            raise ValueError('Missing upstream companion notices')
        for notice in row['upstream_notice_files']:
            begin = ('\n===== BEGIN ' + notice['path'] + ' =====\n').encode('utf-8')
            end = ('\n===== END ' + notice['path'] + ' =====\n').encode('utf-8')
            if content.count(begin) != 1 or content.count(end) != 1:
                raise ValueError('Incomplete upstream companion notices')
            original = content.split(begin, 1)[1].split(end, 1)[0]
            if digest(original) != notice['sha256']:
                raise ValueError('Modified upstream companion notice')
    if actual != expected:
        raise ValueError('Incomplete companion license inventory')
    return inventory


def create_payload(app_dir, archive, output, commit):
    # CLI defaults are relative to the build directory; the runtime consumer
    # deliberately requires absolute context paths, including output not yet made.
    app_dir, archive, output = (Path(path).resolve() for path in (app_dir, archive, output))
    info = identity(commit)
    if not (app_dir / 'SORTH-MCP.exe').is_file():
        raise ValueError('Build the Windows companion first')
    identity_file = app_dir / '_internal/build-identity.json'
    if json.loads(identity_file.read_text(encoding='utf-8')) != info:
        raise ValueError('Companion build identity differs from requested source')
    verify_notices(app_dir / '_internal/third_party/mcp')
    for name in ('LICENSE', 'LICENSING.md', 'third_party/licenses/cpython-3.12.10.txt'):
        if not (app_dir / '_internal' / name).is_file():
            raise ValueError('Required companion legal notice missing')
    rows, content, seen = [], {}, set()
    for path in sorted(app_dir.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlink in companion directory')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError('Nonregular companion member')
        name = path.relative_to(app_dir).as_posix()
        safe_name(name)
        if name.casefold() in seen:
            raise ValueError('Duplicate Windows companion path')
        seen.add(name.casefold())
        data = path.read_bytes()
        content[name] = data
        rows.append({'path': name, 'size': len(data), 'sha256': digest(data)})
    archive.parent.mkdir(parents=True, exist_ok=True)
    # No timestamps or permissions from the developer's machine enter the ZIP.
    with zipfile.ZipFile(archive, 'w') as zf:
        for name, data in content.items():
            member = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = 0o100644 << 16
            zf.writestr(member, data)
    data = archive.read_bytes()
    manifest = {'schema_version': 1, 'component': 'sorth-mcp',
                'version': info['version'], 'source_commit': info['source_commit'],
                'build_id': info['build_id'], 'platform': 'windows-x64',
                'sdk_version': '1.30.0', 'entrypoint': 'SORTH-MCP.exe',
                'archive': 'optional/mcp-component.zip', 'archive_sha256': digest(data),
                'archive_size': len(data), 'files': rows}
    # The producing tool and consuming installer must accept the same limits.
    # Only standard-library application code is imported, never the SDK or GUI.
    import sys
    sys.path.insert(0, str(ROOT))
    from src.application.mcp_component import ComponentContext, bundle_info
    bundle_info(context=ComponentContext(manifest, archive.parent, output))
    output.mkdir(parents=True, exist_ok=True)
    (output / 'mcp-component.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (output / '_sorth_mcp_bundle.py').write_text(
        '# Generated build identity, compiled into the GUI. Do not edit.\nMANIFEST = ' +
        pprint.pformat(manifest, sort_dicts=True) + '\n', encoding='utf-8')
    verify_payload(archive, output, commit)
    return manifest


def verify_payload(archive, output, commit):
    """Validate packaging inputs without importing or launching the companion."""
    archive, output = (Path(path).resolve() for path in (archive, output))
    manifest = json.loads((output / 'mcp-component.json').read_text(encoding='utf-8'))
    # Treat a generated Python anchor strictly as data, not executable code.
    module = ast.parse((output / '_sorth_mcp_bundle.py').read_text(encoding='utf-8'))
    if (len(module.body) != 1 or not isinstance(module.body[0], ast.Assign)
            or len(module.body[0].targets) != 1
            or not isinstance(module.body[0].targets[0], ast.Name)
            or module.body[0].targets[0].id != 'MANIFEST'
            or ast.literal_eval(module.body[0].value) != manifest):
        raise ValueError('Compiled companion anchor differs from manifest')
    expected = identity(commit)
    if any(manifest.get(k) != expected[k] for k in ('version', 'source_commit', 'build_id')):
        raise ValueError('Companion source identity mismatch')
    data = archive.read_bytes()
    if len(data) != manifest['archive_size'] or digest(data) != manifest['archive_sha256']:
        raise ValueError('Companion archive integrity mismatch')
    expected_files = {row['path']: row for row in manifest['files']}
    if len(expected_files) != len(manifest['files']):
        raise ValueError('Duplicate manifest member')
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        if len(members) != len(expected_files) or {i.filename for i in members} != set(expected_files):
            raise ValueError('Companion archive inventory mismatch')
        for member in members:
            safe_name(member.filename)
            if stat.S_ISLNK(member.external_attr >> 16) or member.is_dir():
                raise ValueError('Nonregular ZIP member')
            row = expected_files[member.filename]
            contents = zf.read(member)
            if len(contents) != row['size'] or digest(contents) != row['sha256']:
                raise ValueError('Companion member integrity mismatch')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('create', 'verify', 'notices'))
    parser.add_argument('--app-dir', type=Path, default=Path('dist/mcp/SORTH-MCP'))
    parser.add_argument('--archive', type=Path, default=Path('build/optional/mcp-component.zip'))
    parser.add_argument('--output', type=Path, default=Path('build/identity'))
    parser.add_argument('--notices', type=Path, default=Path('../third_party/mcp'))
    parser.add_argument('--commit')
    args = parser.parse_args()
    if args.command == 'notices':
        verify_notices(args.notices)
    elif args.command == 'create':
        create_payload(args.app_dir, args.archive, args.output, args.commit)
    else:
        verify_payload(args.archive, args.output, args.commit)
    print('Companion ' + args.command + ' verification passed.')


if __name__ == '__main__':
    main()
