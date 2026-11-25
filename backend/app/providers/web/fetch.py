"""Safe download of a URL supplied by the user (SSRF guard, spec 17.4).

Algorithm, under a single `FETCH_TIMEOUT_S` timeout for the whole (redirects included):
1. http/https scheme, host present, no credentials (`user:pass@`), otherwise `UrlForbidden`;
2. all the resolved addresses of the host public, otherwise `UrlForbidden`;
3. streamed request without automatic following; a 3xx goes back to 1 with `Location` resolved
   (5 redirects at most); with `GuardedTransport` (`transport.py`, wired by
   `bootstrap`), the connection itself resolves, checks again and is made on the validated address:
   a DNS that changes between 2 and the connection (rebinding) receives no request;
4. defence in depth: the address actually connected
   (`network_stream.get_extra_info("server_addr")`, httpcore) is public;
5. `Content-Type` on a whitelist, size capped in the stream (declared then read, decompression
   included).
Errors are raised `from None`: the exception chain would quote the URL in a log."""

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable, Mapping
from http.cookiejar import CookieJar, DefaultCookiePolicy

import httpcore
import httpx

from app.providers.web import base
from app.providers.web._body import ACCEPT_ENCODING, declared_too_large, read_capped
from app.providers.web.base import (
    ALLOWED_CONTENT_TYPES,
    MAX_REDIRECTS,
    TIMEOUT_MESSAGE,
    TOO_MANY_REDIRECTS_MESSAGE,
    FetchedResource,
    UrlForbidden,
    UrlTooLarge,
    UrlUnreadable,
    UrlUnsupported,
)
from app.providers.web.throttle import DomainThrottle

Resolver = Callable[[str, int], Awaitable[list[str]]]

_REDIRECTS = frozenset({301, 302, 303, 307, 308})
_HEADERS = {
    "accept": "text/html,application/xhtml+xml,text/plain;q=0.9,text/markdown;q=0.9,"
    "application/pdf;q=0.8",
    "accept-encoding": ACCEPT_ENCODING,
    "user-agent": "Mozilla/5.0 (compatible; TremplinReader/1.0)",
}
# Headers that a call never replaces: the encoding bounds decompression (`_body`), the host
# is that of the validated URL, no cookie is sent (shared client, D63), no body.
_LOCKED_HEADERS = frozenset({"accept-encoding", "host", "cookie", "content-length"})
_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_IPV6_GLOBAL_UNICAST = ipaddress.ip_network("2000::/3")


class AddressRefused(httpcore.ConnectError):
    """Raised by `GuardedBackend` (non-public address at connection); `SafeHttpFetcher` turns
    it into `UrlForbidden`. Fixed message, without the host."""

    def __init__(self) -> None:
        super().__init__("address refused")


