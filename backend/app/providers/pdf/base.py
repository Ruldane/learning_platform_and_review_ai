"""PDF ports: text extraction (imported file or URL read), rendering of a web page to PDF
(fallback for pages rendered in JavaScript), rendering of our HTML templates (lessons, program; D89)
and layout of a CV (positions, fonts, colours, page images; D119)."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from app.core.errors import AppError

MAX_PDF_PAGES = 500
MAX_TEXT_CHARS = 2_000_000

# Extraction in a subprocess (D72): real timeout, bounded memory (POSIX), two at most at a time.
PDF_TIMEOUT_S = 60.0
PDF_MAX_MEMORY_BYTES = 1024 * 1024 * 1024
PDF_TIMEOUT_MESSAGE = "The PDF took too long to read: timeout exceeded."
_UNREADABLE_MESSAGE = "The PDF is unreadable (password-protected or damaged)."

# Rendering of a page by Gotenberg: PDF of 20 MB at most, like a PDF read online.
RENDER_MAX_BYTES = 20 * 1024 * 1024


class PdfUnreadable(AppError):
    """PDF that is encrypted, damaged, too long to read or not a PDF. The message is always
    a constant of this module: never the file or its content."""

    def __init__(self, message: str = _UNREADABLE_MESSAGE) -> None:
        super().__init__("pdf_unreadable", message, status_code=422)


class PdfTextExtractor(Protocol):
    async def extract_text(self, data: bytes) -> str:
        """Text of the first `MAX_PDF_PAGES` pages, truncated to `MAX_TEXT_CHARS` characters."""
        ...


class RenderFailed(AppError):
    """Rendering impossible (service down, timeout, page refused, body too big). Never quotes
    the URL or the service's reply."""

    def __init__(self) -> None:
        super().__init__("render_failed", "The page could not be rendered.", status_code=502)


class PageRenderer(Protocol):
    async def url_to_pdf(self, url: str, *, timeout_s: float) -> bytes:
        """PDF of the page at `url` (already validated by the SSRF guard), within `timeout_s`."""
        ...


# Rendering of an HTML template (lesson with Mermaid diagrams, program, CV): 45 s at most (D89).
HTML_RENDER_TIMEOUT_S = 45.0
_RESERVED = {"index.html", "footer.html", "header.html"}
# Our frozen files (CSS, JS) and the attached fonts ("slugified" names: `lato-400.ttf`).
_ASSET_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}\.(css|js|woff2|ttf)")
# A measure in inches (Gotenberg's unit): "8.27", "0", "0.6".
_INCHES = re.compile(r"\d{1,2}(\.\d{1,4})?")
_MAX_SIDE_IN = 20.0


@dataclass(frozen=True)
class PageSetup:
    """Page size and margins (top, right, bottom, left) in inches, as Gotenberg
    reads them; a CV template follows the original PDF's page, with zero margins (the layout
    is in the CSS)."""

    width_in: str
    height_in: str
    margins_in: tuple[str, str, str, str] = ("0", "0", "0", "0")

    def __post_init__(self) -> None:
        for value in (self.width_in, self.height_in, *self.margins_in):
            if not _INCHES.fullmatch(value):
                raise ValueError("page measure refused")
        # Side in ]0; 20] inches (`MAX_PAGE_SIDE_PT`), margin under half of its side.
        width, height = float(self.width_in), float(self.height_in)
        top, right, bottom, left = (float(value) for value in self.margins_in)
        if not (0 < width <= _MAX_SIDE_IN and 0 < height <= _MAX_SIDE_IN):
            raise ValueError("page measure refused")
        if max(top, bottom) * 2 >= height or max(left, right) * 2 >= width:
            raise ValueError("page measure refused")


@dataclass(frozen=True)
class HtmlDocument:
    """Page to render: `index.html`, resources attached next to it (plain names, CSS, JS or font:
    our frozen files and the free fonts), footer (`pageNumber`, `totalPages`),
    expression awaited before printing (`waitForExpression`) and page (`None`: A4, margins of
    0.6 inch, like the lessons)."""

    index_html: str
    assets: Mapping[str, bytes]
    footer_html: str | None = None
    wait_for_expression: str | None = None
    page: PageSetup | None = None

    def __post_init__(self) -> None:
        for name in self.assets:
            if name in _RESERVED or not _ASSET_NAME.fullmatch(name):
                raise ValueError("resource name refused")


class HtmlPdfRenderer(Protocol):
    async def html_to_pdf(
        self, document: HtmlDocument, *, timeout_s: float = HTML_RENDER_TIMEOUT_S
    ) -> bytes:
        """PDF of `document` (A4 or `document.page`), in `timeout_s` at most; `RenderFailed`
        otherwise."""
        ...


# Layout of a CV (D119): same bounded subprocess as the text extraction (D72).
MAX_CV_PAGES = 4
# LinkedIn profile exported as PDF: often longer than a CV; safety bound only.
MAX_LINKEDIN_PAGES = 40
LAYOUT_DPI = 72
LAYOUT_TIMEOUT_S = 60.0
# Worker output (JSON, base64 PNG images): 40 MB at most.
LAYOUT_MAX_OUTPUT_BYTES = 40 * 1024 * 1024
# A page larger than 20 inches on a side is not a CV page (and its image would be huge).
MAX_PAGE_SIDE_PT = 1440
CV_TOO_LONG_MESSAGE = "A CV of more than 4 pages is not supported."
ROTATED_PAGE_MESSAGE = (
    "A page of this PDF is rotated: export it again without rotation, then try again."
)


@dataclass(frozen=True)
class TextBlock:
    """A line of words with the same font, size and colour. Coordinates in points from the top
    left corner of the page; `color` in `#rrggbb`; `invisible`: colour close to the background
    read on the page image, size under 2 pt, or outside the page."""

    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    font: str
    size: float
    color: str
    bold: bool
    invisible: bool


@dataclass(frozen=True)
class PageLayout:
    """Page in points; blocks in the order of the content stream; PNG image of the page at
    `LAYOUT_DPI`; text in stream order (what a parser reads, invisible text included)."""

    width_pt: float
    height_pt: float
    blocks: list[TextBlock]
    image_png: bytes
    stream_text: str


@dataclass(frozen=True)
class PdfLayout:
    """`fonts`: fonts of the visible text, without subset prefix ("ABCDEF+"), from the
    most used to the least used; `selectable`: at least 20 visible characters on the
    first page (a scanned CV is not)."""

    pages: list[PageLayout]
    fonts: list[str]
    selectable: bool


class PdfLayoutExtractor(Protocol):
    async def extract_layout(self, data: bytes, *, max_pages: int = MAX_CV_PAGES) -> PdfLayout:
        """Layout of the `MAX_CV_PAGES` pages at most. `PdfUnreadable`: protected or damaged PDF,
        too long to read, oversized page or more than `MAX_CV_PAGES` pages
        (`CV_TOO_LONG_MESSAGE`). A scanned PDF returns pages without blocks, not an error."""
        ...
