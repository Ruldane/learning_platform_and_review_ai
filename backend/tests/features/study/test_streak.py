"""Série de jours d'étude (F14)."""

from datetime import date, timedelta

from app.features.study.service.streak import streak

TODAY = date(2026, 11, 12)


def _days(*offsets: int) -> set[date]:
    return {TODAY - timedelta(days=n) for n in offsets}


def test_streak_counts_until_today() -> None:
    assert streak(_days(0, 1, 2), TODAY) == 3


def test_streak_counts_until_yesterday_when_nothing_today() -> None:
    assert streak(_days(1, 2, 3, 4), TODAY) == 4


def test_streak_breaks_on_a_gap() -> None:
    assert streak(_days(0, 1, 3, 4, 5), TODAY) == 2


def test_streak_is_zero_when_idle_two_days() -> None:
    assert streak(_days(2, 3), TODAY) == 0
    assert streak(set(), TODAY) == 0


def test_future_days_are_ignored() -> None:
    assert streak({TODAY + timedelta(days=1), TODAY}, TODAY) == 1
