"""Aiguillage du lecteur web (GitHub, arXiv, page ordinaire) et délai de 15 s pour toute la
lecture, repli Gotenberg compris."""

import asyncio

import pytest

from app.core.errors import AppError
from app.providers.web import base
from app.providers.web.base import TIMEOUT_MESSAGE, FetchedResource, UrlUnreadable, WebDocument
from app.providers.web.reader import TrafilaturaWebReader, _html
from app.providers.web.routing import RoutingWebReader
from tests.support.memory import FakeRenderer, FakeWebReader


class FakeSourceReader:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[str] = []

    async def read(self, url: str) -> WebDocument:
        self.calls.append(url)
        return WebDocument(url, self.name, "texte", None, None, None, None)


class EmptyPageFetcher:
    async def fetch(self, url: str, **options: object) -> FetchedResource:
        return FetchedResource(url, url, "text/html", b"<html><body></body></html>")


class NoPdf:
    async def extract_text(self, data: bytes) -> str:
        raise AssertionError("jamais atteint")


def _doc(url: str) -> WebDocument:
    return WebDocument(url, "défaut", "texte", None, None, None, None)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/psf/requests", "github"),
        ("https://arxiv.org/abs/1706.03762", "arxiv"),
        ("https://arxiv.org/pdf/1706.03762v7.pdf", "arxiv"),
        ("https://github.com/settings/profile", "défaut"),
        ("https://github.com/psf/requests/issues/123", "défaut"),
        ("https://export.arxiv.org/abs/1706.03762", "arxiv"),
        ("https://arxiv.org/list/cs.AI/recent", "défaut"),
        ("https://example.org/article", "défaut"),
    ],
)
async def test_routing_dispatches_github_arxiv_default(url: str, expected: str) -> None:
    default = FakeWebReader({url: _doc(url)})
    github, arxiv = FakeSourceReader("github"), FakeSourceReader("arxiv")
    doc = await RoutingWebReader(default, github, arxiv).read(url)
    assert doc.title == expected
    assert len(default.calls) + len(github.calls) + len(arxiv.calls) == 1


async def test_routing_passes_require_text_to_the_default_reader() -> None:
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    default = FakeWebReader({url: _doc(url)})
    reader = RoutingWebReader(default, FakeSourceReader("github"), FakeSourceReader("arxiv"))
    await reader.read(url, require_text=False)
    assert default.calls == [(url, False)]


async def test_routing_errors_pass_through() -> None:
    reader = RoutingWebReader(
        FakeWebReader(), FakeSourceReader("github"), FakeSourceReader("arxiv")
    )
    with pytest.raises(AppError):
        await reader.read("https://example.org/inconnue")


async def test_routing_whole_read_under_15s(monkeypatch: pytest.MonkeyPatch) -> None:
    # Premier appel de trafilatura (pool de threads, initialisation) hors du budget mesuré.
    await asyncio.to_thread(_html, b"<html><body></body></html>", "https://example.org/")
    monkeypatch.setattr(base, "FETCH_TIMEOUT_S", 0.5)
    renderer = FakeRenderer(b"%PDF-1.4", delay_s=30.0)
    default = TrafilaturaWebReader(EmptyPageFetcher(), NoPdf(), renderer=renderer)
    reader = RoutingWebReader(default, FakeSourceReader("github"), FakeSourceReader("arxiv"))
    with pytest.raises(UrlUnreadable) as caught:
        await reader.read("https://example.org/spa")
    assert caught.value.message == TIMEOUT_MESSAGE and caught.value.__cause__ is None
    [(_, timeout_s)] = renderer.calls
    assert 0 < timeout_s <= 0.5
