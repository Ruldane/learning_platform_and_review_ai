"""Bloc du jour (SPEC F14, D103 n° 1) : les tâches de lecture et de pratique dues d'un module dont
la leçon est prête. Tâches `todo` datées au plus aujourd'hui (jour local de January), retards
d'abord, hors quiz et projet, d'un module non sauté d'un programme validé ; le premier module
dans l'ordre (date, rang) donne le bloc, qui réunit toutes ses tâches dues. Lecture seule."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.lessons import Lesson
from app.features.study.repository import StudyReadRepository
from app.features.study.schemas import BlockOut, BlockTaskOut


@dataclass(frozen=True)
class BlockTask:
    id: str
    title: str
    minutes: int
    type: str


@dataclass(frozen=True)
class Block:
    lesson_id: str
    lesson_title: str
    module_id: str
    module_title: str
    program_id: str
    tasks: list[BlockTask]

    @property
    def task_ids(self) -> list[str]:
        return [task.id for task in self.tasks]

    def out(self) -> BlockOut:
        return BlockOut.model_validate(
            {
                "lesson_id": self.lesson_id,
                "lesson_title": self.lesson_title,
                "module_title": self.module_title,
                "tasks": [BlockTaskOut.model_validate(t.__dict__) for t in self.tasks],
            }
        )


async def _block(
    db: AsyncSession, user_id: str, today: date, module_id: str | None
) -> Block | None:
    reads = StudyReadRepository(db, user_id)
    rows = await reads.due_tasks(today, module_id)
    if not rows:
        return None
    first: Lesson = rows[0][1]
    module = await reads.module(first.module_id)
    tasks = [
        BlockTask(task.id, task.title, task.minutes, task.type)
        for task, lesson in rows
        if lesson.id == first.id
    ]
    return Block(
        lesson_id=first.id,
        lesson_title=first.title,
        module_id=first.module_id,
        module_title=module.title if module is not None else first.title,
        program_id=first.program_id,
        tasks=tasks,
    )


async def block_of_day(db: AsyncSession, user_id: str, today: date) -> Block | None:
    return await _block(db, user_id, today, None)


async def module_block(db: AsyncSession, user_id: str, module_id: str, today: date) -> list[str]:
    """Tâches dues de ce module seul (leçon choisie par January) ; vide s'il n'y en a pas."""
    found = await _block(db, user_id, today, module_id)
    return found.task_ids if found is not None else []
