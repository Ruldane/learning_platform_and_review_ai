"""Rate limit of the web reader per host (SPEC 10.2: one request per second per domain, D74).

A single `DomainThrottle` for the whole process (all users), plugged in by `bootstrap` into the
`SafeHttpFetcher`. Each call reserves the host's next start under a lock (no `await` in the section:
two simultaneous calls never take the same slot), then waits its turn outside the lock. A start that
would fall beyond the caller's budget (`budget_s`) is **not reserved**: the call fails at once with
"deadline exceeded", without pushing back the next ones. A call cancelled while waiting gives its
slot back if it is still the last one reserved; otherwise a gap stays in the queue, without delaying
anyone (review 3.4, D74). The key is the exact host in lowercase, not the registrable domain
(`a.example.org` and `b.example.org` are distinct). The arXiv API asks for 3 s between calls. Hosts
are never logged."""

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
        # Host → instant of the last reserved start.
        self._last: dict[str, float] = {}

    def _reserve(self, key: str, budget_s: float | None) -> tuple[float, float, float | None]:
        """`(wait, reserved start, previous start)`; beyond the budget → `UrlUnreadable` (deadline)
        without
        reserving anything."""
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
        """Gives back the slot `start` if it is still the last one reserved for `key`."""
        with self._lock:
            if self._last.get(key) != start:
                return
            if previous is None:
                del self._last[key]
            else:
                self._last[key] = previous

    def _purge(self, now: float) -> None:
        """Forgets the hosts whose last start is more than 60 s old (under the lock)."""
        stale = [key for key, last in self._last.items() if now - last > _PURGE_AFTER_S]
        for key in stale:
            del self._last[key]

    async def wait(self, host: str, *, budget_s: float | None = None) -> None:
        """Waits for the slot of `host`. `budget_s`: maximum acceptable wait (time the caller has
        left);
        beyond it, `UrlUnreadable(TIMEOUT_MESSAGE)` without waiting or reserving."""
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
        """Number of hosts tracked (for the purge tests)."""
        with self._lock:
            return len(self._last)
