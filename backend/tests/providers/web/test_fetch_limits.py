"""Plafonds du lecteur : taille en flux (décompression comprise), types de contenu, délais."""

import asyncio
import gzip
import zlib

import httpx
import pytest

from app.providers.web.base import UrlTooLarge, UrlUnreadable, UrlUnsupported
from tests.providers.web.fetch_support import (
    PUBLIC_IP,
    endless,
    fetcher_for,
    html,
    never,
    ok,
)

TIMEOUT = "Délai dépassé (15 s) en lisant la page."
UNREACHABLE = "Page injoignable."


async def test_rejects_body_over_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.web.base.FETCH_MAX_BYTES", 100)
    consumed: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "text/plain"}, content=endless(b"x" * 101, consumed)
        )

    fetcher, _ = fetcher_for(handler)
    with pytest.raises(UrlTooLarge) as caught:
        await fetcher.fetch("https://example.com/")
    assert caught.value.code == "url_too_large" and caught.value.status_code == 413
    assert caught.value.message == "Page trop volumineuse : 20 Mo au maximum."
    assert len(consumed) <= 2  # arrêté en flux, sans tout télécharger


async def test_endless_body_is_stopped_while_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.web.base.FETCH_MAX_BYTES", 1000)
    consumed: list[int] = []
    fetcher, _ = fetcher_for(
        lambda r: httpx.Response(
            200, headers={"content-type": "text/html"}, content=endless(b"y" * 7, consumed)
        )
    )
    with pytest.raises(UrlTooLarge):
        await fetcher.fetch("https://example.com/")
    assert sum(consumed) <= 1000 + 7


async def test_declared_length_over_cap_is_refused_before_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.providers.web.base.FETCH_MAX_BYTES", 100)
    consumed: list[int] = []
    headers = {"content-type": "text/html", "content-length": "101"}
    fetcher, _ = fetcher_for(
        lambda r: httpx.Response(200, headers=headers, content=endless(b"z", consumed))
    )
    with pytest.raises(UrlTooLarge):
        await fetcher.fetch("https://example.com/")
    assert consumed == []


async def test_body_exactly_at_cap_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.web.base.FETCH_MAX_BYTES", 100)
    fetcher, _ = fetcher_for(lambda r: html(b"a" * 100))
    assert len((await fetcher.fetch("https://example.com/")).body) == 100


async def test_gzip_body_is_decoded_and_capped_after_decompression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher, _ = fetcher_for(
        lambda r: html(gzip.compress(b"bonjour"), **{"content-encoding": "gzip"})
    )
    assert (await fetcher.fetch("https://example.com/")).body == b"bonjour"
    monkeypatch.setattr("app.providers.web.base.FETCH_MAX_BYTES", 100)
    bomb = gzip.compress(b"\x00" * 10_000_000)
    assert len(bomb) < 100_000
    fetcher, _ = fetcher_for(lambda r: html(bomb, **{"content-encoding": "gzip"}))
    with pytest.raises(UrlTooLarge):
        await fetcher.fetch("https://example.com/")


@pytest.mark.parametrize("encoding", ["br", "zstd", "gzip, gzip", "compress"])
async def test_unknown_content_encoding_is_unsupported(encoding: str) -> None:
    fetcher, _ = fetcher_for(lambda r: html(b"x", **{"content-encoding": encoding}))
    with pytest.raises(UrlUnsupported):
        await fetcher.fetch("https://example.com/")


@pytest.mark.parametrize(
    "body",
    [
        b"pas du gzip",
        gzip.compress(b"bonjour " * 50)[:-12],  # tronqué : fin de flux et CRC absents
        gzip.compress(b"bonjour") + b"donnees en trop",
        b"",
    ],
)
async def test_corrupt_truncated_or_padded_gzip_is_unreadable(body: bytes) -> None:
    fetcher, _ = fetcher_for(lambda r: html(body, **{"content-encoding": "gzip"}))
    with pytest.raises(UrlUnreadable):
        await fetcher.fetch("https://example.com/")


async def test_deflate_with_zlib_wrapper_is_decoded() -> None:
    body = zlib.compress(b"bonjour")
    fetcher, _ = fetcher_for(lambda r: html(body, **{"content-encoding": "deflate"}))
    assert (await fetcher.fetch("https://example.com/")).body == b"bonjour"


@pytest.mark.parametrize("content_type", ["image/png", "application/octet-stream", None])
async def test_rejects_unsupported_content_type(content_type: str | None) -> None:
    headers = {"content-type": content_type} if content_type else {}
    fetcher, _ = fetcher_for(lambda r: ok(**headers))
    with pytest.raises(UrlUnsupported) as caught:
        await fetcher.fetch("https://example.com/")
    assert caught.value.code == "url_unsupported_content" and caught.value.status_code == 415


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("TEXT/HTML; charset=utf-8", "text/html"),
        ("application/pdf", "application/pdf"),
        ("text/markdown", "text/markdown"),
        ("application/xhtml+xml", "application/xhtml+xml"),
    ],
)
async def test_allowed_content_types(header: str, expected: str) -> None:
    fetcher, _ = fetcher_for(lambda r: ok(**{"content-type": header}))
    assert (await fetcher.fetch("https://example.com/")).content_type == expected


async def test_timeout_is_readable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("lent", request=request)

    fetcher, _ = fetcher_for(handler)
    with pytest.raises(UrlUnreadable) as caught:
        await fetcher.fetch("https://example.com/")
    assert (caught.value.code, caught.value.message) == ("url_unreadable", TIMEOUT)


async def test_overall_deadline_covers_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.web.base.FETCH_TIMEOUT_S", 0.05)

    async def slow(host: str, port: int) -> list[str]:
        await asyncio.sleep(5)
        return [PUBLIC_IP]

    fetcher, _ = fetcher_for(never, slow)
    with pytest.raises(UrlUnreadable) as caught:
        await fetcher.fetch("https://example.com/")
    assert caught.value.message == TIMEOUT


async def test_network_error_is_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refusé", request=request)

    fetcher, _ = fetcher_for(handler)
    with pytest.raises(UrlUnreadable) as caught:
        await fetcher.fetch("https://example.com/")
    assert caught.value.message == UNREACHABLE
