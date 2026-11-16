"""Règles pures du brief du jour (P9, P11, P12) : jour local, échéance, offres nouvelles, nombres
permis dans le conseil. Rien ici n'importe la base ni une autre feature."""

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.core.clock import local_moment, local_today

# Les rubriques calculées par le code ; la ressource et le conseil viennent des agents.
BRIEF_KEYS = ("block", "reviews", "reminders", "offers", "week")
OFFERS_MAX = 5
REMINDERS_MAX = 5
SHOWN_BRIEFS = 7
# Le seuil des offres du brief est celui du radar (`radar.service.rules.HIGH_MATCH`, P9).
MIN_OFFER_SCORE = 70


def brief_day(now: datetime, zone: ZoneInfo) -> date:
    """Le jour local de January à l'instant `now`."""
    return local_today(zone, now)


def brief_due(now: datetime, zone: ZoneInfo, hhmm: str) -> bool:
    """Vrai si l'heure du brief (`hhmm`, heure locale) du jour local de `now` est passée."""
    return now >= local_moment(brief_day(now, zone), hhmm, zone)


def new_offers(
    postings: Sequence[Mapping[str, Any]], shown: AbstractSet[str], known: AbstractSet[str]
) -> list[dict[str, Any]]:
    """Les offres à montrer : score au moins 70, lien (`url_key`) ni déjà montré (`shown`) ni déjà
    saisi (`known`), une fois par lien (le meilleur score), triées par score décroissant puis par
    titre, `OFFERS_MAX` au plus. Une offre sans score ou sans lien est ignorée."""
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
    """Les nombres que le conseil peut citer : ceux des faits du jour (valeur absolue, en
    chiffres ; un fait absent n'en donne aucun). Le code rejette tout autre nombre."""
    return {str(abs(value)) for value in facts.values() if value is not None}
