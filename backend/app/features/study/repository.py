"""Guided sessions (D99, D103) and what study reads of lessons and of the program: lesson, module,
the block's due tasks. Fresh reads (`populate_existing`); contested transitions are guarded in
SQL (`UPDATE … WHERE status = 'open'`): two endings, or an ending and an abandonment, write only
one."""

import builtins
from collections.abc import Collection
from datetime import date, datetime
from typing import Any

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.lessons import Lesson
from app.db.models.program import Module, Program, Task
from app.db.models.study import StudySession
from app.db.repository import UserScopedRepository

BLOCK_TYPES = ("read", "watch", "practice")  # outside quiz and project (D103)


class StudyRepository(UserScopedRepository[StudySession]):
    model = StudySession

    async def get_fresh(self, study_id: str) -> StudySession | None:
        stmt = (
            select(StudySession)
            .where(StudySession.id == study_id, StudySession.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def open_one(self) -> StudySession | None:
        """The user's `open` session (at most one, partial unique index)."""
        stmt = (
            select(StudySession)
            .where(
                StudySession.user_id == self.user_id,
                StudySession.status == "open",
                StudySession.independent.is_(False),
            )
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def recent_independent_training(self) -> StudySession | None:
        return await self.session.scalar(
            select(StudySession)
            .where(
                StudySession.user_id == self.user_id,
                StudySession.kind == "training",
                StudySession.status == "open",
                StudySession.independent.is_(True),
            )
            .order_by(StudySession.created_at.desc(), StudySession.id.desc())
            .limit(1)
        )

    async def close_open(self, study_id: str, **values: Any) -> bool:
        """Transition from `open` (end or abandonment); true if this call made it."""
        stmt = (
            update(StudySession)
            .where(
                StudySession.id == study_id,
                StudySession.user_id == self.user_id,
                StudySession.status == "open",
            )
            .values(**values)
        )
        result = await self.session.execute(stmt)
        return isinstance(result, CursorResult) and result.rowcount == 1

    async def claim_training(
        self, study_id: str, *, include_closed: bool = False
    ) -> StudySession | None:
        """Reserves the sitting before a change of context or a state transition."""
        stmt = update(StudySession).where(
            StudySession.user_id == self.user_id,
            StudySession.id == study_id,
            StudySession.kind == "training",
        )
        if not include_closed:
            stmt = stmt.where(StudySession.status == "open")
        return await self.session.scalar(
            stmt.values(updated_at=StudySession.updated_at).returning(StudySession)
        )

    async def finished(self) -> builtins.list[tuple[datetime, int]]:
        """`(end, minutes)` of each finished session (streak, hours of the week)."""
        stmt = select(StudySession.ended_at, StudySession.minutes).where(
            StudySession.user_id == self.user_id,
            StudySession.status == "finished",
            StudySession.ended_at.is_not(None),
        )
        rows = (await self.session.execute(stmt)).all()
        return [(ended, int(minutes)) for ended, minutes in rows if ended is not None]


class StudyReadRepository:
    """The user's lessons, modules and tasks, read for study (never written here)."""

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def lesson(self, lesson_id: str | None) -> Lesson | None:
        stmt = (
            select(Lesson)
            .where(Lesson.id == lesson_id, Lesson.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def module(self, module_id: str | None) -> Module | None:
        stmt = select(Module).where(Module.id == module_id, Module.user_id == self.user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def titles(self, lesson_id: str | None, module_id: str | None) -> tuple[str, str]:
        """`(lesson title, module title)`; empty if they have disappeared."""
        lesson = await self.lesson(lesson_id)
        module = await self.module(module_id)
        return (lesson.title if lesson else "", module.title if module else "")

    async def due_tasks(
        self, today: date, module_id: str | None = None
    ) -> builtins.list[tuple[Task, Lesson]]:
        """Reading or practice `todo` tasks dated at most `today`, from a non-skipped module of a
        validated program whose lesson is ready (`module_id`: that module only), with their lesson;
        oldest first, then by module and task rank."""
        stmt = (
            select(Task, Lesson)
            .join(Module, Module.id == Task.module_id)
            .join(Program, Program.id == Task.program_id)
            .join(Lesson, Lesson.module_id == Task.module_id)
            .where(
                Task.user_id == self.user_id,
                Task.status == "todo",
                Task.type.in_(BLOCK_TYPES),
                Task.planned_date <= today,
                Module.skipped.is_(False),
                Program.user_id == self.user_id,
                Program.status == "validated",
                Lesson.user_id == self.user_id,
                Lesson.status == "ready",
            )
            .order_by(Task.planned_date, Module.rank, Task.rank)
            .execution_options(populate_existing=True)
        )
        if module_id is not None:
            stmt = stmt.where(Task.module_id == module_id)
        rows = (await self.session.execute(stmt)).all()
        return [(task, lesson) for task, lesson in rows]

    async def tasks(self, task_ids: Collection[str]) -> builtins.list[Task]:
        if not task_ids:
            return []
        stmt = select(Task).where(
            Task.user_id == self.user_id, Task.id.in_(builtins.list(task_ids))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())
