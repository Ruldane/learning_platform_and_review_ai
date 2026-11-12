"""Aiguillage du lecteur web (D74) : dépôt GitHub → API GitHub, article arXiv → API arXiv, tout le
reste → lecteur de pages (repli Gotenberg compris). Toute la lecture tient dans
`FETCH_TIMEOUT_S` (15 s par page, SPEC 10.2), quel que soit le chemin."""

import asyncio
from typing import Protocol

from app.providers.web import base
from app.providers.web.arxiv import arxiv_id
from app.providers.web.base import TIMEOUT_MESSAGE, UrlUnreadable, WebDocument, WebReader
from app.providers.web.github import github_repo


class SourceReader(Protocol):
    """Lecteur d'une source structurée (`GithubReader`, `ArxivReader`) : il rend toujours un
    texte ou lève."""

    async def read(self, url: str) -> WebDocument: ...


class RoutingWebReader:
    """`WebReader` composé : la mémoire (import d'URL), YouTube (repli) et la recherche web le
    reçoivent sans changement."""

    def __init__(self, default: WebReader, github: SourceReader, arxiv: SourceReader) -> None:
        self._default = default
        self._github = github
        self._arxiv = arxiv

    async def read(self, url: str, *, require_text: bool = True) -> WebDocument:
        try:
            async with asyncio.timeout(base.FETCH_TIMEOUT_S):
                return await self._dispatch(url, require_text)
        except TimeoutError:
            raise UrlUnreadable(TIMEOUT_MESSAGE) from None

    async def _dispatch(self, url: str, require_text: bool) -> WebDocument:
        if github_repo(url) is not None:
            return await self._github.read(url)
        if arxiv_id(url) is not None:
            return await self._arxiv.read(url)
        return await self._default.read(url, require_text=require_text)
