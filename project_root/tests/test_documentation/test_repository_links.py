"""Validate first-party documentation paths without fetching external sites.

Use the existing Markdown parser so code blocks, reference links and images are
handled as Markdown, rather than guessing link syntax with a regular expression.
"""
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

REPOSITORY = Path(__file__).resolve().parents[3]


def documentation_files(repository):
    files = set(repository.glob("*.md"))
    for directory in (repository / "docs", repository / ".github"):
        files.update(directory.rglob("*.md"))
    application = repository / "project_root"
    files.update(application.glob("*.md"))
    for name in ("tools", "data/input", "assets", "security"):
        files.update((application / name).rglob("*.md"))
    # Vendored upstream notices retain their original bytes and links.
    files.update((repository / "third_party").glob("*.md"))
    files.update((repository / "third_party/mcp").glob("*.md"))
    return sorted(files)


def link_targets(markdown):
    def visit(tokens):
        for token in tokens:
            for name in ("href", "src"):
                target = token.attrGet(name)
                if target:
                    yield target
            if token.children:
                yield from visit(token.children)
    yield from visit(MarkdownIt("commonmark").parse(markdown))


def broken_links(path, repository):
    errors = []
    for href in link_targets(path.read_text(encoding="utf-8")):
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (path.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(repository) or not target.exists():
            errors.append(f"{path.relative_to(repository).as_posix()}: {href}")
    return errors


def test_local_documentation_links_and_images_exist():
    files = documentation_files(REPOSITORY)
    assert len(files) >= 40, "Documentation scan unexpectedly skipped its source tree"
    errors = [error for path in files for error in broken_links(path, REPOSITORY)]
    assert errors == []


def test_parser_handles_reference_links_images_encoded_paths_and_code(tmp_path):
    (tmp_path / "existing guide.md").write_text("# Guide", encoding="utf-8")
    path = tmp_path / "README.md"
    path.write_text("""[Existing][guide]
[guide]: existing%20guide.md#heading
![Missing](missing.png)
[Outside](../not-in-repository.md)
[External](https://example.org/no-local-file)
```markdown
[Not a link](not-a-link.md)
```
""", encoding="utf-8")
    assert broken_links(path, tmp_path) == ["README.md: missing.png",
                                             "README.md: ../not-in-repository.md"]
