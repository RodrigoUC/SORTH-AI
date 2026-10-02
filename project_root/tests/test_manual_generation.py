"""Portable documentation checks; visual QA remains a release requirement."""
import re
import subprocess
import sys

import pytest
from pypdf import PdfReader
from reportlab.platypus import Table

from tools.build_manual import DEFAULT_OUTPUT, DEFAULT_SOURCE, MarkdownRenderer, build_manual


def compact(text):
    return re.sub(r"\s+", " ", text).strip()


def render(tmp_path, markdown):
    source = tmp_path / "source.md"
    source.write_text(markdown, encoding="utf-8")
    output = build_manual(source, tmp_path / "result.pdf")
    return PdfReader(output)


def annotations(reader):
    return [ref.get_object() for page in reader.pages for ref in page.get("/Annots", [])]


def test_current_manual_retains_content_links_and_numbered_pages(tmp_path):
    output = build_manual(output=tmp_path / "manual.pdf")
    reader = PdfReader(output)
    assert len(reader.pages) > 1
    text = compact(" ".join(page.extract_text() for page in reader.pages))
    assert "Mantén activas las protecciones de Windows." in text
    assert "No se puede afirmar que sea un falso positivo" in text
    assert "exclusión" not in text.lower()
    assert "desactiva" not in text.lower()
    assert "bullet" not in text
    for number, page in enumerate(reader.pages, 1):
        assert f"Página {number}" in page.extract_text()
    renderer = MarkdownRenderer(DEFAULT_SOURCE.read_text(encoding="utf-8"))
    for node in renderer.root.walk():
        if node.type in {"text", "code_inline", "fence", "code_block"}:
            assert compact(node.content) in text
    links = {annotation["/A"]["/URI"] for annotation in annotations(reader)}
    assert "https://github.com/RodrigoUC/SORTH-AI" in links
    assert "https://github.com/RodrigoUC/SORTH-AI/blob/main/project_root/WINDOWS_DISTRIBUTION.md" in links
    assert reader.trailer["/Root"]["/Lang"] == "es"
    assert reader.metadata.title == "Manual de usuario de SORTH"


def test_markdown_tables_nested_lists_code_accents_and_links(tmp_path):
    reader = render(tmp_path, """# Prueba de documentación

Texto **negrita**, *énfasis*, `ruta/niñez.xlsx` y [sitio](https://example.org/?a=1&b=2).

> Atención: ¿qué ocurre con pingüinos y árboles?

3. Tercer paso
   - Opción anidada
4. Cuarto paso

| Nombre | Día | Horas |
|:-------|:---:|------:|
| Biología | Miércoles | 08:00 |

```python
if horas < 2:
    print("áéíóú & <salida>")
```

[Volver](#prueba-de-documentación)
""")
    text = reader.pages[0].extract_text()
    assert "Atención: ¿qué ocurre con pingüinos y árboles?" in text
    assert "ruta/niñez.xlsx" in text
    assert '    print("áéíóú & <salida>")' in text
    assert "3\nTercer paso" in text
    assert "4\nCuarto paso" in text
    assert "•\nOpción anidada" in text
    assert "Miércoles" in text
    annots = annotations(reader)
    assert any(a.get("/A", {}).get("/URI") == "https://example.org/?a=1&b=2" for a in annots)
    assert any("/Dest" in a for a in annots)
    fonts = reader.pages[0]["/Resources"]["/Font"].get_object().values()
    embedded = [f.get_object().get("/FontDescriptor") for f in fonts]
    assert sum(bool(f and f.get_object().get("/FontFile2")) for f in embedded) >= 4


def test_generation_is_reproducible(tmp_path):
    first = build_manual(output=tmp_path / "first.pdf").read_bytes()
    second = build_manual(output=tmp_path / "second.pdf").read_bytes()
    assert first == second


def test_manual_tables_do_not_split_header_words():
    renderer = MarkdownRenderer(DEFAULT_SOURCE.read_text(encoding="utf-8"))
    tables = [flowable for flowable in renderer.blocks(renderer.root.children) if isinstance(flowable, Table)]
    assert len(tables) == 2
    for table in tables:
        for width, paragraph in zip(table._argW, table._cellvalues[0]):
            assert width >= paragraph.minWidth() + 14


def test_long_tables_repeat_headers_and_keep_all_rows(tmp_path):
    markdown = "# Tabla\n\n| Código | Descripción |\n|---|---|\n"
    markdown += "".join(f"| CURSO-{i:03d} | Biología y conservación |\n" for i in range(100))
    reader = render(tmp_path, markdown)
    assert len(reader.pages) >= 3
    text = " ".join(page.extract_text() for page in reader.pages)
    for number in range(100):
        assert f"CURSO-{number:03d}" in text
    assert all("Descripción" in page.extract_text() for page in reader.pages)


@pytest.mark.parametrize("markdown, message", [
    ("", "empty"),
    ("# Imagen\n\n![captura](https://example.org/image.png)", "Unsupported inline"),
    ("# Aviso\n\n🚀", "Unsupported character"),
    ("[volver](#no-existe)", "Unknown internal link"),
    ("[local](ftp://example.org/file)", "Unsupported link scheme"),
])
def test_invalid_sources_preserve_existing_output(tmp_path, markdown, message):
    source = tmp_path / "source.md"
    source.write_text(markdown, encoding="utf-8")
    output = tmp_path / "manual.pdf"
    output.write_bytes(b"previous approved PDF")
    with pytest.raises(ValueError, match=message):
        build_manual(source, output)
    assert output.read_bytes() == b"previous approved PDF"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["manual.pdf", "source.md"]


def test_source_cannot_be_overwritten(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("# Fuente", encoding="utf-8")
    with pytest.raises(ValueError, match="different files"):
        build_manual(source, source)
    with pytest.raises(ValueError, match=".pdf extension"):
        build_manual(source, tmp_path / "out.md")
    assert source.read_text(encoding="utf-8") == "# Fuente"


def test_cli_can_run_outside_project(tmp_path):
    script = DEFAULT_SOURCE.parent / "tools" / "build_manual.py"
    output = tmp_path / "manual.pdf"
    result = subprocess.run(
        [sys.executable, str(script), "--output", str(output)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_bytes().startswith(b"%PDF-")
    assert DEFAULT_OUTPUT == DEFAULT_SOURCE.parent / "build/docs/MANUAL_USUARIO.pdf"


def test_cli_returns_nonzero_for_missing_source(tmp_path):
    script = DEFAULT_SOURCE.parent / "tools" / "build_manual.py"
    result = subprocess.run(
        [sys.executable, str(script), "--source", str(tmp_path / "missing.md"),
         "--output", str(tmp_path / "manual.pdf")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "Manual build failed" in result.stderr
    assert not (tmp_path / "manual.pdf").exists()


def test_render_failure_preserves_output_and_cleans_temporary_file(tmp_path, monkeypatch):
    from tools import build_manual as manual_module

    source = tmp_path / "source.md"
    source.write_text("# Manual", encoding="utf-8")
    output = tmp_path / "manual.pdf"
    output.write_bytes(b"previous approved PDF")

    def fail(*args, **kwargs):
        raise RuntimeError("renderer failed")

    monkeypatch.setattr(manual_module.SimpleDocTemplate, "build", fail)
    with pytest.raises(RuntimeError, match="renderer failed"):
        build_manual(source, output)
    assert output.read_bytes() == b"previous approved PDF"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["manual.pdf", "source.md"]
