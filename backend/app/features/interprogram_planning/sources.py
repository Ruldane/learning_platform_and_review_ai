"""The facts of a week, read back from the account and without an external provider."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import user_zone
from app.core.errors import AppError
from app.core.practice import content_version
from app.db.models.calendar import CalendarProposal
from app.db.models.program import Task
from app.features.interprogram_planning import repository
from app.features.program.service.budget import Budget, budget_for
from app.features.program.service.programs import Loaded, load
from app.features.projects.service.views import parse_moment
from app.features.settings.service import SettingsService
from app.providers.calendar.base import Interval

DAYS = 7


@dataclass(frozen=True)
class Booking:
    period: Interval
    task_id: str | None


@dataclass(frozen=True)
class WeekFacts:
    week_start: date
    programs: list[Loaded]
    scheduled: list[Task]
    bookings: list[Booking]
    budget: Budget
    zone: ZoneInfo


def _booking(row: CalendarProposal) -> Booking | None:
    if row.starts_at is None:
        return None
    preview = row.payload.get("preview")
    if not isinstance(preview, dict):
        return None
    end = parse_moment(preview.get("end"))
    if end is None or end <= row.starts_at:
        return None
    selection = row.payload.get("selection")
    task_id = (
        selection.get("source_id")
        if isinstance(selection, dict) and selection.get("kind") == "study"
        else None
    )
    return Booking(Interval(row.starts_at, end), task_id if isinstance(task_id, str) else None)


async def read(
    db: AsyncSession, user_id: str, program_ids: list[str], week_start: date, now: datetime
) -> WeekFacts:
    settings = await SettingsService(db, user_id).get()
    zone = user_zone(settings.timezone)
    today = now.astimezone(zone).date()
    if week_start < today - timedelta(days=today.weekday()):
        raise AppError("shared_week_past", "Choose the current week or an upcoming week.", 409)

    programs = [await load(db, user_id, program_id) for program_id in program_ids]
    if any(item.program.status != "validated" for item in programs):
        raise AppError("shared_week_program_not_validated", "Choose validated programs.", 409)

    end_day = week_start + timedelta(days=DAYS)
    scheduled = await repository.week_tasks(db, user_id, week_start, end_day)
    from_utc = datetime.combine(week_start - timedelta(days=1), time.min, zone).astimezone(UTC)
    to_utc = datetime.combine(end_day, time.min, zone).astimezone(UTC)
    reserved = await repository.bookings(db, user_id, from_utc, to_utc)
    return WeekFacts(
        week_start=week_start,
        programs=programs,
        scheduled=scheduled,
        bookings=[booking for row in reserved if (booking := _booking(row)) is not None],
        budget=budget_for(settings.availability, None),
        zone=zone,
    )


def _task_stamp(task: Task) -> tuple[str, str, str, str, int, str, int, str, str]:
    return (
        task.id,
        task.program_id,
        task.module_id,
        task.planned_date.isoformat(),
        task.minutes,
        task.status,
        task.rank,
        task.title,
        task.type,
    )


def _program_stamp(source: Loaded) -> list[object]:
    return [
        source.program.id,
        source.program.title,
        source.program.version,
        source.program.cap_minutes,
        [(week.id, week.start_date.isoformat()) for week in source.weeks],
        [
            (module.id, module.title, module.prerequisites, module.skills, module.skipped)
            for module in source.modules
        ],
        [_task_stamp(task) for task in source.tasks],
    ]


def fingerprint(facts: WeekFacts) -> str:
    return content_version(
        facts.week_start.isoformat(),
        facts.zone.key,
        facts.budget.weekday_minutes,
        facts.budget.weekend_minutes,
        [_program_stamp(item) for item in facts.programs],
        [_task_stamp(task) for task in facts.scheduled],
        [
            (item.period.start.isoformat(), item.period.end.isoformat(), item.task_id)
            for item in facts.bookings
        ],
    )
