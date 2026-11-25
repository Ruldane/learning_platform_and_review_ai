"""Today's block (SPEC F14, D103 #1): the reading and practice tasks due of a module whose lesson is
ready. `todo` tasks dated at most today (January's local day), overdue ones first, excluding quiz
and project, of a non-skipped module of a validated program; the first module in order (date,
rank) gives the block, which gathers all its due tasks. Read-only."""

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
    """Due tasks of this module only (lesson chosen by January); empty if there are none."""
    found = await _block(db, user_id, today, module_id)
    return found.task_ids if found is not None else []
