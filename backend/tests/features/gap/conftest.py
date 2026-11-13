"""Matériel des tests de l'écart (D122) : celui des offres (lanceur factice, vrai port de l'écart
sur la vraie mémoire) et un programme validé écrit directement en base."""

from datetime import date, timedelta

from app.db.models.program import Module, Program, Task, Week
from tests.features.postings.conftest import (  # noqa: F401  (fixtures partagées)
    fake_reader,
    launcher_spy,
    memory,
    store,
)
from tests.features.program.support import MONDAY, Factory, add_goal


async def add_program(
    factory: Factory,
    user_id: str,
    modules: list[tuple[list[str], int, int, bool]],
    *,
    status: str = "validated",
) -> str:
    """Un programme de trois semaines ; `modules` : `(compétences, semaine du module, semaine de
    sa 1re tâche, sauté)`."""
    goal = await add_goal(factory, user_id)
    async with factory() as db:
        program = Program(
            user_id=user_id, goal_id=goal.goal_id, title="Parcours", status=status,
            start_date=MONDAY, weekly_minutes=600, cap_minutes=510,
        )  # fmt: skip
        db.add(program)
        await db.flush()
        weeks = []
        for rank in (1, 2, 3):
            week = Week(
                user_id=user_id, program_id=program.id, rank=rank, theme=f"S{rank}",
                objective="o", deliverable="d", start_date=MONDAY + timedelta(days=7 * (rank - 1)),
            )  # fmt: skip
            db.add(week)
            weeks.append(week)
        await db.flush()
        for index, (skills, week_rank, task_week, skipped) in enumerate(modules):
            module = Module(
                user_id=user_id, week_id=weeks[week_rank - 1].id, program_id=program.id,
                rank=index, title=f"Module {index}", skills=skills, skipped=skipped,
            )  # fmt: skip
            db.add(module)
            await db.flush()
            day: date = MONDAY + timedelta(days=7 * (task_week - 1) + 1)
            db.add(
                Task(
                    user_id=user_id, module_id=module.id, program_id=program.id, rank=0,
                    title="Lire", type="lire", minutes=30, done_criterion="c", planned_date=day,
                )
            )  # fmt: skip
        await db.commit()
        return program.id
