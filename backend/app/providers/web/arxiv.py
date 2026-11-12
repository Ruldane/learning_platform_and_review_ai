"""Lecture d'un article arXiv (SPEC 10.2) : métadonnées par l'API
(`https://export.arxiv.org/api/query?id_list=<id>`, flux Atom analysé par `defusedxml`, sans
DTD ni entité), puis texte du PDF (`https://arxiv.org/pdf/<id>`) ; le résumé sert de texte si le
PDF manque. Les deux appels passent par le `WebFetcher` sûr (garde SSRF, débit : 3 s entre deux
appels à l'API, consigne d'arXiv, D74).

Seul l'identifiant, validé par expression régulière, entre dans les URL appelées."""

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
# Part des 15 s de la lecture gardée après l'étape du PDF : un PDF trop lent laisse le temps de
# rendre le résumé (revue 3.4).
_PDF_MARGIN_RATIO = 0.15
_ATOM_TYPES = ("application/atom+xml", "application/xml", "text/xml")
_NS = "{http://www.w3.org/2005/Atom}"
# Identifiants récents (`1706.03762`, `2401.12345v2`) et anciens (`hep-th/9901001`,
# `math.GT/0309136v1`), version gardée.
_ID = r"\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?"
_PATH = re.compile(rf"/(?:abs|pdf)/(?P<id>{_ID})(?:\.pdf)?/?")


def arxiv_id(url: str) -> str | None:
    """Identifiant d'une URL `arxiv.org/abs/<id>` ou `arxiv.org/pdf/<id>[.pdf]`, sinon `None`."""
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
    """Texte d'un élément, blancs (dont les retours à la ligne du flux) réduits à une espace."""
    text = " ".join((element.text or "").split()) if element is not None else ""
    return text or None


def _entry(body: bytes) -> Element:
    """Bloquant (expat) : appelé dans un thread. Première entrée du flux ; un flux vide, une
    entrée d'erreur de l'API ou un XML refusé → `ARXIV_UNREADABLE`."""
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
        """Titre, auteurs joints, date de publication, résumé et texte du PDF. API en échec ou
        article absent → `UrlUnreadable(ARXIV_UNREADABLE)` ; une adresse refusée et le délai
        dépassé passent tels quels ; un PDF en échec ou trop lent laisse le résumé comme texte.
        L'étape du PDF s'arrête `_PDF_MARGIN_RATIO` × 15 s avant l'échéance de la lecture."""
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
        """Texte du PDF avant `deadline`, ou `""` en cas d'échec ou de délai (journal : code
        d'erreur seulement). L'échéance est publiée au fetcher (débit et téléchargement) ; le
        sous-processus d'extraction est tué à l'annulation (D72)."""
        if deadline <= asyncio.get_running_loop().time():
            logger.info("PDF arXiv non lu, résumé gardé (délai)")
            return ""
        token = base.READ_DEADLINE.set(deadline)
        try:
            async with asyncio.timeout_at(deadline):
                resource = await self._fetcher.fetch(
                    f"{PDF_ROOT}/{paper}", content_types=("application/pdf",)
                )
                text = await self._pdf.extract_text(resource.body)
        except TimeoutError:
            logger.info("PDF arXiv trop lent, résumé gardé")
            return ""
        except AppError as exc:
            logger.info("PDF arXiv illisible, résumé gardé (%s)", exc.code)
            return ""
        finally:
            base.READ_DEADLINE.reset(token)
        return text.strip()
