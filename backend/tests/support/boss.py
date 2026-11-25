"""Generated program and answers for the Boss flows."""

import json

from fastapi import FastAPI

from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, add_goal, sample_plan

OUTPUT = json.dumps(
    {
        "checks": [
            {"ordered": ids, "intact": True}
            for ids in ([], ["D-2", "D-1"], ["D-3", "D-4", "D-5"], ["D-7", "D-8", "D-6", "D-9"])
        ]
    }
)
CORRECTION = """def schedule(requests):
    return [r["id"] for r in sorted(requests, key=lambda r: not r["urgent"])]
"""
RUBRIC = json.dumps(
    {
        "readability": {"score": 4, "feedback": "Stable sort and readable expression."},
        "maintenance": {"score": 4, "feedback": "Isolate the priority in a focused function."},
    }
)


async def completed_program(app: FastAPI, user_id: str | None = None) -> str:
    user_id = user_id or app.state.local_user_id
    factory = app.state.session_factory
    goal = await add_goal(factory, user_id)
    draft = await AgentProgramStore(app.state.program).save_draft(
        user_id,
        "boss-test",
        goal.goal_id,
        sample_plan(),
        revision=0,
        start_date=MONDAY,
        reason="Fake Boss program",
    )
    async with factory() as db:
        rows = await load(db, user_id, draft.program_id)
        rows.program.status = "validated"
        for task in rows.tasks:
            task.status = "done"
        await db.commit()
    return draft.program_id
