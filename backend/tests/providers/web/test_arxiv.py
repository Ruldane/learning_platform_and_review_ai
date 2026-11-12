"""Lecture d'un article arXiv : métadonnées par l'API Atom (defusedxml), texte par le PDF, résumé
en repli ; tout passe par le fetcher sûr."""

import asyncio
import time
from collections.abc import AsyncIterator

import httpx
import pytest

from app.providers.pdf.base import PdfUnreadable
from app.providers.web import base
from app.providers.web.arxiv import ArxivReader, arxiv_id
from app.providers.web.base import ARXIV_UNREADABLE, UrlForbidden, UrlUnreadable
from app.providers.web.github import GithubReader
from app.providers.web.routing import RoutingWebReader
from tests.providers.web.fetch_support import FakeResolver, Handler, fetcher_for, never, ok
from tests.support.memory import FakeWebReader

SUMMARY = "The dominant sequence transduction models are based on complex recurrent networks."
PDF_TEXT = "Attention Is All You Need. " * 20
ATOM = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title>arXiv Query: id_list=1706.03762</title>
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <published>2017-06-12T17:57:34Z</published>
    <title>Attention Is All
      You Need</title>
    <summary>
      {SUMMARY}
    </summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <link href="http://arxiv.org/pdf/1706.03762v7" rel="related" type="application/pdf"/>
  </entry>