async def system_resolve(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def is_public_address(ip: str) -> bool:
    """Publicly reachable address (`is_global`, not multicast). An IPv6 that carries an IPv4
    (mapped, NAT64 `64:ff9b::/96`, 6to4) is judged on that IPv4; any other IPv6 must be
    global unicast (`2000::/3`): site-local, translated `::ffff:0:0/96`, compatible `::/96`,
    local NAT64 and Teredo are refused."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        if address.teredo is not None:
            return False
        embedded = address.ipv4_mapped or address.sixtofour
        if embedded is None and address in _NAT64:
            embedded = ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
        if embedded is not None:
            return is_public_address(str(embedded))
        if address not in _IPV6_GLOBAL_UNICAST:
            return False
    return address.is_global and not address.is_multicast


class _RefuseAllCookies(DefaultCookiePolicy):
    def set_ok(self, cookie: object, request: object) -> bool:
        return False

    def return_ok(self, cookie: object, request: object) -> bool:
        return False


def refuse_all_cookies() -> CookieJar:
    """Jar of the reader's client: shared between users, it must keep nothing."""
    return CookieJar(policy=_RefuseAllCookies())


def is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _checked_url(url: str | httpx.URL) -> httpx.URL:
    try:
        parsed = url if isinstance(url, httpx.URL) else httpx.URL(url)
    except (httpx.InvalidURL, TypeError, ValueError):
        raise UrlForbidden() from None
    if parsed.scheme not in ("http", "https") or not parsed.host or parsed.userinfo:
        raise UrlForbidden()
    return parsed


def _check_peer(response: httpx.Response) -> None:
    """Without `network_stream` or `server_addr` (non-httpcore transport), nothing to check:
    residual risk accepted (D63)."""
    stream = response.extensions.get("network_stream")
    peer = stream.get_extra_info("server_addr") if stream is not None else None
    if peer is None:
        return
    host = peer[0] if isinstance(peer, tuple) and peer else peer
    if not is_public_address(str(host)):
        raise UrlForbidden()


def _media_type(response: httpx.Response, allowed: tuple[str, ...]) -> str:
    media = str(response.headers.get("content-type", "")).split(";", 1)[0].strip().lower()
    if media not in allowed:
        raise UrlUnsupported()
    return media


def _request_headers(extra: Mapping[str, str] | None) -> dict[str, str]:
    headers = dict(_HEADERS)
    for name, value in (extra or {}).items():
        if name.lower() not in _LOCKED_HEADERS:
            headers[name.lower()] = value
    return headers


class SafeHttpFetcher:
    """`http` must be created with `follow_redirects=False` and `trust_env=False` (no proxy from
    the environment: the connected address would be the proxy's); see `bootstrap`.
    `throttle` (D74) is awaited before each hop, redirects included, once the URL and
    its addresses are validated: a refused address consumes no slot. The wait counts
    in the 15 s, brought down to the deadline of the read in progress (`READ_DEADLINE`); a slot
    beyond it fails right away as "timed out" without being reserved."""

    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        resolve: Resolver = system_resolve,
        throttle: DomainThrottle | None = None,
    ) -> None:
        self._http = http
        self._resolve = resolve
        self._throttle = throttle

    async def fetch(
        self,
        url: str,
        *,
        content_types: tuple[str, ...] = ALLOWED_CONTENT_TYPES,
        headers: Mapping[str, str] | None = None,
    ) -> FetchedResource:
        deadline = base.deadline_within(base.FETCH_TIMEOUT_S)
        try:
            async with asyncio.timeout_at(deadline):
                return await self._follow(url, content_types, _request_headers(headers), deadline)
        except (TimeoutError, httpx.TimeoutException):
            raise UrlUnreadable(TIMEOUT_MESSAGE) from None
        except httpx.ConnectError as exc:
            if isinstance(exc.__cause__, AddressRefused):
                raise UrlForbidden() from None
            raise UrlUnreadable() from None
        except (httpx.HTTPError, httpx.StreamError):
            raise UrlUnreadable() from None

    async def _follow(
        self, url: str, content_types: tuple[str, ...], headers: dict[str, str], deadline: float
    ) -> FetchedResource:
        current = _checked_url(url)
        for _ in range(MAX_REDIRECTS + 1):
            await self._check_host(current)
            if self._throttle is not None:
                budget = deadline - asyncio.get_running_loop().time()
                await self._throttle.wait(current.host, budget_s=budget)
            async with self._http.stream(
                "GET", current, headers=headers, follow_redirects=False
            ) as response:
                _check_peer(response)
                if response.status_code in _REDIRECTS:
                    current = self._next(current, response)
                    continue
                if not response.is_success:
                    raise UrlUnreadable()
                media = _media_type(response, content_types)
                if declared_too_large(response, base.FETCH_MAX_BYTES):
                    raise UrlTooLarge()
                body = await read_capped(response)
                return FetchedResource(url, str(current), media, body)
        raise UrlUnreadable(TOO_MANY_REDIRECTS_MESSAGE)

    @staticmethod
    def _next(current: httpx.URL, response: httpx.Response) -> httpx.URL:
        location = response.headers.get("location")
        if not location:
            raise UrlUnreadable()
        try:
            target = current.join(location)
        except (httpx.InvalidURL, TypeError, ValueError):
            raise UrlForbidden() from None
        return _checked_url(target)

    async def _check_host(self, url: httpx.URL) -> None:
        """A literal address is judged as is; a name (including the numeric forms
        that `getaddrinfo` interprets, `0x7f.1`, `2130706433`) is judged on all its resolutions."""
        try:
            host = url.raw_host.decode("ascii")
        except UnicodeDecodeError:
            raise UrlForbidden() from None
        if is_ip_literal(host):
            addresses = [host]
        else:
            port = url.port or (443 if url.scheme == "https" else 80)
            try:
                addresses = await self._resolve(host, port)
            except UnicodeError:  # name refused by the IDNA codec (`a..b`, label > 63)
                raise UrlForbidden() from None
            except OSError:
                raise UrlUnreadable() from None
        if not addresses:
            raise UrlUnreadable()
        if not all(is_public_address(address) for address in addresses):
            raise UrlForbidden()
