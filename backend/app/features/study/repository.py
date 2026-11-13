"""Sessions guidées (D99, D103) et ce que l'étude lit des leçons et du programme : leçon, module,
tâches dues du bloc. Lectures fraîches (`populate_existing`) ; les transitions disputées sont
gardées en SQL (`UPDATE … WHERE status = 'open'`) : deux fins, ou une fin et un abandon, n'en
écrivent qu'une."""

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

BLOCK_TYPES = ("lire", "regarder", "pratiquer")  # hors quiz et projet (D103)


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
        """La session `open` de l'utilisateur (une au plus, index unique partiel)."""
        stmt = (
            select(StudySession)
            .where(StudySession.user_id == self.user_id, StudySession.status == "open")
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def close_open(self, study_id: str, **values: Any) -> bool:
        """Transition depuis `open` (fin ou abandon) ; vrai si c'est cet appel qui l'a faite."""
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

    async def finished(self) -> builtins.list[tuple[datetime, int]]:
        """`(fin, minutes)` de chaque session terminée (série, heures de la semaine)."""
        stmt = select(StudySession.ended_at, StudySession.minutes).where(
            StudySession.user_id == self.user_id,
            StudySession.status == "finished",
            StudySession.ended_at.is_not(None),
        )
        rows = (await self.session.execute(stmt)).all()
        return [(ended, int(minutes)) for ended, minutes in rows if ended is not None]


class StudyReadRepository:
    """Leçons, modules et tâches de l'utilisateur, lus pour l'étude (jamais écrits ici)."""

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def lesson(self, lesson_id: str) -> Lesson | None:
        stmt = (
            select(Lesson)
            .where(Lesson.id == lesson_id, Lesson.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def module(self, module_id: str) -> Module | None:
        stmt = select(Module).where(Module.id == module_id, Module.user_id == self.user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def titles(self, lesson_id: str, module_id: str) -> tuple[str, str]:
        """`(titre de la leçon, titre du module)` ; vides s'ils ont disparu."""
        lesson = await self.lesson(lesson_id)
        module = await self.module(module_id)
        return (lesson.title if lesson else "", module.title if module else "")

    async def due_tasks(
        self, today: date, module_id: str | None = None
    ) -> builtins.list[tuple[Task, Lesson]]:
        """Tâches `todo` de lecture ou de pratique datées au plus `today`, d'un module non sauté
        d'un programme validé dont la leçon est prête (`module_id` : ce module seul), avec leur
        leçon ; les plus anciennes d'abord, puis par rang de module et de tâche."""
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
