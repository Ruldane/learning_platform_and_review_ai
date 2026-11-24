"""Pure rules of the daily brief (P9, P11, P12): local day, due time, new offers, numbers allowed
in the advice. Nothing here imports the database or another feature."""

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.core.clock import local_moment, local_today

# Sections computed by the code; the resource and the advice come from the agents.
BRIEF_KEYS = ("block", "reviews", "reminders", "offers", "week")
OFFERS_MAX = 5
REMINDERS_MAX = 5
SHOWN_BRIEFS = 7
# The brief offer threshold is the radar's (`radar.service.rules.HIGH_MATCH`, P9).
MIN_OFFER_SCORE = 70


def brief_day(now: datetime, zone: ZoneInfo) -> date:
    """January's local day at the moment `now`."""
    return local_today(zone, now)


def brief_due(now: datetime, zone: ZoneInfo, hhmm: str) -> bool:
    """True if the brief time (`hhmm`, local time) of the local day of `now` has passed."""
    return now >= local_moment(brief_day(now, zone), hhmm, zone)


def new_offers(
    postings: Sequence[Mapping[str, Any]], shown: AbstractSet[str], known: AbstractSet[str]
) -> list[dict[str, Any]]:
    """Offers to show: score at least 70, link (`url_key`) neither already shown (`shown`) nor
    already entered (`known`), once per link (the best score), sorted by descending score then
    title, `OFFERS_MAX` at most. An offer without a score or a link is ignored."""
    best: dict[str, dict[str, Any]] = {}
    for posting in postings:
        key, score = posting.get("url_key"), posting.get("score")
        if not isinstance(key, str) or not key or key in shown or key in known:
            continue
        if not isinstance(score, int) or isinstance(score, bool) or score < MIN_OFFER_SCORE:
            continue
        current = best.get(key)
        if current is None or score > current["score"]:
            best[key] = dict(posting)
    ranked = sorted(best.values(), key=lambda p: (-p["score"], str(p.get("title") or "")))
    return ranked[:OFFERS_MAX]


def advice_numbers(facts: Mapping[str, int | None]) -> set[str]:
    """Numbers the advice may quote: those of the day's facts (absolute value, as digits; a
    missing fact gives none). The code rejects any other number."""
    return {str(abs(value)) for value in facts.values() if value is not None}
