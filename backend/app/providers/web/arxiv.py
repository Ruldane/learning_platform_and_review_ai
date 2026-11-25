"""Reading of an arXiv paper (SPEC 10.2): metadata through the API
(`https://export.arxiv.org/api/query?id_list=<id>`, Atom feed parsed by `defusedxml`, without
DTD or entity), then the PDF text (`https://arxiv.org/pdf/<id>`); the abstract serves as text if the
PDF is missing. Both calls go through the safe `WebFetcher` (SSRF guard, rate: 3 s between two
calls to the API, arXiv's guideline, D74).

Only the identifier, validated by regular expression, enters the URLs called."""

import asyncio
import logging
import re
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

from app.core.errors import AppError
from app.providers.pdf import base as pdf_limits
from app.providers.pdf.base import PdfTextExtractor
from app.providers.web import base
from app.providers.web.base import (
    ARXIV_UNREADABLE,
    TIMEOUT_MESSAGE,
    UrlForbidden,
    UrlUnreadable,
    WebDocument,
    WebFetcher,
)

logger = logging.getLogger(__name__)

API_URL = "https://export.arxiv.org/api/query"
PDF_ROOT = "https://arxiv.org/pdf"
_HOSTS = frozenset({"arxiv.org", "www.arxiv.org", "export.arxiv.org"})
# Share of the 15 s of the read kept after the PDF step: a PDF that is too slow leaves time to
# return the abstract (review 3.4).
_PDF_MARGIN_RATIO = 0.15
_ATOM_TYPES = ("application/atom+xml", "application/xml", "text/xml")
_NS = "{http://www.w3.org/2005/Atom}"
# Recent identifiers (`1706.03762`, `2401.12345v2`) and old ones (`hep-th/9901001`,
# `math.GT/0309136v1`), version kept.
_ID = r"\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?"
_PATH = re.compile(rf"/(?:abs|pdf)/(?P<id>{_ID})(?:\.pdf)?/?")


def arxiv_id(url: str) -> str | None:
    """Identifier of a URL `arxiv.org/abs/<id>` or `arxiv.org/pdf/<id>[.pdf]`, otherwise `None`."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or host not in _HOSTS:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    match = _PATH.fullmatch(parts.path)
    return match.group("id") if match else None


def _clean(element: Element | None) -> str | None:
    """Text of an element, blanks (including the feed's line breaks) reduced to one space."""
    text = " ".join((element.text or "").split()) if element is not None else ""
    return text or None


def _entry(body: bytes) -> Element:
    """Blocking (expat): called in a thread. First entry of the feed; an empty feed, an
    error entry from the API or a refused XML -> `ARXIV_UNREADABLE`."""
    try:
        root = fromstring(body, forbid_dtd=True)
    except (ParseError, DefusedXmlException, ValueError):
        raise UrlUnreadable(ARXIV_UNREADABLE) from None
    entry = root.find(f"{_NS}entry")
    if entry is None:
        raise UrlUnreadable(ARXIV_UNREADABLE)
    entry_id = _clean(entry.find(f"{_NS}id")) or ""
    if "/api/errors" in entry_id or _clean(entry.find(f"{_NS}title")) is None:
        raise UrlUnreadable(ARXIV_UNREADABLE)
    return entry


class ArxivReader:
    def __init__(self, fetcher: WebFetcher, pdf: PdfTextExtractor) -> None:
        self._fetcher = fetcher
        self._pdf = pdf

    async def read(self, url: str) -> WebDocument:
        """Title, joined authors, publication date, abstract and PDF text. API failure or
        missing paper -> `UrlUnreadable(ARXIV_UNREADABLE)`; a refused address and the exceeded
        timeout pass through as they are; a failed or too slow PDF leaves the abstract as the text.
        The PDF step stops `_PDF_MARGIN_RATIO` x 15 s before the read's deadline."""
        paper = arxiv_id(url)
        if paper is None:
            raise UrlUnreadable(ARXIV_UNREADABLE)
        deadline = base.deadline_within(base.FETCH_TIMEOUT_S)
        entry = await asyncio.to_thread(_entry, await self._feed(paper))
        summary = _clean(entry.find(f"{_NS}summary"))
        names = [_clean(author.find(f"{_NS}name")) for author in entry.findall(f"{_NS}author")]
        pdf_deadline = deadline - base.FETCH_TIMEOUT_S * _PDF_MARGIN_RATIO
        text = await self._pdf_text(paper, pdf_deadline) or summary
        if not text:
            raise UrlUnreadable(ARXIV_UNREADABLE)
        return WebDocument(
            url=url,
            title=_clean(entry.find(f"{_NS}title")),
            text=text[: pdf_limits.MAX_TEXT_CHARS],
            author=", ".join(name for name in names if name) or None,
            date=_clean(entry.find(f"{_NS}published")),
            lang=None,
            description=summary,
        )

    async def _feed(self, paper: str) -> bytes:
        try:
            resource = await self._fetcher.fetch(
                f"{API_URL}?id_list={paper}", content_types=_ATOM_TYPES
            )
        except UrlForbidden:
            raise
        except UrlUnreadable as exc:
            if exc.message == TIMEOUT_MESSAGE:
                raise
            raise UrlUnreadable(ARXIV_UNREADABLE) from None
        except AppError:
            raise UrlUnreadable(ARXIV_UNREADABLE) from None
        return resource.body

    async def _pdf_text(self, paper: str, deadline: float) -> str:
        """PDF text before `deadline`, or `""` on failure or timeout (log: error code
        only). The deadline is published to the fetcher (rate and download); the
        extraction subprocess is killed on cancellation (D72)."""
        if deadline <= asyncio.get_running_loop().time():
            logger.info("arXiv PDF not read, abstract kept (timeout)")
            return ""
        token = base.READ_DEADLINE.set(deadline)
        try:
            async with asyncio.timeout_at(deadline):
                resource = await self._fetcher.fetch(
                    f"{PDF_ROOT}/{paper}", content_types=("application/pdf",)
                )
                text = await self._pdf.extract_text(resource.body)
        except TimeoutError:
            logger.info("arXiv PDF too slow, abstract kept")
            return ""
        except AppError as exc:
            logger.info("arXiv PDF unreadable, abstract kept (%s)", exc.code)
            return ""
        finally:
            base.READ_DEADLINE.reset(token)
        return text.strip()
