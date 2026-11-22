"""Rendu complet d'une édition avant de l'exposer au stockage."""

import asyncio
from dataclasses import dataclass
from xml.etree.ElementTree import tostring

from app.features.book.service.content import PreparedBook, prepare_book
from app.features.book.service.epub import epub_bytes
from app.features.book.service.layout import BOOK_CSS, STYLESHEET, book_document, book_pages
from app.features.book.service.models import BookSource
from app.providers.pdf.base import HtmlDocument, HtmlPdfRenderer
from app.templates.assets import template_file


@dataclass(frozen=True)
class BookFiles:
    pdf: bytes
    epub: bytes


def _pdf_document(book: PreparedBook) -> HtmlDocument:
    pages = book_pages(book, epub=False)
    root = book_document(book.source.title, book.source.language, pages, epub=False)
    return HtmlDocument(
        index_html="<!doctype html>\n" + tostring(root, encoding="unicode", method="html"),
        assets={STYLESHEET: BOOK_CSS},
        footer_html=template_file("lesson/footer.html"),
    )


def _prepare(source: BookSource) -> tuple[HtmlDocument, bytes]:
    book = prepare_book(source)
    return _pdf_document(book), epub_bytes(book)


async def compile_book(source: BookSource, renderer: HtmlPdfRenderer) -> BookFiles:
    """Compile les deux formats à partir du même instantané, pour un travail de fond."""
    document, epub = await asyncio.to_thread(_prepare, source)
    return BookFiles(pdf=await renderer.html_to_pdf(document), epub=epub)
