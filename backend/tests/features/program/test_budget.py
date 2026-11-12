from datetime import date

from app.features.program.service.budget import Budget, budget_for
from app.features.settings.schemas import Availability


def test_default_budget_is_840_with_cap_714() -> None:
    b = budget_for(Availability(), None)
    assert (b.weekday_minutes, b.weekend_minutes) == (120, 240)
    assert (b.weekly_minutes, b.cap_minutes) == (840, 714)


def test_goal_hours_scale_the_budget() -> None:
    b = budget_for(Availability(), 420)
    assert (b.weekday_minutes, b.weekend_minutes, b.cap_minutes) == (60, 120, 357)


def test_goal_scaling_rounds_down() -> None:
    b = budget_for(Availability(), 100)  # 100 / 840 de 120 et de 240
    assert (b.weekday_minutes, b.weekend_minutes) == (14, 28)


def test_empty_availability_is_not_divided_by_zero() -> None:
    zero = Availability(weekday_minutes=0, weekend_block_min_minutes=0, weekend_block_max_minutes=0)
    assert budget_for(zero, 300) == Budget(0, 0)


def test_sunday_has_no_capacity() -> None:
    b = Budget(120, 240)
    week = [date(2026, 11, 16 + i) for i in range(7)]  # lundi 16 -> dimanche 22
    assert [b.day_capacity(d) for d in week] == [120, 120, 120, 120, 120, 240, 0]


def test_cap_is_exact_for_odd_budgets() -> None:
    assert Budget(45, 95).cap_minutes == 272  # 320 * 85 // 100
