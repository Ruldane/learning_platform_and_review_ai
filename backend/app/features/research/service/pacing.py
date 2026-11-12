"""Cadence de Brave (revue de la phase 3, I1) : l'offre gratuite accepte une requête par
seconde ; au-delà, Brave répond 429. Un départ au plus tous les `BRAVE_INTERVAL_S` par clé
(empreinte), pour tout le processus, attendu après la réservation et avant l'appel.

Même principe que `DomainThrottle` du lecteur web (que la feature n'importe pas, contrat 3) :
le prochain départ est réservé sous verrou (aucun `await` dans la section), puis attendu hors
verrou ; un départ au-delà du budget de l'appelant n'est pas réservé ; une attente annulée rend
son créneau s'il est encore le dernier réservé. Les clés ne sont jamais journalisées."""

import asyncio
import threading
import time
from collections.abc import Awaitable, Callable

BRAVE_INTERVAL_S = 1.1  # une requête par seconde, plus une marge
# Attente maximale par défaut avant un appel à Brave (le délai d'une recherche).
BRAVE_MAX_WAIT_S = 10.0
_PURGE_AFTER_S = 60.0


class KeyPacer:
    def __init__(
        self,
        interval_s: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._interval_s = interval_s
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last: dict[str, float] = {}  # clé → dernier départ réservé

    def _reserve(self, key: str, budget_s: float) -> tuple[float, float, float | None] | None:
        """`(attente, départ réservé, départ précédent)`, ou `None` hors budget (rien réservé)."""
        with self._lock:
            now = self._clock()
            for stale in [k for k, last in self._last.items() if now - last > _PURGE_AFTER_S]:
                del self._last[stale]
            previous = self._last.get(key)
            start = now if previous is None else max(now, previous + self._interval_s)
            if start - now > max(budget_s, 0.0):
                return None
            self._last[key] = start
        return start - now, start, previous

    def _release(self, key: str, start: float, previous: float | None) -> None:
        with self._lock:
            if self._last.get(key) != start:
                return
            if previous is None:
                del self._last[key]
            else:
                self._last[key] = previous

    async def wait(self, key: str, *, budget_s: float) -> bool:
        """Attend le créneau de `key`. Faux, sans attendre ni réserver, si ce créneau tombe
        au-delà de `budget_s` (temps que l'appelant accepte d'attendre)."""
        slot = self._reserve(key, budget_s)
        if slot is None:
            return False
        delay, start, previous = slot
        if delay > 0:
            try:
                await self._sleep(delay)
            except asyncio.CancelledError:
                self._release(key, start, previous)
                raise
        return True
