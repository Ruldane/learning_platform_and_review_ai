"""Débit du lecteur web par hôte (SPEC 10.2 : une requête par seconde et par domaine, D74).

Un seul `DomainThrottle` pour tout le processus (tous utilisateurs), branché par `bootstrap` dans
le `SafeHttpFetcher`. Chaque appel réserve le prochain départ de l'hôte sous verrou (aucun
`await` dans la section : deux appels simultanés ne prennent jamais le même créneau), puis
attend son tour hors verrou. Un départ qui tomberait au-delà du budget de l'appelant
(`budget_s`) n'est **pas réservé** : l'appel échoue tout de suite en « délai dépassé », sans
repousser les suivants. Un appel annulé pendant son attente rend son créneau s'il est encore le
dernier réservé ; sinon un trou reste dans la file, sans retarder personne (revue 3.4, D74).
La clé est l'hôte exact en minuscules, pas le domaine enregistrable (`a.example.org` et
`b.example.org` sont distincts). L'API arXiv demande 3 s entre deux appels. Les hôtes ne sont
jamais journalisés."""

import asyncio
import threading
import time
from collections.abc import Awaitable, Callable, Mapping

from app.providers.web.base import TIMEOUT_MESSAGE, UrlUnreadable

DEFAULT_INTERVAL_S = 1.0
DEFAULT_OVERRIDES: Mapping[str, float] = {"export.arxiv.org": 3.0}
_PURGE_AFTER_S = 60.0


class DomainThrottle:
    def __init__(
        self,
        *,
        interval_s: float = DEFAULT_INTERVAL_S,
        overrides: Mapping[str, float] | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._interval_s = interval_s
        chosen = DEFAULT_OVERRIDES if overrides is None else overrides
        self._overrides = {host.lower(): value for host, value in chosen.items()}
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        # Hôte → instant du dernier départ réservé.
        self._last: dict[str, float] = {}

    def _reserve(self, key: str, budget_s: float | None) -> tuple[float, float, float | None]:
        """`(attente, départ réservé, départ précédent)` ; hors budget → `UrlUnreadable`
        (délai) sans rien réserver."""
        interval = self._overrides.get(key, self._interval_s)
        with self._lock:
            now = self._clock()
            self._purge(now)
            previous = self._last.get(key)
            start = now if previous is None else max(now, previous + interval)
            if budget_s is not None and start - now > max(budget_s, 0.0):
                raise UrlUnreadable(TIMEOUT_MESSAGE)
            self._last[key] = start
        return start - now, start, previous

    def _release(self, key: str, start: float, previous: float | None) -> None:
        """Rend le créneau `start` s'il est encore le dernier réservé pour `key`."""
        with self._lock:
            if self._last.get(key) != start:
                return
            if previous is None:
                del self._last[key]
            else:
                self._last[key] = previous

    def _purge(self, now: float) -> None:
        """Oublie les hôtes dont le dernier départ date de plus de 60 s (sous le verrou)."""
        stale = [key for key, last in self._last.items() if now - last > _PURGE_AFTER_S]
        for key in stale:
            del self._last[key]

    async def wait(self, host: str, *, budget_s: float | None = None) -> None:
        """Attend le créneau de `host`. `budget_s` : attente maximale acceptable (temps qui
        reste à l'appelant) ; au-delà, `UrlUnreadable(TIMEOUT_MESSAGE)` sans attendre ni
        réserver."""
        key = host.lower()
        delay, start, previous = self._reserve(key, budget_s)
        if delay <= 0:
            return
        try:
            await self._sleep(delay)
        except asyncio.CancelledError:
            self._release(key, start, previous)
            raise

    def tracked_hosts(self) -> int:
        """Nombre d'hôtes suivis (tests de la purge)."""
        with self._lock:
            return len(self._last)
