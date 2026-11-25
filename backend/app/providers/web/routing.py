"""Routing of the web reader (D74): GitHub repository → GitHub API, arXiv article → arXiv API,
everything else → page reader (Gotenberg fallback included). All reading fits within
`FETCH_TIMEOUT_S` (15 s per page, SPEC 10.2), whatever the path."""

import asyncio
from typing import Protocol

from app.providers.web import base
from app.providers.web.arxiv import arxiv_id
from app.providers.web.base import TIMEOUT_MESSAGE, UrlUnreadable, WebDocument, WebReader
from app.providers.web.github import github_repo


class SourceReader(Protocol):
    """Reader of a structured source (`GithubReader`, `ArxivReader`): it always returns text or
    raises."""

    async def read(self, url: str) -> WebDocument: ...


class RoutingWebReader:
    """Composed `WebReader`: memory (URL import), YouTube (fallback) and web search receive it
    unchanged."""

    def __init__(self, default: WebReader, github: SourceReader, arxiv: SourceReader) -> None:
        self._default = default
        self._github = github
        self._arxiv = arxiv

    async def read(self, url: str, *, require_text: bool = True) -> WebDocument:
        """The deadline is published in `READ_DEADLINE`: each step (rate limit, fetch, render, arXiv
        PDF)
        is set by what remains."""
        deadline = base.deadline_within(base.FETCH_TIMEOUT_S)
        token = base.READ_DEADLINE.set(deadline)
        try:
            async with asyncio.timeout_at(deadline):
                return await self._dispatch(url, require_text)
        except TimeoutError:
            raise UrlUnreadable(TIMEOUT_MESSAGE) from None
        finally:
            base.READ_DEADLINE.reset(token)

    async def _dispatch(self, url: str, require_text: bool) -> WebDocument:
        if github_repo(url) is not None:
            return await self._github.read(url)
        if arxiv_id(url) is not None:
            return await self._arxiv.read(url)
        return await self._default.read(url, require_text=require_text)
