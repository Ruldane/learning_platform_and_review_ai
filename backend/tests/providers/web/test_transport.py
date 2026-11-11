"""Anti rebinding DNS : la connexion se fait sur l'adresse validée (`GuardedBackend`). Seule la
boucle locale est touchée (serveur dans le processus), jamais le réseau extérieur."""

import asyncio
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager

import httpcore
import httpx
import pytest

from app.providers.web.base import UrlForbidden, UrlUnreadable
from app.providers.web.fetch import AddressRefused, SafeHttpFetcher, refuse_all_cookies
from app.providers.web.transport import GuardedBackend, GuardedTransport
from tests.providers.web.fetch_support import PUBLIC_IP, FakeResolver

OTHER_PUBLIC_IP = "93.184.216.35"
_OK = [b"HTTP/1.1 200 OK\r\n", b"Content-Type: text/html\r\n", b"Content-Length: 2\r\n\r\n", b"ok"]


class RecordingBackend(httpcore.AsyncNetworkBackend):
    """Backend interne factice : note les adresses demandées ; `refuse` simule un échec."""

    def __init__(self, refuse: Iterable[str] = ()) -> None:
        self.hosts: list[str] = []
        self.slept: list[float] = []
        self._refuse = set(refuse)

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        self.hosts.append(host)
        if host in self._refuse:
            raise httpcore.ConnectError("refusé")
        return httpcore.AsyncMockStream(list(_OK))

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)


async def test_connects_to_the_validated_address_never_to_the_name() -> None:
    inner = RecordingBackend()
    backend = GuardedBackend(FakeResolver({"example.com": [PUBLIC_IP]}), inner=inner)
    await backend.connect_tcp("example.com", 443)
    assert inner.hosts == [PUBLIC_IP]


async def test_tries_each_validated_address_in_turn() -> None:
    inner = RecordingBackend(refuse=[PUBLIC_IP])
    resolver = FakeResolver({"example.com": [PUBLIC_IP, PUBLIC_IP, OTHER_PUBLIC_IP]})
    await GuardedBackend(resolver, inner=inner).connect_tcp("example.com", 80)
    assert inner.hosts == [PUBLIC_IP, OTHER_PUBLIC_IP]


async def test_all_addresses_failing_is_a_plain_connect_error() -> None:
    inner = RecordingBackend(refuse=[PUBLIC_IP])
    backend = GuardedBackend(FakeResolver({"example.com": [PUBLIC_IP]}), inner=inner)
    with pytest.raises(httpcore.ConnectError) as caught:
        await backend.connect_tcp("example.com", 80)
    assert not isinstance(caught.value, AddressRefused)


@pytest.mark.parametrize(
    ("host", "table"),
    [
        ("example.com", {"example.com": ["127.0.0.1"]}),
        ("example.com", {"example.com": [PUBLIC_IP, "10.0.0.1"]}),
        ("example.com", {"example.com": []}),
        ("127.0.0.1", {}),
        ("::1", {}),
    ],
)
async def test_refuses_non_public_addresses_without_connecting(
    host: str, table: dict[str, list[str]]
) -> None:
    inner = RecordingBackend()
    resolver = FakeResolver(table)
    with pytest.raises(AddressRefused):
        await GuardedBackend(resolver, inner=inner).connect_tcp(host, 80)
    assert inner.hosts == []
    if host[0].isdigit() or ":" in host:
        assert resolver.calls == []  # adresse littérale jugée telle quelle


async def test_resolution_errors_never_connect() -> None:
    async def idna(host: str, port: int) -> list[str]:
        raise UnicodeError("label vide")

    async def dns_down(host: str, port: int) -> list[str]:
        raise OSError("dns")

    inner = RecordingBackend()
    with pytest.raises(AddressRefused):
        await GuardedBackend(idna, inner=inner).connect_tcp("a..b", 80)
    with pytest.raises(httpcore.ConnectError) as caught:
        await GuardedBackend(dns_down, inner=inner).connect_tcp("example.com", 80)
    assert not isinstance(caught.value, AddressRefused) and inner.hosts == []


async def test_unix_sockets_are_refused_and_sleep_is_delegated() -> None:
    inner = RecordingBackend()
    backend = GuardedBackend(FakeResolver(), inner=inner)
    with pytest.raises(AddressRefused):
        await backend.connect_unix_socket("/var/run/docker.sock")
    await backend.sleep(0.5)
    assert inner.slept == [0.5] and inner.hosts == []


async def test_fetcher_through_the_guarded_transport() -> None:
    inner = RecordingBackend()
    transport = GuardedTransport(FakeResolver(), inner=inner)
    async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
        got = await SafeHttpFetcher(client, resolve=FakeResolver()).fetch("http://example.com/")
    assert got.body == b"ok" and inner.hosts == [PUBLIC_IP]


class Rebinding:
    """Première réponse publique (contrôle de `SafeHttpFetcher`), puis 127.0.0.1 : un DNS à TTL
    nul qui change d'avis entre la vérification et la connexion."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, host: str, port: int) -> list[str]:
        self.calls += 1
        return [PUBLIC_IP] if self.calls == 1 else ["127.0.0.1"]


@asynccontextmanager
async def loopback_server(served: list[bytes]) -> AsyncIterator[int]:
    async def serve(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        served.append(await reader.readuntil(b"\r\n\r\n"))
        writer.write(b"".join(_OK))
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    async with server:
        yield server.sockets[0].getsockname()[1]


async def test_dns_rebinding_delivers_no_request_to_the_internal_service() -> None:
    served: list[bytes] = []
    rebinding = Rebinding()
    async with loopback_server(served) as port:
        client = httpx.AsyncClient(
            transport=GuardedTransport(rebinding),
            trust_env=False,
            cookies=refuse_all_cookies(),
        )
        async with client:
            with pytest.raises(UrlForbidden):
                await SafeHttpFetcher(client, resolve=rebinding).fetch(
                    f"http://rebind.test:{port}/"
                )
    assert served == [] and rebinding.calls == 2


async def test_without_the_guarded_transport_the_peer_check_still_refuses() -> None:
    """Défense en profondeur, contrat httpcore réel : sans `GuardedTransport`, la requête part
    (d'où le transport gardé) mais l'adresse connectée 127.0.0.1 est refusée ensuite."""
    served: list[bytes] = []
    async with loopback_server(served) as port, httpx.AsyncClient(trust_env=False) as client:
        fetcher = SafeHttpFetcher(client, resolve=FakeResolver({"localhost": [PUBLIC_IP]}))
        with pytest.raises(UrlForbidden):
            await fetcher.fetch(f"http://localhost:{port}/")
    assert len(served) == 1


async def test_dns_failure_at_connection_is_unreachable() -> None:
    calls: list[str] = []

    async def flaky(host: str, port: int) -> list[str]:
        calls.append(host)
        if len(calls) > 1:
            raise OSError("dns")
        return [PUBLIC_IP]

    async with httpx.AsyncClient(transport=GuardedTransport(flaky), trust_env=False) as client:
        with pytest.raises(UrlUnreadable):
            await SafeHttpFetcher(client, resolve=flaky).fetch("http://example.com/")
