"""Collect upstream wheel notices after checking every wheel against the build lock.

Offline evidence collector, not a legal compatibility/completeness decision.
Run from project_root; do not execute or import any wheel during collection.
"""
import argparse
import hashlib
import json
import re
from email.parser import Parser
from pathlib import Path
from zipfile import ZipFile


def lock_digest(lock):
    """Hash UTF-8/LF text so Git autocrlf does not change the lock identity."""
    return hashlib.sha256(Path(lock).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def collect(wheel_dir, lock, output):
    expected = {}
    for line in Path(lock).read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        match = re.fullmatch(r'([\w.-]+)==([^ ]+) --hash=sha256:([a-f0-9]{64})', line)
        if not match:
            raise ValueError('Unrecognized locked requirement: ' + line)
        name, version, digest = match.groups()
        expected[re.sub(r'[-_.]+', '-', name).lower()] = (version, digest)
    rows, notices, seen = [], {}, set()
    for wheel in sorted(Path(wheel_dir).glob('*.whl')):
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        with ZipFile(wheel) as archive:
            metadata_path = next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))
            metadata = Parser().parsestr(archive.read(metadata_path).decode('utf-8'))
            name = re.sub(r'[-_.]+', '-', metadata['Name']).lower()
            version = metadata['Version']
            if name in seen or expected.get(name) != (version, digest):
                raise ValueError('Unmatched, modified or duplicate wheel: ' + wheel.name)
            seen.add(name)
            paths = sorted(n for n in archive.namelist() if not n.endswith('/') and any(
                word in n.rsplit('/', 1)[-1].lower()
                for word in ('license', 'licence', 'copying', 'notice', 'copyright')))
            if not paths:
                raise ValueError('No notice files found: ' + wheel.name)
            records = []
            parts = [f'UPSTREAM NOTICES: {metadata["Name"]} {version}\nWheel: {wheel.name}\nSHA-256: {digest}\n',
                     'The following upstream text is preserved; inclusion does not imply every component ships in SORTH.\n']
            for path in paths:
                data = archive.read(path)
                text = data.decode('utf-8')
                records.append({'path': path, 'sha256': hashlib.sha256(data).hexdigest()})
                parts.extend([f'\n===== BEGIN {path} =====\n', text, f'\n===== END {path} =====\n'])
            filename = name + '.txt'
            notices[filename] = ''.join(parts)
            rows.append({'name': metadata['Name'], 'version': version, 'wheel': wheel.name,
                         'sha256': digest, 'license_expression': metadata.get('License-Expression'),
                         'license_metadata': metadata.get('License'),
                         'license_classifiers': [x for x in metadata.get_all('Classifier', []) if x.startswith('License')],
                         'upstream_urls': metadata.get_all('Project-URL', []) + ([metadata['Home-page']] if metadata.get('Home-page') else []),
                         'notice_file': 'licenses/' + filename, 'upstream_notice_files': records})
    if seen != set(expected):
        raise ValueError('Missing wheels: ' + ', '.join(sorted(set(expected) - seen)))
    output = Path(output)
    (output / 'licenses').mkdir(parents=True, exist_ok=True)
    for name, content in notices.items():
        (output / 'licenses' / name).write_bytes(content.encode('utf-8'))
    data = {'schema_version': 1, 'scope': 'all wheels in Windows build lock; not a frozen binary SBOM',
            'lock_sha256': lock_digest(lock), 'packages': rows}
    (output / 'wheel-inventory.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel-dir', type=Path, required=True)
    parser.add_argument('--lock', type=Path, default=Path('requirements-windows.lock'))
    parser.add_argument('--output', type=Path, default=Path('../third_party'))
    args = parser.parse_args()
    print(f'Collected {collect(args.wheel_dir, args.lock, args.output)} verified wheel inventories.')
