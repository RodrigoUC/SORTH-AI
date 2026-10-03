"""Integrity of supplementary native source evidence; not legal clearance."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_native_notice_original_bytes_and_inventory():
    data = json.loads((ROOT / 'third_party/native-source-inventory.json').read_text())
    base = ROOT / 'third_party/native-notices'
    paths = {row['path'] for row in data['files']}
    assert len(paths) == len(data['files'])
    assert paths == {p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()}
    for row in data['files']:
        raw = (base / row['path']).read_bytes()
        assert len(raw) == row['size']
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
    ids = {row['id'] for row in data['attributions']}
    assert {'psl-data', 'libpsl', 'xsvg', 'libtiff', 'libwebp', 'pcre2', 'freetype'} <= ids
    assert not {'cocoa-platform-plugin', 'qeventdispatcher_cf', 'android-native-style'} & ids
    assert len(data['source_archives']) == 8


def test_public_suffix_source_regenerates_exact_upstream_data(tmp_path):
    import subprocess
    import sys
    base = ROOT / 'third_party/native-notices'
    qt = base / 'qtbase-everywhere-src-6.11.2/src/3rdparty/libpsl'
    source = base / 'publicsuffix-e452c7058d6946bd76952b128c12f5ce87a5acb8/public_suffix_list.dat'
    output = tmp_path / 'psl.cpp'
    subprocess.run([sys.executable, str(qt / 'src/psl-make-dafsa'), str(source), str(output)], check=True)
    assert output.read_bytes() == (qt / 'psl_data.cpp').read_bytes()
    data = json.loads((ROOT / 'third_party/native-source-inventory.json').read_text())
    assert hashlib.sha256(output.read_bytes()).hexdigest() == data['psl_verification']['generated_cpp_sha256']
    assert data['psl_verification']['array_size'] == 56135
    assert data['psl_verification']['count'] == 1
