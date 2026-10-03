"""Build the Spanish user manual from Markdown without network or native tools.

Supports CommonMark headings, paragraphs, lists, quotes, fenced/indented code,
links and Markdown tables. Images and unsupported glyphs fail explicitly rather
than producing an incomplete PDF. Relative links point to repository documents.
Install requirements-docs.txt, then run this file from any working directory.
"""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re
import tempfile
from urllib.parse import quote, unquote, urljoin, urlsplit

import reportlab
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    HRFlowable, ListFlowable, ListItem, Paragraph, Preformatted,
    SimpleDocTemplate, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT.parent / "docs" / "user" / "MANUAL_USUARIO.md"
DEFAULT_OUTPUT = ROOT / "build" / "docs" / "MANUAL_USUARIO.pdf"
REPOSITORY_DOCS = "https://github.com/RodrigoUC/SORTH-AI/blob/main/docs/user/"
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 48
CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2 - 12  # SimpleDocTemplate frame padding


def _register_fonts() -> None:
    fonts = Path(reportlab.__file__).resolve().parent / "fonts"
    for name, filename in (("SorthSans", "Vera.ttf"), ("SorthSans-Bold", "VeraBd.ttf"),
                           ("SorthSans-Italic", "VeraIt.ttf"), ("SorthSans-BoldItalic", "VeraBI.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    pdfmetrics.registerFontFamily(
        "SorthSans", normal="SorthSans", bold="SorthSans-Bold",
        italic="SorthSans-Italic", boldItalic="SorthSans-BoldItalic",
    )
    pdfmetrics.registerFont(TTFont("SorthMono", str(ROOT / "tools/fonts/DejaVuSansMono.ttf")))
    pdfmetrics.registerFontFamily("SorthMono", normal="SorthMono", bold="SorthMono",
                                  italic="SorthMono", boldItalic="SorthMono")


def _slug(text: str) -> str:
    """GitHub-style heading IDs for the manual's internal links."""
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


def _plain(node: SyntaxTreeNode) -> str:
    if node.type in {"text", "code_inline"}:
        return node.content
    return "".join(_plain(child) for child in node.children)


def _validate_glyphs(text: str) -> None:
    # Every style must have a glyph; do not silently substitute black squares.
    font_names = ("SorthSans", "SorthSans-Bold", "SorthSans-Italic", "SorthSans-BoldItalic", "SorthMono")
    for glyph in set(text) - {"\n", "\r", "\t"}:
        if any(ord(glyph) not in pdfmetrics.getFont(name).face.charToGlyph for name in font_names):
            raise ValueError(
                f"Unsupported character U+{ord(glyph):04X} ({glyph!r}); "
                "use Spanish text without decorative emoji or unsupported symbols."
            )


class MarkdownRenderer:
    def __init__(self, markdown: str):
        _register_fonts()
        _validate_glyphs(markdown)
        self.root = SyntaxTreeNode(
            MarkdownIt("commonmark", {"html": False}).enable("table").parse(markdown)
        )
        self.anchors: dict[int, str] = {}
        counts: dict[str, int] = {}
        for node in self.root.walk():
            if node.type == "heading":
                slug = _slug(_plain(node)) or "section"
                count = counts.get(slug, 0)
                counts[slug] = count + 1
                self.anchors[id(node)] = f"{slug}-{count}" if count else slug
        self.styles = self._styles()

    @staticmethod
    def _styles() -> dict[str, ParagraphStyle]:
        body = ParagraphStyle(
            "Body", fontName="SorthSans", fontSize=10, leading=14,
            textColor=colors.HexColor("#202733"), spaceAfter=7,
            allowWidows=0, allowOrphans=0,
        )
        styles = {"body": body}
        for level, size in enumerate((22, 15, 12, 10.5, 10, 10), 1):
            styles[f"h{level}"] = ParagraphStyle(
                f"Heading{level}", parent=body, fontName="SorthSans-Bold",
                fontSize=size, leading=size * 1.25, textColor=colors.black,
                spaceBefore=16 if level > 1 else 0, spaceAfter=8,
                keepWithNext=True,
            )
        styles["table"] = ParagraphStyle(
            "Table", parent=body, fontSize=8.3, leading=11, spaceAfter=0,
        )
        styles["code"] = ParagraphStyle(
            "Code", parent=body, fontName="SorthMono", fontSize=8.5,
            leading=11, spaceBefore=3, spaceAfter=9,
        )
        return styles

    def _link(self, href: str) -> str:
        if href.startswith("#"):
            if unquote(href[1:]) not in self.anchors.values():
                raise ValueError(f"Unknown internal link: {href}")
            return "#" + unquote(href[1:])
        parsed = urlsplit(href)
        if parsed.scheme and parsed.scheme not in {"https", "http", "mailto"}:
            raise ValueError(f"Unsupported link scheme: {parsed.scheme}")
        if not parsed.scheme:
            if parsed.netloc or href.startswith("/"):
                raise ValueError(f"Use an explicit https URL: {href}")
            href = urljoin(REPOSITORY_DOCS, href)
        return quote(href, safe=":/#?=&%+@,;~!$'()*[]-")

    def inline(self, node: SyntaxTreeNode) -> str:
        kind = node.type
        if kind in {"text", "code_inline"}:
            value = escape(node.content)
            return f'<font name="SorthMono">{value}</font>' if kind == "code_inline" else value
        if kind == "softbreak":
            return " "
        if kind == "hardbreak":
            return "<br/>"
        inner = "".join(self.inline(child) for child in node.children)
        if kind in {"inline", "paragraph", "heading", "th", "td"}:
            return inner
        if kind in {"strong", "em"}:
            tag = "b" if kind == "strong" else "i"
            return f"<{tag}>{inner}</{tag}>"
        if kind == "link":
            href = escape(self._link(node.attrs["href"]), quote=True)
            return f'<a href="{href}" color="#175783"><u>{inner}</u></a>'
        raise ValueError(f"Unsupported inline Markdown element: {kind}")

    def _table(self, node: SyntaxTreeNode, width: float) -> Table:
        data = []
        minimums = []
        preferred = []
        for section in node.children:
            for row in section.children:
                cells = []
                for index, cell in enumerate(row.children):
                    alignment = cell.attrs.get("style", "").removeprefix("text-align:")
                    style = ParagraphStyle(
                        "Cell", parent=self.styles["table"],
                        alignment={"center": TA_CENTER, "right": TA_RIGHT}.get(alignment, TA_LEFT),
                        fontName="SorthSans-Bold" if cell.type == "th" else "SorthSans",
                    )
                    paragraph = Paragraph(self.inline(cell), style)
                    cells.append(paragraph)
                    if index == len(minimums):
                        minimums.append(0)
                        preferred.append(0)
                    minimums[index] = max(minimums[index], paragraph.minWidth() + 14)
                    preferred[index] = max(preferred[index], min(160, pdfmetrics.stringWidth(
                        _plain(cell), style.fontName, style.fontSize
                    ) + 14))
                data.append(cells)
        if sum(minimums) >= width:
            widths = [width * size / sum(minimums) for size in minimums]
        else:
            extra = width - sum(minimums)
            widths = [minimum + extra * preferred[i] / sum(preferred)
                      for i, minimum in enumerate(minimums)]
        table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT", spaceAfter=12)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE7EF")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9D9D9")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return table

    def blocks(self, nodes: list[SyntaxTreeNode], width: float = CONTENT_WIDTH) -> list:
        flowables = []
        for node in nodes:
            kind = node.type
            if kind in {"heading", "paragraph"}:
                text = self.inline(node)
                if kind == "heading":
                    anchor = escape(self.anchors[id(node)], quote=True)
                    text = f'<a name="{anchor}"/>' + text
                style = self.styles[node.tag if kind == "heading" else "body"]
                flowables.append(Paragraph(text, style))
            elif kind in {"bullet_list", "ordered_list"}:
                items = [ListItem(self.blocks(item.children, width - 18)) for item in node.children]
                ordered = kind == "ordered_list"
                flowables.append(ListFlowable(
                    items, bulletType="1" if ordered else "bullet",
                    start=int(node.attrs.get("start", 1)) if ordered else "bulletchar",
                    leftIndent=18, bulletFontName="SorthSans", bulletFontSize=9,
                    spaceAfter=5,
                ))
            elif kind == "blockquote":
                # Quotes in this manual are notes. Keep them as indented prose.
                for flowable in self.blocks(node.children, width - 12):
                    if isinstance(flowable, Paragraph):
                        flowable.style = ParagraphStyle(
                            "Quote", parent=flowable.style, leftIndent=12,
                        )
                    flowables.append(flowable)
            elif kind in {"fence", "code_block"}:
                # Preformatted expands tabs and wraps at a measured monospaced
                # width, preserving whitespace and characters instead of clipping.
                flowables.append(Preformatted(
                    node.content.expandtabs(4).rstrip("\n"), self.styles["code"],
                    maxLineLength=max(10, int(width / pdfmetrics.stringWidth("M", "SorthMono", 8.5))),
                ))
            elif kind == "table":
                flowables.append(self._table(node, width))
            elif kind == "hr":
                flowables.append(HRFlowable(
                    width="100%", thickness=0.35, color=colors.HexColor("#D9D9D9"),
                    spaceBefore=5, spaceAfter=5,
                ))
            else:
                raise ValueError(f"Unsupported block Markdown element: {kind}")
        return flowables


