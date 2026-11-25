"""MCP call limits, per token (phase 10, P17): 60 calls and 10 writes per minute, 1,000 calls and
100 writes per day, 20 level 3 requests per day, 2 code runs per minute. Beyond that: 429
`rate_limited` with `retry_after` (seconds) and a readable message.

The counters are in memory (a single process): a restart resets them, which grants no more right
than a valid token already had (the switch and revocation stay immediate, as they are in the
database)."""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil

from app.core.caller import McpIdentity
from app.core.errors import AppError
from app.mcp.base import Level

MINUTE = timedelta(minutes=1)
DAY = timedelta(days=1)
CODE_RUN_BUCKET = "code_run"


@dataclass(frozen=True)
class Limits:
    """Starting values (P17), adjustable by passing them to `RateLimiter`. The daily call and write
    limits are `None` when they are turned off (D311)."""

    calls_per_minute: int = 60
    writes_per_minute: int = 10
    calls_per_day: int | None = 1_000
    writes_per_day: int | None = 100
    confirmations_per_day: int = 20
    code_runs_per_minute: int = 2
    requests_per_minute: int = 600  # any authenticated request (rough cap)

    @classmethod
    def with_daily(cls, *, writes_per_day: int, calls_per_day: int) -> "Limits":
        """The starting limits with the daily ones set (`MCP_WRITES_PER_DAY`, `MCP_CALLS_PER_DAY`):
        0 turns the limit off."""
        return cls(writes_per_day=writes_per_day or None, calls_per_day=calls_per_day or None)


@dataclass(frozen=True)
class _Rule:
    kind: str  # the counter
    window: timedelta
    limit: int
    subject: str  # what the limit counts, for the message


def _wait_text(seconds: int) -> str:
    if seconds <= 90:
        return f"{seconds} s"
    if seconds <= 5_400:
        return f"{ceil(seconds / 60)} min"
    return f"{ceil(seconds / 3_600)} h"


class RateLimiter:
    """`check` counts a call and refuses it if it exceeds one of the limits that apply to it; a
    refused call is not counted."""

    def __init__(self, limits: Limits | None = None) -> None:
        self._limits = limits or Limits()
        # One counter per token, per kind and per window: each keeps only the instants of its
        # own window (at most `limit`; a refused call is not counted).
        self._events: dict[tuple[str, str, timedelta], deque[datetime]] = {}

    def _rules(self, level: Level, bucket: str | None) -> list[_Rule]:
        lim = self._limits
        rules = [_Rule("calls", MINUTE, lim.calls_per_minute, "calls")]
        if lim.calls_per_day is not None:
            rules.append(_Rule("calls", DAY, lim.calls_per_day, "calls"))
        if level >= 2:
            rules.append(_Rule("writes", MINUTE, lim.writes_per_minute, "writes"))
            if lim.writes_per_day is not None:
                rules.append(_Rule("writes", DAY, lim.writes_per_day, "writes"))
        if level == 3:
            rules.append(_Rule("confirm", DAY, lim.confirmations_per_day, "requests to confirm"))
        if bucket == CODE_RUN_BUCKET:
            rules.append(_Rule(CODE_RUN_BUCKET, MINUTE, lim.code_runs_per_minute, "code runs"))
        return rules

    def _events_of(self, token_id: str, rule: _Rule, now: datetime) -> deque[datetime]:
        """The instants of the rule's counter, without those that have left its window."""
        events = self._events.setdefault((token_id, rule.kind, rule.window), deque())
        while events and events[0] <= now - rule.window:
            events.popleft()
        return events

    @staticmethod
    def _wait_seconds(events: deque[datetime], rule: _Rule, now: datetime) -> int | None:
        """Seconds to wait if the rule is reached, otherwise `None` (`events`: already pruned)."""
        if len(events) < rule.limit:
            return None
        frees_at = events[len(events) - rule.limit] + rule.window
        return max(1, ceil((frees_at - now).total_seconds()))

    async def check(
        self, identity: McpIdentity, level: Level, now: datetime, *, bucket: str | None = None
    ) -> None:
        """Counts the token's call; raises `AppError("rate_limited", …, 429, {"retry_after": s})` if
        a
        limit is reached. `bucket`: a counter separate from a tool's (`code_run`)."""
        rules = self._rules(level, bucket)
        worst: tuple[int, _Rule] | None = None
        for rule in rules:
            events = self._events_of(identity.token_id, rule, now)
            wait = self._wait_seconds(events, rule, now)
            if wait is not None and (worst is None or wait > worst[0]):
                worst = (wait, rule)
        if worst is not None:
            self._forget_empty(identity.token_id)
            raise _too_many(*worst)
        for rule in rules:
            self._events_of(identity.token_id, rule, now).append(now)

    async def check_request(self, token_id: str, now: datetime) -> None:
        """Rough cap on any authenticated request (`ping`, `tools/list`, invalid JSON...), before
        any
        database write. Same readable 429 as `check`."""
        rule = _Rule("requests", MINUTE, self._limits.requests_per_minute, "requests")
        events = self._events_of(token_id, rule, now)
        wait = self._wait_seconds(events, rule, now)
        if wait is not None:
            raise _too_many(wait, rule)
        events.append(now)

    def _forget_empty(self, token_id: str) -> None:
        for key in [k for k, events in self._events.items() if k[0] == token_id and not events]:
            del self._events[key]


def _too_many(wait: int, rule: _Rule) -> AppError:
    per = "per minute" if rule.window == MINUTE else "per day"
    message = (
        f"Too many requests: the limit of {rule.limit} {rule.subject} {per} is reached. "
        f"Retry in {_wait_text(wait)}."
    )
    return AppError(
        "rate_limited",
        message,
        429,
        {
            "retry_after": wait,
            "limit": rule.limit,
            "window": "minute" if per == "per minute" else "day",
        },
    )
