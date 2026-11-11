"""Lecture d'une page web : texte principal et métadonnées (`trafilatura`, sans réseau : la page
est téléchargée par le `WebFetcher` sûr, jamais par trafilatura)."""

import asyncio

import trafilatura

from app.providers.pdf import base as pdf_limits
from app.providers.pdf.base import PdfTextExtractor
from app.providers.web.base import NO_TEXT_MESSAGE, UrlUnreadable, WebDocument, WebFetcher

MIN_TEXT_CHARS = 200
_PLAIN = ("text/plain", "text/markdown")


def _html(body: bytes, url: str) -> WebDocument:
    """Bloquant (lxml) : appelé dans un thread. Deux analyses : `extract` élague l'arbre. L'URL
    n'est jamais passée à trafilatura, qui la recopierait dans ses journaux."""
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


class TrafilaturaWebReader:
    def __init__(self, fetcher: WebFetcher, pdf: PdfTextExtractor) -> None:
        self._fetcher = fetcher
        self._pdf = pdf

    async def read(self, url: str, *, require_text: bool = True) -> WebDocument:
        resource = await self._fetcher.fetch(url)
        if resource.content_type == "application/pdf":
            text = await self._pdf.extract_text(resource.body)
            doc = WebDocument(url, None, text, None, None, None, None)
        elif resource.content_type in _PLAIN:
            text = resource.body.decode("utf-8", errors="replace")
            doc = WebDocument(url, None, text, None, None, None, None)
        else:
            doc = await asyncio.to_thread(_html, resource.body, resource.final_url)
        text = doc.text.strip()[: pdf_limits.MAX_TEXT_CHARS]
        if require_text and len(text) < MIN_TEXT_CHARS:
            raise UrlUnreadable(NO_TEXT_MESSAGE)
        return WebDocument(url, doc.title, text, doc.author, doc.date, doc.lang, doc.description)
