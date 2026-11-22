from uuid import uuid4

from fastapi import FastAPI

from app.db.models.lessons import Lesson
from app.db.models.program import Program
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, add_goal, sample_plan


async def add_ready_lesson(
    app: FastAPI, user_id: str, title: str, *, validated: bool = True
) -> str:
    factory = app.state.session_factory
    goal = await add_goal(factory, user_id)
    plan = await AgentProgramStore(app.state.program).save_draft(
        user_id,
        str(uuid4()),
        goal.goal_id,
        sample_plan(),
        revision=0,
        start_date=MONDAY,
        reason="Premier plan",
    )
    async with factory() as db:
        program = await db.get(Program, plan.program_id)
        assert program is not None
        if validated:
            program.status = "validated"
        module = (await load(db, user_id, plan.program_id)).modules[0]
        lesson = Lesson(
            user_id=user_id,
            module_id=module.id,
            program_id=plan.program_id,
            title=title,
            markdown=title,
            status="ready",
        )
        db.add(lesson)
        await db.commit()
        return lesson.id
