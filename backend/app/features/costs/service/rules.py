"""Règles pures du rapport des coûts (P15) : la fenêtre en jours locaux, puis l'agrégation des
appels par jour, par fonction (le graphe de la session), par agent et par modèle. Aucune
entrée-sortie."""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.features.costs.schemas import CostRow, CostsReport, CostTotals

WINDOWS = (7, 30, 90)
_DECIMALS = 6


@dataclass(frozen=True)
class CallFact:
    """Un appel journalisé, réduit à ce que le rapport compte."""

    at: datetime
    graph: str | None
    agent: str | None
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    estimated: bool


def window(today: date, days: int) -> tuple[date, date]:
    """Les `days` derniers jours locaux, aujourd'hui compris : `(since, until)`."""
    return today - timedelta(days=days - 1), today


def _local_day(fact: CallFact, zone: ZoneInfo) -> date:
    moment = fact.at if fact.at.tzinfo is not None else fact.at.replace(tzinfo=UTC)
    return moment.astimezone(zone).date()


def _totals(facts: Iterable[CallFact]) -> CostTotals:
    group = list(facts)
    return CostTotals(
        calls=len(group),
        tokens_in=sum(f.tokens_in for f in group),
        tokens_out=sum(f.tokens_out for f in group),
        cost_usd=round(sum(f.cost_usd for f in group), _DECIMALS),
        estimated_calls=sum(1 for f in group if f.estimated),
    )


def _rows(facts: Sequence[CallFact], key_of: Callable[[CallFact], str]) -> list[CostRow]:
    """Une ligne par clé rencontrée, la plus coûteuse d'abord, puis par clé."""
    groups: dict[str, list[CallFact]] = {}
    for fact in facts:
        groups.setdefault(key_of(fact), []).append(fact)
    rows = [CostRow(key=key, **_totals(group).model_dump()) for key, group in groups.items()]
    return sorted(rows, key=lambda row: (-row.cost_usd, row.key))


def aggregate(calls: Sequence[CallFact], zone: ZoneInfo, since: date, until: date) -> CostsReport:
    """Le rapport des appels dont le jour local tombe entre `since` et `until` inclus.

    `by_day` compte chaque jour de la fenêtre, zéros compris, dans l'ordre chronologique ; les
    autres axes ne listent que les clés rencontrées, la plus coûteuse d'abord (puis par clé)."""
    per_day: dict[date, list[CallFact]] = {}
    for call in calls:
        day = _local_day(call, zone)
        if since <= day <= until:
            per_day.setdefault(day, []).append(call)
    inside = [call for group in per_day.values() for call in group]
    span = (until - since).days + 1
    by_day = [
        CostRow(key=day.isoformat(), **_totals(per_day.get(day, [])).model_dump())
        for day in (since + timedelta(days=offset) for offset in range(span))
    ]
    return CostsReport(
        days=span,
        since=since,
        until=until,
        total=_totals(inside),
        by_day=by_day,
        by_feature=_rows(inside, lambda call: call.graph or ""),
        by_agent=_rows(inside, lambda call: call.agent or ""),
        by_model=_rows(inside, lambda call: f"{call.provider}:{call.model}"),
    )