def _footer(canvas: Canvas, document: SimpleDocTemplate) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D9D9D9"))
    canvas.line(MARGIN + 6, 38, PAGE_WIDTH - MARGIN - 6, 38)
    canvas.setFillColor(colors.HexColor("#526170"))
    canvas.setFont("SorthSans", 8)
    canvas.drawString(MARGIN + 6, 25, "SORTH | Manual de usuario")
    canvas.drawRightString(PAGE_WIDTH - MARGIN - 6, 25, f"Página {document.page}")
    canvas.restoreState()


def build_manual(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT) -> Path:
    """Render UTF-8 Markdown atomically; leave an existing PDF intact on error."""
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError("Source and output must be different files")
    if output.suffix.lower() != ".pdf":
        raise ValueError("Output must have a .pdf extension")
    renderer = MarkdownRenderer(source.read_text(encoding="utf-8"))
    story = renderer.blocks(renderer.root.children)
    if not story:
        raise ValueError("The Markdown source is empty")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".pdf", dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        document = SimpleDocTemplate(
            str(temporary), pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=54,
            title="Manual de usuario de SORTH", author="SORTH",
            subject=f"Generado desde {source.name}", invariant=1, lang="es",
        )
        document.build(
            story, onFirstPage=_footer, onLaterPages=_footer,
        )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="UTF-8 Markdown source")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Destination PDF")
    args = parser.parse_args()
    try:
        output = build_manual(args.source, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Manual build failed: {error}\n")
    print(f"Manual generated: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
