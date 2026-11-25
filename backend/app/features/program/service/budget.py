"""Time budget of a week (SPEC 3.4): five days, a block on Saturday, Sunday free."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

# Share of the budget that the planned load never exceeds (SPEC 3.4, 13).
CAP_PERCENT = 85
SATURDAY = 5


class AvailabilityLike(Protocol):
    """What the budget reads from availabilities (`features.settings.schemas.Availability`).

    A feature imports from another only its service (contract 2): the type is described here.
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
        """Five weekdays plus Saturday."""
        return 5 * self.weekday_minutes + self.weekend_minutes

    @property
    def cap_minutes(self) -> int:
        """85% of the weekly budget, rounded down (integers: no floating-point error)."""
        return self.weekly_minutes * CAP_PERCENT // 100

    def _usual_capacity(self, day: date) -> int:
        weekday = day.weekday()
        if weekday < SATURDAY:
            return self.weekday_minutes
        return self.weekend_minutes if weekday == SATURDAY else 0

    def day_capacity(self, day: date) -> int:
        """Budget of the day, capped by the known availabilities."""
        planned = self._usual_capacity(day)
        return min(planned, self.daily_caps.get(day, planned))


def budget_for(availability: AvailabilityLike, goal_weekly_minutes: int | None) -> Budget:
    """Availability budget, scaled to the time the goal asks for, if it has a figure."""
    weekday = availability.weekday_minutes
    weekend = availability.weekend_block_max_minutes
    full = availability.weekly_budget_minutes
    if goal_weekly_minutes is None or full <= 0:
        return Budget(weekday, weekend)
    return Budget(weekday * goal_weekly_minutes // full, weekend * goal_weekly_minutes // full)
