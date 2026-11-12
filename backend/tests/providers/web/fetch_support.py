"""Réseau factice des tests du lecteur web : résolveur à table fixe et transport `MockTransport`.
Aucun test n'atteint un vrai DNS ni un vrai serveur."""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field

import httpx

from app.providers.web.fetch import Resolver, SafeHttpFetcher
from app.providers.web.throttle import DomainThrottle

PUBLIC_IP = "93.184.216.34"
Handler = Callable[[httpx.Request], httpx.Response]


@dataclass
class FakeResolver:
    """`table` : hôte → adresses ; tout autre hôte se résout en `PUBLIC_IP`."""

    table: dict[str, list[str]] = field(default_factory=dict)
    calls: list[tuple[str, int]] = field(default_factory=list)

    async def __call__(self, host: str, port: int) -> list[str]:
        self.calls.append((host, port))
        return self.table.get(host, [PUBLIC_IP])


class FakeNetworkStream:
    """Ce que `httpcore` pose dans `response.extensions["network_stream"]`."""

    def __init__(self, server_addr: object) -> None:
        self.server_addr = server_addr

    def get_extra_info(self, info: str) -> object:
        return self.server_addr if info == "server_addr" else None


async def streamed(body: bytes) -> AsyncIterator[bytes]:
    """Corps en flux, comme httpcore le rend : `httpx.Response(content=bytes)` serait déjà lu
    et `aiter_raw` le refuserait."""
    yield body


def ok(body: bytes = b"x", status: int = 200, **headers: str) -> httpx.Response:
    return httpx.Response(status, headers=headers, content=streamed(body))


def html(body: bytes = b"<html>ok</html>", **headers: str) -> httpx.Response:
    return ok(body, **{"content-type": "text/html", **headers})


def never(request: httpx.Request) -> httpx.Response:
    raise AssertionError("aucune requête ne doit partir")


def redirect(location: str, status: int = 302) -> httpx.Response:
    return httpx.Response(status, headers={"location": location})


async def endless(chunk: bytes, consumed: list[int]) -> AsyncIterator[bytes]:
    """Corps sans fin et sans `Content-Length` : seul un plafond appliqué en flux l'arrête."""
    while True:
        consumed.append(len(chunk))
        yield chunk


def fetcher_for(
    handler: Handler,
    resolver: Resolver | None = None,
    seen: list[httpx.Request] | None = None,
    *,
    throttle: DomainThrottle | None = None,
) -> tuple[SafeHttpFetcher, httpx.AsyncClient]:
    def recording(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return handler(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(recording), trust_env=False)
    fetcher = SafeHttpFetcher(client, resolve=resolver or FakeResolver(), throttle=throttle)
    return fetcher, client
