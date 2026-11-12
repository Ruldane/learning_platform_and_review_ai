"""Options par appel du fetcher (D74) : types de contenu acceptés et en-têtes ajoutés, sans
jamais toucher à la garde SSRF ni à l'encodage accepté (plafond de décompression)."""

import httpx
import pytest

from app.providers.web.base import UrlUnsupported
from tests.providers.web.fetch_support import fetcher_for, ok


def _json(request: httpx.Request) -> httpx.Response:
    return ok(b'{"a": 1}', **{"content-type": "application/json; charset=utf-8"})


async def test_default_content_types_refuse_json() -> None:
    fetcher, _ = fetcher_for(_json)
    with pytest.raises(UrlUnsupported):
        await fetcher.fetch("https://api.example/x")


async def test_content_types_per_call() -> None:
    fetcher, _ = fetcher_for(_json)
    resource = await fetcher.fetch("https://api.example/x", content_types=("application/json",))
    assert resource.content_type == "application/json" and resource.body == b'{"a": 1}'


async def test_per_call_content_types_replace_the_defaults() -> None:
    def page(request: httpx.Request) -> httpx.Response:
        return ok(b"<html></html>", **{"content-type": "text/html"})

    fetcher, _ = fetcher_for(page)
    with pytest.raises(UrlUnsupported):
        await fetcher.fetch("https://api.example/x", content_types=("application/json",))


async def test_headers_per_call_are_added_but_never_the_encoding() -> None:
    seen: list[httpx.Request] = []
    fetcher, _ = fetcher_for(_json, seen=seen)
    await fetcher.fetch(
        "https://api.example/x",
        content_types=("application/json",),
        headers={"Accept": "application/vnd.github+json", "Accept-Encoding": "br, zstd"},
    )
    sent = seen[-1].headers
    assert sent["accept"] == "application/vnd.github+json"
    assert sent["accept-encoding"] == "gzip, deflate"
    assert "TremplinReader" in sent["user-agent"]


async def test_default_headers_are_unchanged_without_options() -> None:
    seen: list[httpx.Request] = []
    fetcher, _ = fetcher_for(lambda r: ok(b"x", **{"content-type": "text/plain"}), seen=seen)
    await fetcher.fetch("https://ex.org/a")
    assert seen[-1].headers["accept"].startswith("text/html")
