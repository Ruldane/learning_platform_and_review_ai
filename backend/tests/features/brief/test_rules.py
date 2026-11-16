"""Règles pures du brief du jour (8.1, P9, P11, P12)."""

from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.features.brief.service.rules import (
    BRIEF_KEYS,
    MIN_OFFER_SCORE,
    OFFERS_MAX,
    REMINDERS_MAX,
    SHOWN_BRIEFS,
    advice_numbers,
    brief_day,
    brief_due,
    new_offers,
)
from app.features.radar.service.rules import HIGH_MATCH

PARIS = ZoneInfo("Europe/Paris")


def test_constants() -> None:
    assert BRIEF_KEYS == ("block", "reviews", "reminders", "offers", "week")
    assert (OFFERS_MAX, REMINDERS_MAX, SHOWN_BRIEFS) == (5, 5, 7)
    assert MIN_OFFER_SCORE == HIGH_MATCH  # deux seuils, un seul chiffre


def test_brief_day_is_local() -> None:
    now = datetime(2026, 11, 15, 23, 30, tzinfo=UTC)
    assert brief_day(now, PARIS) == date(2026, 11, 16)
    assert brief_day(now, ZoneInfo("UTC")) == date(2026, 11, 15)


def test_brief_due_before_and_after_hour() -> None:
    before = datetime(2026, 11, 16, 5, 59, tzinfo=UTC)  # 6 h 59 à Paris
    at = datetime(2026, 11, 16, 6, 0, tzinfo=UTC)  # 7 h
    assert not brief_due(before, PARIS, "07:00")
    assert brief_due(at, PARIS, "07:00")
    assert brief_due(datetime(2026, 11, 16, 20, 0, tzinfo=UTC), PARIS, "07:00")


def test_brief_due_uses_the_local_day() -> None:
    # Dimanche 23 h 30 UTC = lundi 00 h 30 à Paris : le brief du lundi n'est pas encore dû.
    assert not brief_due(datetime(2026, 11, 15, 23, 30, tzinfo=UTC), PARIS, "07:00")


def offer(url_key: str, score: int, title: str = "Poste") -> dict[str, Any]:
    return {"url_key": url_key, "score": score, "title": title}


def test_new_offers_filters_shown_and_known() -> None:
    postings = [
        offer("a", 90),
        offer("b", 69),  # sous le seuil
        offer("c", 80),  # déjà montrée
        offer("d", 75),  # déjà saisie
        offer("e", 70),
    ]
    out = new_offers(postings, shown={"c"}, known={"d"})
    assert [o["url_key"] for o in out] == ["a", "e"]


def test_new_offers_sorted_by_score_then_title_and_capped() -> None:
    postings = [offer(f"k{i}", 80, title=f"T{i}") for i in range(7)]
    postings.append(offer("top", 95, title="Z"))
    out = new_offers(postings, set(), set())
    assert [o["url_key"] for o in out] == ["top", "k0", "k1", "k2", "k3"]


def test_new_offers_keeps_each_link_once_and_ignores_unscored() -> None:
    postings = [
        offer("a", 72),
        offer("a", 88),  # le même lien dans un autre relevé : le meilleur score reste
        {"url_key": "x", "title": "Sans score"},
        {"url_key": "y", "score": None, "title": "Score nul"},
        {"score": 99, "title": "Sans lien"},
    ]
    out = new_offers(postings, set(), set())
    assert [(o["url_key"], o["score"]) for o in out] == [("a", 88)]


def test_advice_numbers() -> None:
    assert advice_numbers({"streak": 4, "due": 0, "offers": None, "delta": -3}) == {"4", "0", "3"}
    assert advice_numbers({}) == set()
