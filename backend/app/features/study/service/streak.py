"""Streak of study days (SPEC F14): pure rule, in January's local days."""

from collections.abc import Set as AbstractSet
from datetime import date, timedelta


def streak(days: AbstractSet[date], today: date) -> int:
    """The number of consecutive study days up to today, or up to yesterday if January has not yet
    studied today (the streak only breaks at midnight after a day without a session)."""
    day = today if today in days else today - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count
