"""Rendu de nos gabarits par Gotenberg (`convert/html`, D89), sans Gotenberg réel."""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from email.message import Message
from email.parser import BytesParser
from email.policy import HTTP

import httpx
import pytest

from app.providers.pdf.base import (
    HTML_RENDER_TIMEOUT_S,
    RENDER_MAX_BYTES,
    HtmlDocument,
    RenderFailed,
)
from app.providers.pdf.html import GotenbergHtmlRenderer

_PDF = b"%PDF-1.7\nrendu\n%%EOF"
_SECRET = "Titre-secret-de-la-lecon"
_DOC = HtmlDocument(
    index_html=f"<!doctype html><title>{_SECRET}</title><p>{_SECRET}</p>",
    assets={"lesson.css": b"body{}", "render.js": b"window.__lessonReady=true"},
    footer_html='<span class="pageNumber"></span>',
    wait_for_expression="window.__lessonReady === true",
)


class _Stream(httpx.AsyncByteStream):
    def __init__(self, body: bytes, *, delay: float = 0.0) -> None:
        self._body = body
        self._delay = delay

    async def __aiter__(self) -> AsyncIterator[bytes]:
        if self._delay:
            await asyncio.sleep(self._delay)
        for start in range(0, len(self._body), 1024 * 1024):
            yield self._body[start : start + 1024 * 1024]


def _parts(request: httpx.Request) -> list[tuple[str, str | None, bytes, str]]:
    """(champ, nom de fichier, contenu, type) de chaque partie du multipart."""
    raw = b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n"
    message: Message = BytesParser(policy=HTTP).parsebytes(raw + request.content)
    parts = []
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True)
        assert isinstance(name, str) and isinstance(payload, bytes)
        parts.append((name, part.get_filename(), payload, part.get_content_type()))
    return parts


def _renderer(handler: Callable[[httpx.Request], httpx.Response]) -> GotenbergHtmlRenderer:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return GotenbergHtmlRenderer(http, "http://gotenberg:3000/")


async def test_html_renderer_posts_a4_form() -> None:
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request.read()
        sent.append(request)
        return httpx.Response(200, stream=_Stream(_PDF))

    assert await _renderer(handler).html_to_pdf(_DOC) == _PDF
    (request,) = sent
    assert str(request.url) == "http://gotenberg:3000/forms/chromium/convert/html"
    parts = _parts(request)
    files = {filename: (body, kind) for name, filename, body, kind in parts if name == "files"}
    assert set(files) == {"index.html", "footer.html", "lesson.css", "render.js"}
    assert files["index.html"] == (_DOC.index_html.encode(), "text/html")
    assert files["lesson.css"][1] == "text/css" and files["render.js"][1] == "text/javascript"
    fields = {name: body.decode() for name, filename, body, _ in parts if filename is None}
    assert fields == {
        "paperWidth": "8.27",
        "paperHeight": "11.7",
        "marginTop": "0.6",
        "marginBottom": "0.6",
        "marginLeft": "0.6",
        "marginRight": "0.6",
        "printBackground": "true",
        "waitForExpression": "window.__lessonReady === true",
    }


async def test_html_renderer_without_footer_nor_wait() -> None:
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request.read()
        sent.append(request)
        return httpx.Response(200, stream=_Stream(_PDF))

    await _renderer(handler).html_to_pdf(HtmlDocument("<p>x</p>", {}))
    names = {(name, filename) for name, filename, _, _ in _parts(sent[0])}
    assert ("files", "index.html") in names and ("files", "footer.html") not in names
    assert "waitForExpression" not in {name for name, _ in names}


def _status(code: int) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _request: httpx.Response(code, stream=_Stream(_SECRET.encode()))


def _slow(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, stream=_Stream(_PDF, delay=5))


def _too_big(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, stream=_Stream(b"%PDF-" + b"x" * RENDER_MAX_BYTES))


def _not_pdf(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, stream=_Stream(b"<html>" + _SECRET.encode()))


def _network_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError(f"refus {_SECRET}", request=request)


@pytest.mark.parametrize(
    "handler",
    [_status(500), _status(503), _status(409), _slow, _too_big, _not_pdf, _network_error],
    ids=["500", "503", "409", "delai", "trop-gros", "pas-un-pdf", "reseau"],
)
async def test_html_renderer_errors_never_cite_body(
    handler: Callable[[httpx.Request], httpx.Response], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    with pytest.raises(RenderFailed) as caught:
        await _renderer(handler).html_to_pdf(_DOC, timeout_s=0.5)
    error = caught.value
    assert (error.code, error.status_code) == ("render_failed", 502)
    assert error.__cause__ is None and error.__suppress_context__
    assert _SECRET not in caplog.text and _SECRET not in error.message


@pytest.mark.parametrize("name", ["index.html", "footer.html", "../x.js", "a/b.css", "x.html", ""])
def test_document_refuses_unsafe_asset_names(name: str) -> None:
    with pytest.raises(ValueError):
        HtmlDocument("<p>x</p>", {name: b""})


def test_html_render_timeout() -> None:
    assert HTML_RENDER_TIMEOUT_S == 45.0
