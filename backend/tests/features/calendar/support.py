from fastapi import FastAPI

from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, add_goal, sample_plan


async def seed_program(app: FastAPI) -> tuple[str, str]:
    owner = app.state.local_user_id
    factory = app.state.session_factory
    goal = await add_goal(factory, owner)
    saved = await AgentProgramStore(app.state.program).save_draft(
        owner,
        "calendar-fixture",
        goal.goal_id,
        sample_plan(),
        revision=0,
        start_date=MONDAY,
        reason="Agenda de recette",
    )
    async with factory() as db:
        loaded = await load(db, owner, saved.program_id)
        loaded.program.status = "validated"
        task = min(loaded.tasks, key=lambda item: item.planned_date)
        await db.commit()
        return str(saved.program_id), str(task.id)
