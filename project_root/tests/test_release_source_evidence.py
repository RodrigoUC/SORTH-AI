"""Preserved original supplier notices; integrity is not licensing clearance."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[2]
NOTICE_HASHES = {
    'cpython-3.12.10-embed-amd64-LICENSE.txt': 'e502c6b880ff58d614901495a9009c136539cd0b1e2a2abb8fc00b934c203419',
    'qt-v6.11.2-llvmpipe-NOTICES.txt': 'ca4eeeb4f8adc83e5cbef7c0cf802b1321f7fce102a9d8f0af7014822085a108',
    'llvm-3.6.2-MD5-NOTICES.txt': '27e149c532db0eb8cd5e96283e0c4a86c8a58ba6f894ca7a869dfd3cdee97ca5',
}


def test_supplier_notices_preserve_recorded_text():
    for name, expected in NOTICE_HASHES.items():
        # .gitattributes keeps original upstream bytes, including CRLF.
        raw = (ROOT / 'third_party/licenses' / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected


def test_source_evidence_keeps_final_artifact_and_runtime_scope_explicit():
    text = (ROOT / 'third_party/RELEASE_SOURCE_EVIDENCE.md').read_text(encoding='utf-8')
    assert 'ni identifica por sí sola los bytes del instalador final' in text
    assert 'falta repetirla contra los archivos del paquete final de SORTH' in text
    assert 'no afirma que esté publicado' in text
    assert 'no demuestra distribución ilícita ni implica comprar una licencia' in text
    assert 'THIRD-PARTY-SOURCES.tar.gz' in text
    assert 'project_root/tools/prepare_release_sources.py' in text
    for name in NOTICE_HASHES:
        assert name in text
