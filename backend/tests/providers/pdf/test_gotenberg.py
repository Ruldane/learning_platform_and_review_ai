import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from email.message import Message
from email.parser import BytesParser
from email.policy import HTTP

import httpx
import pytest

from app.providers.pdf.base import RENDER_MAX_BYTES, RenderFailed
from app.providers.pdf.gotenberg import GotenbergRenderer

_URL = "https://ex.org/app?token=secret-123"
_PDF = b"%PDF-1.4\nrendu\n%%EOF"


class _Stream(httpx.AsyncByteStream):
    """Corps en flux, comme sur le réseau, en morceaux de 1 Mio."""

    def __init__(self, body: bytes, *, delay: float = 0.0) -> None:
        self._body = body
        self._delay = delay

    async def __aiter__(self) -> AsyncIterator[bytes]:
        if self._delay:
            await asyncio.sleep(self._delay)
        for start in range(0, len(self._body), 1024 * 1024):
            yield self._body[start : start + 1024 * 1024]


def _form(request: httpx.Request) -> dict[str, str]:
    raw = b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n"
    message: Message = BytesParser(policy=HTTP).parsebytes(raw + request.content)
    fields: dict[str, str] = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True)
        assert isinstance(name, str) and isinstance(payload, bytes)
        fields[name] = payload.decode()
    return fields


def _renderer(handler: Callable[[httpx.Request], httpx.Response]) -> GotenbergRenderer:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return GotenbergRenderer(http, "http://gotenberg:3000/")


async def test_renderer_posts_url_form() -> None:
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request.read()
        sent.append(request)
        return httpx.Response(200, stream=_Stream(_PDF))

    pdf = await _renderer(handler).url_to_pdf(_URL, timeout_s=5)
    assert pdf.startswith(b"%PDF") and pdf == _PDF
    (request,) = sent
    assert request.method == "POST"
    assert str(request.url) == "http://gotenberg:3000/forms/chromium/convert/url"
    assert request.headers["content-type"].startswith("multipart/form-data")
    form = _form(request)
    assert form["url"] == _URL
    assert form == {"url": _URL, "skipNetworkIdleEvent": "false"}


def _status(code: int) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _request: httpx.Response(code, stream=_Stream(b"Forbidden " + _URL.encode()))


def _slow(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, stream=_Stream(_PDF, delay=5))


def _too_big(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, stream=_Stream(b"%PDF-" + b"x" * RENDER_MAX_BYTES))


def _not_pdf(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, stream=_Stream(b"<html>" + _URL.encode()))


def _network_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError(f"connexion refusée pour {_URL}", request=request)


@pytest.mark.parametrize(
    "handler",
    [_status(500), _status(403), _status(409), _slow, _too_big, _not_pdf, _network_error],
    ids=["500", "403", "409", "delai", "trop-gros", "pas-un-pdf", "reseau"],
)
async def test_renderer_errors_never_cite_url(
    handler: Callable[[httpx.Request], httpx.Response], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    with pytest.raises(RenderFailed) as caught:
        await _renderer(handler).url_to_pdf(_URL, timeout_s=0.5)
    error = caught.value
    assert (error.code, error.status_code) == ("render_failed", 502)
    assert error.message == "Rendu de la page impossible."
    assert error.__cause__ is None and error.__suppress_context__
    assert "ex.org" not in caplog.text and "secret" not in caplog.text


def test_render_max_bytes() -> None:
    assert RENDER_MAX_BYTES == 20 * 1024 * 1024
