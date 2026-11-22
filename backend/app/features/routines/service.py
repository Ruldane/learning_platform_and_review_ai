from datetime import UTC, date, datetime, timedelta
from typing import assert_never

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import user_zone
from app.core.errors import AppError
from app.db.models.routines import Routine, RoutineAction, RoutineExecution, RoutineSource
from app.features.dated_commitments.service.reminders import CommitmentReminder, due_reminders
from app.features.missions.service import count_ending_missions
from app.features.quiz.service.cards import count_due_cards
from app.features.routines.repository import Executions, Routines
from app.features.routines.schemas import RoutineIn, RoutinePatch
from app.features.settings.service import SettingsService
from app.features.skill_transfer.service import count_due_transfers


async def _local(db: AsyncSession, owner: str, now: datetime) -> datetime:
    preferences = await SettingsService(db, owner).get()
    return now.astimezone(user_zone(preferences.timezone))


def _first_day(local: datetime, hour: str) -> date:
    return local.date() + timedelta(days=int(local.strftime("%H:%M") > hour))


async def _require(repo: Routines, routine_id: str) -> Routine:
    row = await repo.get(routine_id)
    if row is None:
        raise AppError("routine_not_found", "Routine introuvable.", 404)
    return row


async def list_rules(db: AsyncSession, owner: str) -> list[Routine]:
    return await Routines(db, owner).rules()


async def create(db: AsyncSession, owner: str, body: RoutineIn, now: datetime) -> Routine:
    repo = Routines(db, owner)
    await repo.begin_write()
    if await repo.for_action(body.action) is not None:
        raise AppError("routine_exists", "Cette routine existe déjà.", 409)
    local = await _local(db, owner, now)
    return await repo.add(
        action=body.action, local_time=body.local_time, starts_on=_first_day(local, body.local_time)
    )


async def change(
    db: AsyncSession, owner: str, routine_id: str, body: RoutinePatch, now: datetime
) -> Routine:
    repo = Routines(db, owner)
    await repo.begin_write()
    row = await _require(repo, routine_id)
    if (body.local_time is not None and body.local_time != row.local_time) or (
        body.enabled is True and not row.enabled
    ):
        row.local_time = body.local_time or row.local_time
        row.starts_on = _first_day(await _local(db, owner, now), row.local_time)
    if body.enabled is not None:
        row.enabled = body.enabled
    return row


async def history(db: AsyncSession, owner: str, routine_id: str) -> list[RoutineExecution]:
    await _require(Routines(db, owner), routine_id)
    return await Executions(db, owner).recent(routine_id)


async def _evaluate(
    repo: Executions, action: RoutineAction, local: datetime
) -> tuple[int, list[CommitmentReminder]]:
    match action:
        case "due_reviews":
            return await count_due_cards(repo.session, repo.user_id, local.date()), []
        case "due_transfers":
            return await count_due_transfers(repo.session, repo.user_id, local.date()), []
        case "missions_ending":
            return await count_ending_missions(
                repo.session, repo.user_id, local.astimezone(UTC)
            ), []
        case "due_commitments":
            notices = await due_reminders(repo.session, repo.user_id, local.date())
            return len(notices), notices
    assert_never(action)


async def _execute(
    repo: Executions,
    routine: Routine,
    occurrence: str,
    source: RoutineSource,
    local: datetime,
) -> tuple[RoutineExecution, bool]:
    previous = await repo.occurrence(routine.id, occurrence)
    if previous is not None:
        return previous, False
    count, notices = await _evaluate(repo, routine.action, local)
    result = await repo.add(
        routine_id=routine.id,
        occurrence=occurrence,
        source=source,
        result_count=count,
        notices=[item.model_dump(mode="json") for item in notices],
    )
    return result, True


async def execute_now(
    db: AsyncSession, owner: str, routine_id: str, receipt: str, now: datetime
) -> RoutineExecution:
    repo = Routines(db, owner)
    await repo.begin_write()
    routine = await _require(repo, routine_id)
    local = await _local(db, owner, now)
    result, _ = await _execute(Executions(db, owner), routine, f"manual:{receipt}", "manual", local)
    return result


async def run_daily(db: AsyncSession, owner: str, now: datetime) -> int:
    created = 0
    async with db.begin():
        repo = Routines(db, owner)
        await repo.begin_write()
        local = await _local(db, owner, now)
        day = local.date()
        executions = Executions(db, owner)
        for rule in await repo.due(day, local.strftime("%H:%M")):
            _, started = await _execute(executions, rule, f"daily:{day}", "scheduled", local)
            created += started
    return created
