from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.study_return import StudyReturn
from app.features.postings.service.runtime import KeyLocks
from app.features.quiz.service.runtime import QuizRuntime
from app.features.study.service.runtime import StudyRuntime
from app.features.study.service.training import start_direct_training
from app.features.study_return import repository, selection
from app.features.study_return.schemas import StudyReturnOut, StudyReturnPlan, StudyReturnSelection


@dataclass
class StudyReturnRuntime:
    study: StudyRuntime
    quiz: QuizRuntime
    locks: KeyLocks = field(default_factory=KeyLocks)


def _view(row: StudyReturn | None, today: date) -> StudyReturnOut:
    if row is None:
        return StudyReturnOut(plan=None, reminder_on=None, reminder_due=False)
    plan = None
    if row.selection is not None and row.prepared_at is not None:
        selected = StudyReturnSelection.model_validate(row.selection)
        plan = StudyReturnPlan(
            **selected.model_dump(),
            id=row.id,
            prepared_at=row.prepared_at,
            training_id=row.training_id,
        )
    return StudyReturnOut(
        plan=plan,
        reminder_on=row.reminder_on,
        reminder_due=row.reminder_on is not None and row.reminder_on <= today,
    )


async def get(rt: StudyReturnRuntime, db: AsyncSession, user_id: str) -> StudyReturnOut:
    return _view(await repository.current(db, user_id), await rt.quiz.today(db, user_id))


async def _get_or_add(db: AsyncSession, user_id: str) -> StudyReturn:
    row = await repository.current(db, user_id)
    if row is None:
        row = StudyReturn(user_id=user_id)
        db.add(row)
    return row


async def prepare(rt: StudyReturnRuntime, user_id: str) -> StudyReturnOut:
    async with rt.locks.get(user_id, "return"), rt.study.session_factory() as db:
        row = await _get_or_add(db, user_id)
        selected = (await selection.choose(db, user_id, rt.quiz)).model_dump(mode="json")
        previously_closed = row.training_id is not None and not await repository.training_open(
            db, user_id, row.training_id
        )
        if row.selection != selected or previously_closed:
            row.selection = selected
            row.prepared_at = rt.study.now()
            row.training_id = None
        await db.commit()
        return _view(row, await rt.quiz.today(db, user_id))


async def set_reminder(rt: StudyReturnRuntime, user_id: str, day: date | None) -> StudyReturnOut:
    async with rt.locks.get(user_id, "return"), rt.study.session_factory() as db:
        row = await _get_or_add(db, user_id)
        row.reminder_on = day
        await db.commit()
        return _view(row, await rt.quiz.today(db, user_id))


def _plan_required() -> AppError:
    return AppError("study_return_not_prepared", "Prépare ton bloc de reprise d’abord.", 409)


async def link_training(db: AsyncSession, user_id: str, training_id: str) -> None:
    row = await repository.current(db, user_id)
    if row is None or row.selection is None:
        raise _plan_required()
    row.training_id = training_id
    row.reminder_on = None


async def start(rt: StudyReturnRuntime, user_id: str) -> StudyReturnOut:
    async with rt.locks.get(user_id, "return"):
        async with rt.study.session_factory() as db:
            row = await repository.current(db, user_id)
            if row is None or row.selection is None:
                raise _plan_required()
            if row.training_id is not None:
                return _view(row, await rt.quiz.today(db, user_id))

        async def save_link(db: AsyncSession, training_id: str) -> None:
            await link_training(db, user_id, training_id)

        await start_direct_training(rt.study, user_id, save_link)
        async with rt.study.session_factory() as db:
            return await get(rt, db, user_id)
