"""Révisions espacées (F9) : intervalles 1, 3, 7, 16 puis 35 jours ; une erreur ramène à 1 jour."""

from datetime import date, timedelta

import pytest

from app.features.quiz.service.spacing import (
    CARD_SECONDS,
    DAILY_CARDS,
    DEMOTE_AFTER,
    INTERVALS,
    QUEUE_MINUTES,
    first_due,
    next_review,
    queue_room,
)

D = date(2026, 11, 12)


def test_constants_follow_the_spec() -> None:
    assert INTERVALS == (1, 3, 7, 16, 35)
    assert (CARD_SECONDS, QUEUE_MINUTES, DAILY_CARDS, DEMOTE_AFTER) == (30, 15, 30, 2)
    assert DAILY_CARDS == QUEUE_MINUTES * 60 // CARD_SECONDS


def test_first_due_is_tomorrow() -> None:
    assert first_due(D) == D + timedelta(days=1)


@pytest.mark.parametrize(
    ("step", "ok", "expected"),
    [
        (0, True, (1, D + timedelta(days=3))),
        (1, True, (2, D + timedelta(days=7))),
        (2, True, (3, D + timedelta(days=16))),
        (3, True, (4, D + timedelta(days=35))),
        (4, True, (4, D + timedelta(days=35))),
        (3, False, (0, D + timedelta(days=1))),
        (0, False, (0, D + timedelta(days=1))),
    ],
)
def test_next_review(step: int, ok: bool, expected: tuple[int, date]) -> None:
    assert next_review(step, ok, D) == expected


def test_queue_room_caps_at_30() -> None:
    assert (queue_room(0), queue_room(29), queue_room(30), queue_room(40)) == (30, 1, 0, 0)