</feed>""".encode()
EMPTY_FEED = b'<feed xmlns="http://www.w3.org/2005/Atom"><title>vide</title></feed>'
ERROR_FEED = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry>
<id>http://arxiv.org/api/errors#incorrect_id_format_for_1234.12345</id><title>Error</title>
<summary>incorrect id format for 1234.12345</summary></entry></feed>"""
BOMB = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>
<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>&lol2;</title></entry></feed>"""


class FakePdf:
    def __init__(self, result: str | Exception = PDF_TEXT) -> None:
        self.result = result
        self.calls: list[bytes] = []

    async def extract_text(self, data: bytes) -> str:
        self.calls.append(data)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _atom(body: bytes) -> httpx.Response:
    return ok(body, **{"content-type": "application/atom+xml; charset=utf-8"})


def _arxiv(atom: bytes = ATOM, pdf: httpx.Response | None = None) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "export.arxiv.org" and request.url.path == "/api/query":
            return _atom(atom)
        if request.url.host == "arxiv.org" and request.url.path.startswith("/pdf/"):
            return pdf or ok(b"%PDF-1.4 article", **{"content-type": "application/pdf"})
        return ok(b"", status=404)

    return handler


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://arxiv.org/abs/1706.03762", "1706.03762"),
        ("https://arxiv.org/pdf/1706.03762v7.pdf", "1706.03762v7"),
        ("https://arxiv.org/abs/hep-th/9901001", "hep-th/9901001"),
        ("https://arxiv.org/abs/2401.12345v2", "2401.12345v2"),
        ("https://www.arxiv.org/pdf/2401.12345", "2401.12345"),
        ("https://export.arxiv.org/abs/2401.12345", "2401.12345"),
        ("http://arxiv.org/abs/math.GT/0309136v1", "math.GT/0309136v1"),
        ("https://arxiv.org/abs/1706.03762/", "1706.03762"),
        ("https://arxiv.org/list/cs.AI/recent", None),
        ("https://arxiv.org/abs/", None),
        ("https://arxiv.org/abs/1706.03762/../../x", None),
        ("https://arxiv.org/abs/17060.3762", None),
        ("https://evil.org/abs/1706.03762", None),
        ("https://arxiv.org.evil.org/abs/1706.03762", None),
        ("https://u:p@arxiv.org/abs/1706.03762", None),
        ("pas une url", None),
    ],
)
def test_arxiv_id_forms(url: str, expected: str | None) -> None:
    assert arxiv_id(url) == expected


async def test_arxiv_reads_atom_then_pdf() -> None:
    seen: list[httpx.Request] = []
    fetcher, _ = fetcher_for(_arxiv(), seen=seen)
    pdf = FakePdf()
    url = "https://arxiv.org/abs/1706.03762v7"
    doc = await ArxivReader(fetcher, pdf).read(url)
    assert doc.url == url and doc.title == "Attention Is All You Need"
    assert doc.author == "Ashish Vaswani, Noam Shazeer" and doc.date == "2017-06-12T17:57:34Z"
    assert doc.description == SUMMARY and doc.text == PDF_TEXT.strip()
    assert pdf.calls == [b"%PDF-1.4 article"]
    query, paper = seen
    assert query.url.params["id_list"] == "1706.03762v7" and query.url.scheme == "https"
    assert (paper.url.host, paper.url.path) == ("arxiv.org", "/pdf/1706.03762v7")


async def test_arxiv_old_style_id_is_sent_as_is() -> None:
    seen: list[httpx.Request] = []
    fetcher, _ = fetcher_for(_arxiv(), seen=seen)
    await ArxivReader(fetcher, FakePdf()).read("https://arxiv.org/abs/hep-th/9901001")
    assert seen[0].url.params["id_list"] == "hep-th/9901001"
    assert seen[1].url.path == "/pdf/hep-th/9901001"


@pytest.mark.parametrize(
    ("pdf_response", "pdf_result"),
    [
        (ok(b"", status=404), PDF_TEXT),
        (ok(b"<html></html>", **{"content-type": "text/html"}), PDF_TEXT),
        (None, PdfUnreadable()),
        (None, "   "),
    ],
    ids=["404", "pas-un-pdf", "pdf-illisible", "pdf-vide"],
)
async def test_arxiv_pdf_failure_keeps_abstract(
    pdf_response: httpx.Response | None, pdf_result: str | Exception
) -> None:
    fetcher, _ = fetcher_for(_arxiv(pdf=pdf_response))
    doc = await ArxivReader(fetcher, FakePdf(pdf_result)).read("https://arxiv.org/abs/1706.03762")
    assert doc.text == SUMMARY and doc.title == "Attention Is All You Need"


@pytest.mark.parametrize(
    "atom",
    [BOMB, EMPTY_FEED, ERROR_FEED, b"<feed><entry>", b"pas du xml"],
    ids=["bombe", "vide", "erreur", "tronque", "texte"],
)
async def test_arxiv_rejects_xml_entity_bomb_and_bad_feeds(atom: bytes) -> None:
    pdf = FakePdf()
    fetcher, _ = fetcher_for(_arxiv(atom=atom))
    with pytest.raises(UrlUnreadable) as caught:
        await ArxivReader(fetcher, pdf).read("https://arxiv.org/abs/1706.03762")
    assert caught.value.message == ARXIV_UNREADABLE and caught.value.__cause__ is None
    assert pdf.calls == []


async def test_arxiv_api_failure_is_unreadable() -> None:
    fetcher, _ = fetcher_for(lambda request: ok(b"", status=503))
    with pytest.raises(UrlUnreadable) as caught:
        await ArxivReader(fetcher, FakePdf()).read("https://arxiv.org/abs/1706.03762")
    assert caught.value.message == ARXIV_UNREADABLE


async def test_arxiv_non_paper_url_is_unreadable_without_request() -> None:
    fetcher, _ = fetcher_for(never)
    with pytest.raises(UrlUnreadable) as caught:
        await ArxivReader(fetcher, FakePdf()).read("https://arxiv.org/list/cs.AI/recent")
    assert caught.value.message == ARXIV_UNREADABLE


async def test_arxiv_api_goes_through_the_ssrf_guard() -> None:
    fetcher, _ = fetcher_for(never, FakeResolver({"export.arxiv.org": ["169.254.169.254"]}))
    with pytest.raises(UrlForbidden):
        await ArxivReader(fetcher, FakePdf()).read("https://arxiv.org/abs/1706.03762")


# Revue 3.4 (I2) : un PDF lent (téléchargement ou extraction) laisse le résumé, dans les 15 s.


class SlowPdf:
    def __init__(self) -> None:
        self.cancelled = False

    async def extract_text(self, data: bytes) -> str:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return PDF_TEXT


async def _slow_body() -> AsyncIterator[bytes]:
    yield b"%PDF-1.4 "
    await asyncio.sleep(30)
    yield b"fin"


def _slow_download(request: httpx.Request) -> httpx.Response:
    if request.url.host == "arxiv.org":
        return httpx.Response(
            200, headers={"content-type": "application/pdf"}, content=_slow_body()
        )
    return _arxiv()(request)


@pytest.mark.parametrize("slow", ["extraction", "telechargement"])
async def test_arxiv_slow_pdf_keeps_abstract_within_the_page_budget(
    slow: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(base, "FETCH_TIMEOUT_S", 1.0)
    pdf = SlowPdf()
    fetcher, _ = fetcher_for(_slow_download if slow == "telechargement" else _arxiv())
    reader = RoutingWebReader(FakeWebReader(), GithubReader(fetcher), ArxivReader(fetcher, pdf))
    started = time.monotonic()
    doc = await reader.read("https://arxiv.org/abs/1706.03762")
    elapsed = time.monotonic() - started
    assert doc.text == SUMMARY and doc.title == "Attention Is All You Need"
    assert doc.author == "Ashish Vaswani, Noam Shazeer"
    assert 0.5 <= elapsed < 1.0  # échéance du PDF : 15 % avant la fin des 15 s (ici 1 s)
    assert pdf.cancelled is (slow == "extraction")


async def test_arxiv_pdf_skipped_when_no_time_is_left(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.web.arxiv._PDF_MARGIN_RATIO", 1.0)
    seen: list[httpx.Request] = []
    fetcher, _ = fetcher_for(_arxiv(), seen=seen)
    doc = await ArxivReader(fetcher, SlowPdf()).read("https://arxiv.org/abs/1706.03762")
    assert doc.text == SUMMARY and [r.url.host for r in seen] == ["export.arxiv.org"]
