"""Garde SSRF du lecteur : schéma, identifiants, adresses résolues et connectée, redirections,
cookies, messages sans URL."""

import socket

import httpx
import pytest

from app.core.errors import AppError
from app.providers.web.base import UrlForbidden, UrlUnreadable
from app.providers.web.fetch import SafeHttpFetcher, is_public_address, refuse_all_cookies
from tests.providers.web.fetch_support import (
    PUBLIC_IP,
    FakeNetworkStream,
    FakeResolver,
    fetcher_for,
    html,
    never,
    ok,
    redirect,
)

UNREACHABLE = "Page injoignable."


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/a",
        "http://user:pw@example.com/",
        "https://user@example.com/",
        "http://:pw@example.com/",
        "javascript:alert(1)",
        "gopher://example.com:70/_x",
        "http:///sans-hote",
        "pas une url",
        "",
    ],
)
async def test_rejects_bad_scheme_or_credentials(url: str) -> None:
    resolver = FakeResolver()
    fetcher, _ = fetcher_for(never, resolver)
    with pytest.raises(UrlForbidden) as caught:
        await fetcher.fetch(url)
    assert caught.value.code == "url_forbidden" and caught.value.status_code == 422
    assert resolver.calls == []


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.2",
        "169.254.169.254",
        "0.0.0.0",
        "::1",
        "fc00::1",
        "fe80::1",
        "::ffff:127.0.0.1",
        "224.0.0.1",
        "::",
        "100.64.0.1",
        "255.255.255.255",
        "240.0.0.1",
        "ff02::1",
        "ff0e::1",
        "fe80::1%eth0",
        "::127.0.0.1",
        "64:ff9b::a00:1",
        "64:ff9b:1::1",
        "2002:7f00:1::",
        "2001::1",
        "2001:db8::1",
        "fec0::1",
        "::ffff:0:7f00:1",
        "::ffff:0:808:808",
        "::8.8.8.8",
        "pas-une-ip",
    ],
)
async def test_rejects_non_public_addresses(ip: str) -> None:
    assert not is_public_address(ip)
    fetcher, _ = fetcher_for(never, FakeResolver({"example.com": [ip]}))
    with pytest.raises(UrlForbidden):
        await fetcher.fetch("http://example.com/")


@pytest.mark.parametrize(
    "ip", [PUBLIC_IP, "2606:4700::1111", "::ffff:8.8.8.8", "64:ff9b::808:808", "2002:808:808::"]
)
def test_public_addresses_are_accepted(ip: str) -> None:
    assert is_public_address(ip)


async def test_rejects_when_any_resolved_address_is_private() -> None:
    fetcher, _ = fetcher_for(never, FakeResolver({"example.com": [PUBLIC_IP, "10.0.0.1"]}))
    with pytest.raises(UrlForbidden):
        await fetcher.fetch("https://example.com/")


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1:8000/admin", "http://[::1]/", "http://[::ffff:10.0.0.1]/"]
)
async def test_ip_literal_hosts_are_judged_without_resolution(url: str) -> None:
    resolver = FakeResolver()  # dirait « publique » pour tout hôte
    fetcher, _ = fetcher_for(never, resolver)
    with pytest.raises(UrlForbidden):
        await fetcher.fetch(url)
    assert resolver.calls == []


@pytest.mark.parametrize("url", ["http://a..invalid/", f"http://{'a' * 64}.example/"])
async def test_name_refused_by_the_idna_codec_is_forbidden(url: str) -> None:
    async def idna(host: str, port: int) -> list[str]:
        return [host.encode("idna").decode()]  # lève UnicodeError, comme getaddrinfo

    fetcher, _ = fetcher_for(never, idna)
    with pytest.raises(UrlForbidden):
        await fetcher.fetch(url)


async def test_unresolvable_host_is_unreachable() -> None:
    async def failing(host: str, port: int) -> list[str]:
        raise socket.gaierror("nom inconnu")

    async def empty(host: str, port: int) -> list[str]:
        return []

    for resolver in (failing, empty):
        fetcher, _ = fetcher_for(never, resolver)
        with pytest.raises(UrlUnreadable) as caught:
            await fetcher.fetch("https://example.com/")
        assert caught.value.message == UNREACHABLE


async def test_fetches_a_public_page() -> None:
    seen: list[httpx.Request] = []
    resolver = FakeResolver()
    body = b"<html><title>Ok</title></html>"
    fetcher, _ = fetcher_for(
        lambda r: html(body, **{"content-type": "text/html; charset=utf-8"}), resolver, seen
    )
    got = await fetcher.fetch("https://example.com:8443/a?b=1")
    assert (got.url, got.final_url) == ("https://example.com:8443/a?b=1",) * 2
    assert (got.content_type, got.body) == ("text/html", body)
    assert resolver.calls == [("example.com", 8443)]
    assert seen[0].headers["accept-encoding"] == "gzip, deflate"


