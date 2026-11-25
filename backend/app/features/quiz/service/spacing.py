"""Spaced reviews (SPEC F9, D99): pure rules, without database or model.

A card passed moves to the next level (1, 3, 7, 16, then 35 days); an error brings it back to
1 day. The days are January's (local time zone, `core.clock`): the caller gives `today`. The
day's queue holds 15 minutes, at 30 seconds per card."""

from datetime import date, timedelta

INTERVALS = (1, 3, 7, 16, 35)  # days before the next review, per level (`step`)
CARD_SECONDS = 30
QUEUE_MINUTES = 15
DAILY_CARDS = QUEUE_MINUTES * 60 // CARD_SECONDS  # 30 cards per day at most
DEMOTE_AFTER = 2  # consecutive card failures that bring a `valide` skill back down


def first_due(today: date) -> date:
    """The due date of a new card (level 0): tomorrow."""
    return today + timedelta(days=INTERVALS[0])


def next_review(step: int, ok: bool, today: date) -> tuple[int, date]:
    """`(new level, new due date)` after a rating. Success: one level more, capped at the last.
    Failure: back to level 0, tomorrow."""
    new_step = min(step + 1, len(INTERVALS) - 1) if ok else 0
    return new_step, today + timedelta(days=INTERVALS[new_step])


def queue_room(reviewed_today: int) -> int:
    """How many cards still fit in the day's queue."""
    return max(0, DAILY_CARDS - reviewed_today)
