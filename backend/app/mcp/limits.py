"""Limites d'appels du MCP, par jeton (phase 10, P17) : 60 appels et 10 écritures par minute,
1 000 appels et 100 écritures par jour, 20 demandes de niveau 3 par jour, 2 exécutions de code par
minute. Au-delà : 429 `rate_limited` avec `retry_after` (secondes) et un message lisible.

Les compteurs sont en mémoire (un seul processus) : un redémarrage les remet à zéro, ce qui ne
donne aucun droit de plus qu'un jeton valide n'en avait déjà (l'interrupteur et la révocation
restent immédiats, ils sont en base)."""

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
    """Valeurs de départ (P17), réglables en les passant à `RateLimiter`."""

    calls_per_minute: int = 60
    writes_per_minute: int = 10
    calls_per_day: int = 1_000
    writes_per_day: int = 100
    confirmations_per_day: int = 20
    code_runs_per_minute: int = 2
    requests_per_minute: int = 600  # toute requête authentifiée (plafond grossier)


@dataclass(frozen=True)
class _Rule:
    kind: str  # le compteur
    window: timedelta
    limit: int
    subject: str  # ce que la limite compte, pour le message


def _wait_text(seconds: int) -> str:
    if seconds <= 90:
        return f"{seconds} s"
    if seconds <= 5_400:
        return f"{ceil(seconds / 60)} min"
    return f"{ceil(seconds / 3_600)} h"


class RateLimiter:
    """`check` compte un appel et le refuse s'il dépasse l'une des limites qui le concernent ;
    un appel refusé n'est pas compté."""

    def __init__(self, limits: Limits | None = None) -> None:
        self._limits = limits or Limits()
        self._events: dict[tuple[str, str], deque[datetime]] = {}

    def _rules(self, level: Level, bucket: str | None) -> list[_Rule]:
        lim = self._limits
        rules = [
            _Rule("calls", MINUTE, lim.calls_per_minute, "appels"),
            _Rule("calls", DAY, lim.calls_per_day, "appels"),
        ]
        if level >= 2:
            rules += [
                _Rule("writes", MINUTE, lim.writes_per_minute, "écritures"),
                _Rule("writes", DAY, lim.writes_per_day, "écritures"),
            ]
        if level == 3:
            rules.append(_Rule("confirm", DAY, lim.confirmations_per_day, "demandes à confirmer"))
        if bucket == CODE_RUN_BUCKET:
            rules.append(
                _Rule(CODE_RUN_BUCKET, MINUTE, lim.code_runs_per_minute, "exécutions de code")
            )
        return rules

    def _events_of(self, token_id: str, kind: str, now: datetime) -> deque[datetime]:
        """Les instants du compteur, sans ceux de plus d'un jour (la plus longue fenêtre)."""
        events = self._events.setdefault((token_id, kind), deque())
        while events and events[0] <= now - DAY:
            events.popleft()
        return events

    def _wait_seconds(self, events: deque[datetime], rule: _Rule, now: datetime) -> int | None:
        """Secondes à attendre si la règle est atteinte, sinon `None`."""
        cutoff = now - rule.window
        inside = [moment for moment in events if moment > cutoff]
        if len(inside) < rule.limit:
            return None
        frees_at = inside[len(inside) - rule.limit] + rule.window
        return max(1, ceil((frees_at - now).total_seconds()))

    async def check(
        self, identity: McpIdentity, level: Level, now: datetime, *, bucket: str | None = None
    ) -> None:
        """Compte l'appel du jeton ; lève `AppError("rate_limited", …, 429, {"retry_after": s})`
        si une limite est atteinte. `bucket` : compteur à part d'un outil (`code_run`)."""
        rules = self._rules(level, bucket)
        worst: tuple[int, _Rule] | None = None
        for rule in rules:
            events = self._events_of(identity.token_id, rule.kind, now)
            wait = self._wait_seconds(events, rule, now)
            if wait is not None and (worst is None or wait > worst[0]):
                worst = (wait, rule)
        if worst is not None:
            self._forget_empty(identity.token_id)
            raise _too_many(*worst)
        for kind in dict.fromkeys(rule.kind for rule in rules):
            self._events_of(identity.token_id, kind, now).append(now)

    async def check_request(self, token_id: str, now: datetime) -> None:
        """Plafond grossier de toute requête authentifiée (`ping`, `tools/list`, JSON invalide…),
        avant la moindre écriture en base. Même 429 lisible que `check`."""
        rule = _Rule("requests", MINUTE, self._limits.requests_per_minute, "requêtes")
        events = self._events_of(token_id, rule.kind, now)
        wait = self._wait_seconds(events, rule, now)
        if wait is not None:
            raise _too_many(wait, rule)
        events.append(now)

    def _forget_empty(self, token_id: str) -> None:
        for key in [k for k, events in self._events.items() if k[0] == token_id and not events]:
            del self._events[key]


def _too_many(wait: int, rule: _Rule) -> AppError:
    per = "par minute" if rule.window == MINUTE else "par jour"
    message = (
        f"Trop de requêtes : la limite de {rule.limit} {rule.subject} {per} est atteinte. "
        f"Réessaie dans {_wait_text(wait)}."
    )
    return AppError(
        "rate_limited",
        message,
        429,
        {
            "retry_after": wait,
            "limit": rule.limit,
            "window": "minute" if per == "par minute" else "day",
        },
    )
