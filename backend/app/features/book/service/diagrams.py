"""Render normalised diagrams with the lessons' local resources."""

from collections.abc import Iterator, Sequence
from itertools import batched, chain
from xml.etree.ElementTree import Element, SubElement, tostring

from app.agents.nodes.mermaid_grammar import parse_flowchart
from app.agents.nodes.mermaid_tree import Chain, Subgraph
from app.features.book.service.content import PreparedBook
from app.features.lessons.service.render import CSP_WITH_SCRIPTS, LESSON_READY
from app.providers.pdf.base import (
    HtmlDocument,
    HtmlPdfRenderer,
    PageSetup,
    PdfLayoutExtractor,
    PdfUnreadable,
    RenderFailed,
)
from app.templates.assets import asset

_BATCH_SIZE = 12
_SHEET_CSS = b"""
body { margin: 0; }
.sheet { box-sizing: border-box; height: 8in; padding: .16in;
  display: grid; place-items: center; break-inside: avoid; }
.sheet + .sheet { break-before: page; }
.diagram { margin: 0; }
.diagram svg { display: block; max-width: 11in !important; max-height: 7.5in; height: auto; }
"""


def _blocks(book: PreparedBook) -> Iterator[Element]:
    for chapter in book.chapters:
        sections = chain(chapter.body, chapter.exercises, *(note.body for note in chapter.notes))
        for section in sections:
            yield from (block for block in section.iter("pre") if block.get("class") == "mermaid")


def _description(code: str) -> str:
    chart, _ = parse_flowchart(code)
    if chart is None:
        return "Chapter diagram"
    paths = [statement for statement in chart.statements if isinstance(statement, Chain)]
    labels = {s.key: s.label or s.key for s in chart.statements if isinstance(s, Subgraph)}
    labels.update(
        (node.key, node.label)
        for path in paths
        for group in path.groups
        for node in group
        if node.label is not None
    )
    descriptions = []
    for path in paths:
        groups = [" and ".join(labels.get(node.key, node.key) for node in g) for g in path.groups]
        parts = [groups[0]]
        for edge, group in zip(path.edges, groups[1:], strict=True):
            arrow = "↔" if edge.arrow.startswith("<") else "→" if edge.arrow.endswith(">") else "—"
            parts.extend([edge.label or "", arrow, group])
        descriptions.append(" ".join(part for part in parts if part))
    return ". ".join(descriptions) or "Chapter diagram"


def _document(codes: Sequence[str]) -> HtmlDocument:
    root = Element("html", {"lang": "fr"})
    head = SubElement(root, "head")
    SubElement(head, "meta", {"charset": "utf-8"})
    SubElement(head, "meta", {"http-equiv": "Content-Security-Policy", "content": CSP_WITH_SCRIPTS})
    SubElement(head, "link", {"rel": "stylesheet", "href": "diagrams.css"})
    body = SubElement(root, "body")
    for code in codes:
        sheet = SubElement(body, "section", {"class": "sheet"})
        SubElement(sheet, "pre", {"class": "mermaid"}).text = code
    SubElement(body, "script", {"src": "mermaid.min.js"})
    SubElement(body, "script", {"src": "render.js"})
    return HtmlDocument(
        index_html="<!doctype html>\n" + tostring(root, encoding="unicode", method="html"),
        assets={
            "diagrams.css": _SHEET_CSS,
            "mermaid.min.js": asset("mermaid.min.js"),
            "render.js": asset("render.js"),
        },
        wait_for_expression=LESSON_READY,
        page=PageSetup("11.7", "8.27"),
    )


async def _images(
    codes: Sequence[str], renderer: HtmlPdfRenderer, layout: PdfLayoutExtractor
) -> list[bytes | None]:
    try:
        pdf = await renderer.html_to_pdf(_document(codes))
        pages = (await layout.extract_layout(pdf, max_pages=len(codes))).pages
    except (PdfUnreadable, RenderFailed):
        return [None] * len(codes)
    if len(pages) != len(codes):
        return [None] * len(codes)
    return [
        page.image_png if not page.stream_text.lstrip().startswith("flowchart ") else None
        for page in pages
    ]


def _figure(block: Element, code: str, image: str | None) -> None:
    description = _description(code)
    tail = block.tail
    block.clear()
    block.tag, block.tail = "figure", tail
    block.set("class", "book-diagram")
    if image is None:
        SubElement(block, "figcaption").text = description
        SubElement(block, "pre", {"class": "mermaid-source"}).text = code
    else:
        SubElement(block, "img", {"src": image, "alt": description})


async def render_diagrams(
    book: PreparedBook, renderer: HtmlPdfRenderer, layout: PdfLayoutExtractor | None
) -> dict[str, bytes]:
    assets: dict[str, bytes] = {}
    for batch in batched(tuple(_blocks(book)), _BATCH_SIZE):
        codes = ["".join(block.itertext()) for block in batch]
        images = (
            await _images(codes, renderer, layout) if layout is not None else [None] * len(codes)
        )
        for block, code, image in zip(batch, codes, images, strict=True):
            filename = None
            if image:
                filename = f"diagram-{len(assets) + 1}.png"
                assets[filename] = image
            _figure(block, code, filename)
    return assets
