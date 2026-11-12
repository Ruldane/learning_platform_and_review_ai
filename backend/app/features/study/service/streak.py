"""Série de jours d'étude (SPEC F14) : règle pure, en jours locaux de January."""

from collections.abc import Set as AbstractSet
from datetime import date, timedelta


def streak(days: AbstractSet[date], today: date) -> int:
    """Le nombre de jours consécutifs d'étude jusqu'à aujourd'hui, ou jusqu'à hier si January
    n'a pas encore étudié aujourd'hui (la série ne tombe qu'à minuit passé sans session)."""
    day = today if today in days else today - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count
