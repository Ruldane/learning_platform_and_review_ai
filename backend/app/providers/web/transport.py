"""Transport du lecteur web : la connexion se fait sur une adresse vérifiée (anti rebinding DNS).

httpcore résout lui-même l'hôte dans `connect_tcp` : entre la vérification de `SafeHttpFetcher`
et la connexion, un DNS à TTL nul peut répondre une autre adresse (127.0.0.1) et la requête
partirait vers le service interne. `GuardedBackend` résout avec le résolveur injecté, refuse
si une adresse n'est pas publique, puis se connecte à l'**adresse** validée : aucune seconde
résolution. TLS reste vérifié sur le nom (httpcore passe `server_hostname=origin.host` à
`start_tls`) et l'en-tête `Host` est inchangé."""

from collections.abc import Iterable

import httpcore
import httpx

from app.providers.web.fetch import (
    AddressRefused,
    Resolver,
    is_ip_literal,
    is_public_address,
    system_resolve,
)

_DEFAULT_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)


class GuardedBackend(httpcore.AsyncNetworkBackend):
    def __init__(
        self, resolve: Resolver, *, inner: httpcore.AsyncNetworkBackend | None = None
    ) -> None:
        self._resolve = resolve
        self._inner = inner or httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        addresses = await self._validated(host, port)
        last: Exception = httpcore.ConnectError("connexion impossible")
        for address in addresses:
            try:
                return await self._inner.connect_tcp(
                    address,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                last = exc
        raise last

    async def _validated(self, host: str, port: int) -> list[str]:
        if is_ip_literal(host):
            addresses = [host]
        else:
            try:
                addresses = await self._resolve(host, port)
            except UnicodeError:
                raise AddressRefused() from None
            except OSError:
                raise httpcore.ConnectError("résolution impossible") from None
        if not addresses or not all(is_public_address(a) for a in addresses):
            raise AddressRefused()
        return list(dict.fromkeys(addresses))

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise AddressRefused()

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


class GuardedTransport(httpx.AsyncHTTPTransport):
    """`AsyncHTTPTransport` dont le pool passe par `GuardedBackend` ; jamais de proxy."""

    def __init__(
        self,
        resolve: Resolver = system_resolve,
        *,
        inner: httpcore.AsyncNetworkBackend | None = None,
    ) -> None:
        super().__init__(trust_env=False)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=httpx.create_ssl_context(trust_env=False),
            max_connections=_DEFAULT_LIMITS.max_connections,
            max_keepalive_connections=_DEFAULT_LIMITS.max_keepalive_connections,
            network_backend=GuardedBackend(resolve, inner=inner),
        )
