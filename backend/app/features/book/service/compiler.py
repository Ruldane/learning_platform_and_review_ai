"""Rendu complet d'une édition avant de l'exposer au stockage."""

import asyncio
from base64 import b64encode
from collections.abc import Mapping
from dataclasses import dataclass
from xml.etree.ElementTree import SubElement, tostring

from app.features.book.service.content import PreparedBook, prepare_book
from app.features.book.service.diagrams import render_diagrams
from app.features.book.service.epub import epub_bytes
from app.features.book.service.layout import BOOK_CSS, STYLESHEET, book_document, book_pages
from app.features.book.service.models import BookSource
from app.providers.pdf.base import HtmlDocument, HtmlPdfRenderer, PdfLayoutExtractor
from app.templates.assets import template_file


@dataclass(frozen=True)
class BookFiles:
    pdf: bytes
    epub: bytes


def _pdf_document(book: PreparedBook, diagrams: Mapping[str, bytes]) -> HtmlDocument:
    pages = book_pages(book, epub=False)
    root = book_document(book.source.title, book.source.language, pages, epub=False)
    for figure in root.iter("figure"):
        image = figure.find("img")
        if image is not None and (content := diagrams.get(image.get("src", ""))):
            image.set("src", "data:image/png;base64," + b64encode(content).decode("ascii"))
            SubElement(figure, "figcaption").text = image.get("alt")
    return HtmlDocument(
        index_html="<!doctype html>\n" + tostring(root, encoding="unicode", method="html"),
        assets={STYLESHEET: BOOK_CSS},
        footer_html=template_file("lesson/footer.html"),
    )


def _serialize(book: PreparedBook, diagrams: Mapping[str, bytes]) -> tuple[HtmlDocument, bytes]:
    epub = epub_bytes(book, diagrams)
    # Le PDF remplace les références EPUB par des images embarquées dans le document HTML.
    return _pdf_document(book, diagrams), epub


async def compile_book(
    source: BookSource,
    renderer: HtmlPdfRenderer,
    *,
    diagram_layout: PdfLayoutExtractor | None = None,
) -> BookFiles:
    """Compile les deux formats à partir du même instantané, pour un travail de fond."""
    book = await asyncio.to_thread(prepare_book, source)
    diagrams = await render_diagrams(book, renderer, diagram_layout)
    document, epub = await asyncio.to_thread(_serialize, book, diagrams)
    return BookFiles(pdf=await renderer.html_to_pdf(document), epub=epub)
