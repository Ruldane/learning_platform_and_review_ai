"""Charge journalière, en tenant compte des réservations horaires connues."""

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from app.db.models.program import Task
from app.features.calendar.service.availability import study_windows
from app.features.interprogram_planning.schemas import SharedWeekDay
from app.features.interprogram_planning.sources import DAYS, WeekFacts


def _capacity(facts: WeekFacts, day: date, timed_minutes: int, now: datetime) -> int:
    windows = study_windows(day, facts.zone, [item.period for item in facts.bookings], now)
    largest = max(
        (
            int((slot.end.astimezone(UTC) - slot.start.astimezone(UTC)).total_seconds() // 60)
            for slot in windows
        ),
        default=0,
    )
    return min(facts.budget.day_capacity(day), largest + timed_minutes)


def fixed_days(facts: WeekFacts, fixed: list[Task], now: datetime) -> list[SharedWeekDay]:
    reserved: dict[date, int] = defaultdict(int)
    timed: dict[date, int] = defaultdict(int)
    on_calendar = {
        (item.task_id, item.period.start.astimezone(facts.zone).date())
        for item in facts.bookings
        if item.task_id is not None
    }
    for task in fixed:
        reserved[task.planned_date] += task.minutes
        if (task.id, task.planned_date) in on_calendar:
            timed[task.planned_date] += task.minutes

    days = [facts.week_start + timedelta(days=offset) for offset in range(DAYS)]
    return [
        SharedWeekDay(
            date=day,
            capacity_minutes=_capacity(facts, day, timed[day], now),
            reserved_minutes=reserved[day],
            planned_minutes=0,
        )
        for day in days
    ]
