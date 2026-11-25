"""Reading of a web page: main text and metadata (`trafilatura`, without network: the page
is downloaded by the safe `WebFetcher`, never by trafilatura).

Fallback for pages rendered in JavaScript (D74): an HTML page **downloaded successfully** whose
main text is too short is rendered to PDF by the `PageRenderer` (Gotenberg), which only
receives the final URL, already validated by the SSRF guard (never HTML, never a refused URL,
never after an error status or a refused type: the fetch then raised). The rendering timeout
is what remains of the read's 15 s."""

import asyncio
import dataclasses
import logging

import trafilatura

from app.core.errors import AppError
from app.providers.pdf import base as pdf_limits
from app.providers.pdf.base import PageRenderer, PdfTextExtractor
from app.providers.web import base
from app.providers.web.base import (
    NO_TEXT_MESSAGE,
    TIMEOUT_MESSAGE,
    FetchedResource,
    UrlUnreadable,
    WebDocument,
    WebFetcher,
)

logger = logging.getLogger(__name__)

MIN_TEXT_CHARS = 200
_PLAIN = ("text/plain", "text/markdown")


def _html(body: bytes, url: str) -> WebDocument:
    """Blocking (lxml): called in a thread. Two parses: `extract` prunes the tree. The URL
    is never passed to trafilatura, which would copy it into its logs."""
    tree = trafilatura.load_html(body)
    if tree is None:
        return WebDocument(url, None, "", None, None, None, None)
    metadata = trafilatura.extract_metadata(tree)
    text = trafilatura.extract(
        trafilatura.load_html(body), include_comments=False, include_tables=True
    )
    return WebDocument(
        url=url,
        title=metadata.title,
        text=text or "",
        author=metadata.author,
        date=metadata.date,
        lang=metadata.language,
        description=metadata.description,
    )


def _too_short(text: str) -> bool:
    return len(text.strip()) < MIN_TEXT_CHARS


class TrafilaturaWebReader:
    def __init__(
        self,
        fetcher: WebFetcher,
        pdf: PdfTextExtractor,
        *,
        renderer: PageRenderer | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._pdf = pdf
        self._renderer = renderer

    async def read(self, url: str, *, require_text: bool = True) -> WebDocument:
        """Without required text (`require_text=False`, YouTube fallback), no rendering: only the
        title and the description are expected."""
        deadline = base.deadline_within(base.FETCH_TIMEOUT_S)
        resource = await self._fetcher.fetch(url)
        if resource.content_type == "application/pdf":
            text = await self._pdf.extract_text(resource.body)
            doc = WebDocument(url, None, text, None, None, None, None)
        elif resource.content_type in _PLAIN:
            text = resource.body.decode("utf-8", errors="replace")
            doc = WebDocument(url, None, text, None, None, None, None)
        else:
            doc = await asyncio.to_thread(_html, resource.body, resource.final_url)
            if require_text and self._renderer is not None and _too_short(doc.text):
                doc = await self._rendered(doc, resource, self._renderer, deadline)
        text = doc.text.strip()[: pdf_limits.MAX_TEXT_CHARS]
        if require_text and len(text) < MIN_TEXT_CHARS:
            raise UrlUnreadable(NO_TEXT_MESSAGE)
        return WebDocument(url, doc.title, text, doc.author, doc.date, doc.lang, doc.description)

    async def _rendered(
        self,
        doc: WebDocument,
        resource: FetchedResource,
        renderer: PageRenderer,
        deadline: float,
    ) -> WebDocument:
        """`doc` with the rendered text; rendering or extraction failed -> unreadable page
        (log: error code only, never the URL)."""
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise UrlUnreadable(TIMEOUT_MESSAGE)
        try:
            pdf = await renderer.url_to_pdf(resource.final_url, timeout_s=remaining)
            text = await self._pdf.extract_text(pdf)
        except AppError as exc:
            logger.info("Rendering fallback without text (%s)", exc.code)
            raise UrlUnreadable(NO_TEXT_MESSAGE) from None
        return dataclasses.replace(doc, text=text)
