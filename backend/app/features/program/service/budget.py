"""Budget de temps d'une semaine (SPEC 3.4) : cinq jours, un bloc le samedi, dimanche libre."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

# Part du budget que la charge planifiée ne dépasse jamais (SPEC 3.4, 13).
CAP_PERCENT = 85
SATURDAY = 5


class AvailabilityLike(Protocol):
    """Ce que le budget lit des disponibilités (`features.settings.schemas.Availability`).

    Une feature n'importe d'une autre que son service (contrat 2) : le type est décrit ici.
    """

    @property
    def weekday_minutes(self) -> int: ...

    @property
    def weekend_block_max_minutes(self) -> int: ...

    @property
    def weekly_budget_minutes(self) -> int: ...


@dataclass(frozen=True)
class Budget:
    weekday_minutes: int
    weekend_minutes: int
    daily_caps: Mapping[date, int] = field(default_factory=dict, kw_only=True)

    @property
    def longest_day_minutes(self) -> int:
        return max(self.weekday_minutes, self.weekend_minutes)

    @property
    def weekly_minutes(self) -> int:
        """Cinq jours de semaine plus le samedi."""
        return 5 * self.weekday_minutes + self.weekend_minutes

    @property
    def cap_minutes(self) -> int:
        """85 % du budget hebdomadaire, arrondi par défaut (entiers : pas d'erreur flottante)."""
        return self.weekly_minutes * CAP_PERCENT // 100

    def _usual_capacity(self, day: date) -> int:
        weekday = day.weekday()
        if weekday < SATURDAY:
            return self.weekday_minutes
        return self.weekend_minutes if weekday == SATURDAY else 0

    def day_capacity(self, day: date) -> int:
        """Budget du jour, borné aux disponibilités connues."""
        planned = self._usual_capacity(day)
        return min(planned, self.daily_caps.get(day, planned))


def budget_for(availability: AvailabilityLike, goal_weekly_minutes: int | None) -> Budget:
    """Budget des disponibilités, mis à l'échelle du temps voulu par l'objectif s'il est chiffré."""
    weekday = availability.weekday_minutes
    weekend = availability.weekend_block_max_minutes
    full = availability.weekly_budget_minutes
    if goal_weekly_minutes is None or full <= 0:
        return Budget(weekday, weekend)
    return Budget(weekday * goal_weekly_minutes // full, weekend * goal_weekly_minutes // full)