async def test_rechecks_redirect_target() -> None:
    seen: list[httpx.Request] = []
    resolver = FakeResolver({"interne": ["10.0.0.5"]})
    fetcher, _ = fetcher_for(lambda r: redirect("http://interne/"), resolver, seen)
    with pytest.raises(UrlForbidden):
        await fetcher.fetch("https://example.com/")
    assert [r.url.host for r in seen] == ["example.com"]
    assert resolver.calls == [("example.com", 443), ("interne", 80)]


@pytest.mark.parametrize(
    "location", ["file:///etc/passwd", "http://u:p@example.org/", "ftp://example.org/"]
)
async def test_redirect_to_a_forbidden_url_is_refused(location: str) -> None:
    fetcher, _ = fetcher_for(lambda r: redirect(location, 301))
    with pytest.raises(UrlForbidden):
        await fetcher.fetch("https://example.com/")


async def test_follows_a_relative_redirect() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return html() if request.url.path == "/b" else redirect("/b", 307)

    fetcher, _ = fetcher_for(handler)
    got = await fetcher.fetch("https://example.com/a")
    assert got.final_url == "https://example.com/b" and got.url == "https://example.com/a"


@pytest.mark.parametrize(("hops", "ok"), [(5, True), (6, False)])
async def test_stops_after_5_redirects(hops: int, ok: bool) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        step = int(request.url.path.strip("/") or 0)
        return html() if step == hops else redirect(f"/{step + 1}")

    fetcher, _ = fetcher_for(handler, seen=seen)
    if ok:
        assert (await fetcher.fetch("https://example.com/")).final_url.endswith("/5")
    else:
        with pytest.raises(UrlUnreadable):
            await fetcher.fetch("https://example.com/")
    assert len(seen) == 6


@pytest.mark.parametrize("status", [302, 404, 500, 304])
async def test_failed_or_incomplete_responses_are_unreadable(status: int) -> None:
    headers = {"content-type": "text/html"}  # 302 sans Location
    fetcher, _ = fetcher_for(lambda r: httpx.Response(status, headers=headers))
    with pytest.raises(UrlUnreadable) as caught:
        await fetcher.fetch("https://example.com/")
    assert caught.value.message == UNREACHABLE


@pytest.mark.parametrize(
    "peer", [("10.0.0.7", 80), ("::1", 80, 0, 0), ("::ffff:10.0.0.7", 80, 0, 0)]
)
async def test_checks_connected_peer_address(peer: object) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        stream = FakeNetworkStream(peer)
        response = html(b"x")
        response.extensions["network_stream"] = stream
        return response

    fetcher, _ = fetcher_for(handler)
    with pytest.raises(UrlForbidden):
        await fetcher.fetch("http://example.com/")


async def test_connected_peer_is_checked_on_redirects_too() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        stream = FakeNetworkStream(("127.0.0.1", 80))
        return httpx.Response(
            302, headers={"location": "/x"}, extensions={"network_stream": stream}
        )

    fetcher, _ = fetcher_for(handler)
    with pytest.raises(UrlForbidden):
        await fetcher.fetch("http://example.com/")


async def test_public_connected_peer_passes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        stream = FakeNetworkStream((PUBLIC_IP, 443))
        response = html(b"ok")
        response.extensions["network_stream"] = stream
        return response

    fetcher, _ = fetcher_for(handler)
    assert (await fetcher.fetch("https://example.com/")).body == b"ok"


async def test_cookies_are_never_kept_between_requests() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/b":
            return html()
        return httpx.Response(302, headers={"location": "/b", "set-cookie": "sid=secret; Path=/"})

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: seen.append(r) or handler(r)),  # type: ignore[func-returns-value]
        cookies=refuse_all_cookies(),
    )
    await SafeHttpFetcher(client, resolve=FakeResolver()).fetch("https://example.com/a")
    assert "cookie" not in seen[1].headers and not client.cookies


async def test_error_messages_never_contain_the_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.web.base.FETCH_MAX_BYTES", 10)
    marker = "secret-marqueur"

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"échec vers {request.url}", request=request)

    cases = [
        (f"ftp://{marker}.com/", never, FakeResolver()),
        (f"https://{marker}.com/", never, FakeResolver({f"{marker}.com": ["10.0.0.1"]})),
        (f"https://{marker}.com/", boom, FakeResolver()),
        (f"https://{marker}.com/", lambda r: html(b"x" * 11), FakeResolver()),
        (f"https://{marker}.com/", lambda r: ok(), FakeResolver()),
        (
            f"https://{marker}.com/",
            lambda r: redirect(f"http://{marker}.org/"),
            FakeResolver({f"{marker}.org": ["::1"]}),
        ),
    ]
    for url, handler, resolver in cases:
        fetcher, _ = fetcher_for(handler, resolver)
        with pytest.raises(AppError) as caught:
            await fetcher.fetch(url)
        error = caught.value
        assert marker not in f"{error} {error!r} {error.message} {error.details}"
        assert error.__cause__ is None
        assert error.__suppress_context__ or error.__context__ is None
