"""Rendu PDF de test lisible (preflight G14) : le texte visible d'un `HtmlDocument` (balises
retirées, ordre du DOM, une ligne par bloc) écrit par `sample_pdf.make_pdf` à la taille de
`document.page`. Le PDF se relit avec l'extracteur réel (texte sélectionnable, 12 pt) ; le nombre
de pages est réglable appel par appel (resserrement d'un CV trop long, 6.14)."""

import math
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser

from app.providers.pdf.base import HTML_RENDER_TIMEOUT_S, HtmlDocument, RenderFailed
from scripts.sample_pdf import LEADING_PT, make_pdf

_POINTS_PER_INCH = 72
_A4 = (595, 842)
_HIDDEN = {"head", "title", "style", "script", "template"}
_BLOCKS = {
    "address", "article", "aside", "br", "dd", "div", "dl", "dt", "footer", "h1", "h2", "h3",
    "h4", "h5", "h6", "header", "li", "main", "ol", "p", "section", "table", "tr", "ul",
}  # fmt: skip
_WRAP = 80  # caractères par ligne (Helvetica 12 pt sur une page de CV)
_FREE_PT = 72 + 36  # haut (première ligne de base) et bas laissés libres


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self._current: list[str] = []
        self._hidden = 0

    def _flush(self) -> None:
        text = " ".join("".join(self._current).split())
        if text:
            self.lines.append(text)
        self._current = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _HIDDEN:
            self._hidden += 1
        elif tag in _BLOCKS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in _HIDDEN:
            self._hidden = max(0, self._hidden - 1)
        elif tag in _BLOCKS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self._hidden:
            self._current.append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def visible_lines(html: str) -> list[str]:
    """Texte visible de `html`, une ligne par bloc, coupé à `_WRAP` caractères."""
    parser = _VisibleText()
    parser.feed(html)
    parser.close()
    return [part for line in parser.lines for part in textwrap.wrap(line, _WRAP)]


def _size(document: HtmlDocument) -> tuple[int, int]:
    if document.page is None:
        return _A4
    width = round(float(document.page.width_in) * _POINTS_PER_INCH)
    return width, round(float(document.page.height_in) * _POINTS_PER_INCH)


@dataclass
class TextHtmlRenderer:
    """`HtmlPdfRenderer` de test. Le i-ème appel rend `pages[i]` pages (la dernière valeur
    ensuite), davantage si le texte n'y tient pas ; les `failures` premiers appels lèvent
    `RenderFailed` ; chaque document reçu est gardé."""

    pages: Sequence[int] = (1,)
    failures: int = 0
    documents: list[HtmlDocument] = field(default_factory=list)

    async def html_to_pdf(
        self, document: HtmlDocument, *, timeout_s: float = HTML_RENDER_TIMEOUT_S
    ) -> bytes:
        self.documents.append(document)
        if self.failures:
            self.failures -= 1
            raise RenderFailed()
        size = _size(document)
        lines = visible_lines(document.index_html)
        per_page = max(1, (size[1] - _FREE_PT) // LEADING_PT)
        wanted = self.pages[min(len(self.documents), len(self.pages)) - 1]
        pages = max(wanted, math.ceil(len(lines) / per_page))
        return make_pdf(lines, size=size, pages=pages)
