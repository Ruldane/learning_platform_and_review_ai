"""Téléchargement sûr d'une URL fournie par l'utilisateur (garde SSRF, spec 17.4).

Algorithme, sous un délai unique de `FETCH_TIMEOUT_S` pour l'ensemble (redirections comprises) :
1. schéma http/https, hôte présent, aucun identifiant (`user:pass@`), sinon `UrlForbidden` ;
2. toutes les adresses résolues de l'hôte publiques, sinon `UrlForbidden` ;
3. requête en flux sans suivi automatique ; une 3xx revient en 1 avec `Location` résolue
   (5 redirections au plus) ; avec `GuardedTransport` (`transport.py`, branché par
   `bootstrap`), la connexion elle-même résout, revérifie et se fait sur l'adresse validée :
   un DNS qui change entre 2 et la connexion (rebinding) ne reçoit aucune requête ;
4. défense en profondeur : adresse réellement connectée
   (`network_stream.get_extra_info("server_addr")`, httpcore) publique ;
5. `Content-Type` sur liste blanche, taille plafonnée en flux (déclarée puis lue, décompression
   comprise).
Les erreurs sont levées `from None` : la chaîne d'exceptions citerait l'URL dans un journal."""

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
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

Resolver = Callable[[str, int], Awaitable[list[str]]]

_REDIRECTS = frozenset({301, 302, 303, 307, 308})
_HEADERS = {
    "accept": "text/html,application/xhtml+xml,text/plain;q=0.9,text/markdown;q=0.9,"
    "application/pdf;q=0.8",
    "accept-encoding": ACCEPT_ENCODING,
    "user-agent": "Mozilla/5.0 (compatible; TremplinReader/1.0)",
}
_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_IPV6_GLOBAL_UNICAST = ipaddress.ip_network("2000::/3")


class AddressRefused(httpcore.ConnectError):
    """Levée par `GuardedBackend` (adresse non publique à la connexion) ; `SafeHttpFetcher` la
    rend en `UrlForbidden`. Message fixe, sans l'hôte."""

    def __init__(self) -> None:
        super().__init__("adresse refusée")


async def system_resolve(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def is_public_address(ip: str) -> bool:
    """Adresse joignable publiquement (`is_global`, pas multicast). Une IPv6 qui porte une IPv4
    (mappée, NAT64 `64:ff9b::/96`, 6to4) est jugée sur cette IPv4 ; toute autre IPv6 doit être
    unicast globale (`2000::/3`) : site-local, traduite `::ffff:0:0/96`, compatible `::/96`,
    NAT64 local et Teredo sont refusées."""
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
    """Jar du client du lecteur : partagé entre utilisateurs, il ne doit rien retenir."""
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
    """Sans `network_stream` ou `server_addr` (transport non httpcore), rien à vérifier : risque
    résiduel accepté (D63)."""
    stream = response.extensions.get("network_stream")
    peer = stream.get_extra_info("server_addr") if stream is not None else None
    if peer is None:
        return
    host = peer[0] if isinstance(peer, tuple) and peer else peer
    if not is_public_address(str(host)):
        raise UrlForbidden()


def _media_type(response: httpx.Response) -> str:
    media = str(response.headers.get("content-type", "")).split(";", 1)[0].strip().lower()
    if media not in ALLOWED_CONTENT_TYPES:
        raise UrlUnsupported()
    return media


class SafeHttpFetcher:
    """`http` doit être créé avec `follow_redirects=False` et `trust_env=False` (aucun proxy de
    l'environnement : l'adresse connectée serait celle du proxy) ; voir `bootstrap`."""

    def __init__(self, http: httpx.AsyncClient, *, resolve: Resolver = system_resolve) -> None:
        self._http = http
        self._resolve = resolve

    async def fetch(self, url: str) -> FetchedResource:
        try:
            async with asyncio.timeout(base.FETCH_TIMEOUT_S):
                return await self._follow(url)
        except (TimeoutError, httpx.TimeoutException):
            raise UrlUnreadable(TIMEOUT_MESSAGE) from None
        except httpx.ConnectError as exc:
            if isinstance(exc.__cause__, AddressRefused):
                raise UrlForbidden() from None
            raise UrlUnreadable() from None
        except (httpx.HTTPError, httpx.StreamError):
            raise UrlUnreadable() from None

    async def _follow(self, url: str) -> FetchedResource:
        current = _checked_url(url)
        for _ in range(MAX_REDIRECTS + 1):
            await self._check_host(current)
            async with self._http.stream(
                "GET", current, headers=_HEADERS, follow_redirects=False
            ) as response:
                _check_peer(response)
                if response.status_code in _REDIRECTS:
                    current = self._next(current, response)
                    continue
                if not response.is_success:
                    raise UrlUnreadable()
                media = _media_type(response)
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
        """Une adresse littérale est jugée telle quelle ; un nom (y compris les formes numériques
        que `getaddrinfo` interprète, `0x7f.1`, `2130706433`) l'est sur toutes ses résolutions."""
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
            except UnicodeError:  # nom refusé par le codec IDNA (`a..b`, label > 63)
                raise UrlForbidden() from None
            except OSError:
                raise UrlUnreadable() from None
        if not addresses:
            raise UrlUnreadable()
        if not all(is_public_address(address) for address in addresses):
            raise UrlForbidden()
