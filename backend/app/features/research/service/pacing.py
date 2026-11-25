"""Brave pacing (phase 3 review, I1): the free tier accepts one query per second; beyond that,
Brave answers 429. At most one start every `BRAVE_INTERVAL_S` per key (fingerprint), for the
whole process, awaited after the reservation and before the call.

Same principle as `DomainThrottle` of the web reader (which this feature does not import,
contract 3): the next start is reserved under lock (no `await` in the section), then awaited
outside the lock; a start beyond the caller's budget is not reserved; a cancelled wait gives
back its slot if it is still the last reserved one. Keys are never logged."""

import asyncio
import threading
import time
from collections.abc import Awaitable, Callable

BRAVE_INTERVAL_S = 1.1  # one query per second, plus a margin
# Default maximum wait before a call to Brave (the delay of a search).
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
        self._last: dict[str, float] = {}  # key → last reserved start

    def _reserve(self, key: str, budget_s: float) -> tuple[float, float, float | None] | None:
        """`(wait, reserved start, previous start)`, or `None` beyond budget (nothing reserved)."""
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
        """Waits for the slot of `key`. False, without waiting or reserving, if this slot falls
        beyond `budget_s` (the time the caller agrees to wait)."""
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
