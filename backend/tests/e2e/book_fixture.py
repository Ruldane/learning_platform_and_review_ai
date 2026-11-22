"""Données du parcours Ton livre. Ces routes n'existent que sur le serveur de recette."""

from fastapi import APIRouter, Request

from app.core.deps import CurrentUserDep
from app.db.base import new_id
from app.db.models.lessons import Lesson
from app.features.book.service.refresh import refresh_books
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, add_goal, sample_plan

router = APIRouter(prefix="/__e2e/book")


@router.post("/seed")
async def seed_book(request: Request, current: CurrentUserDep) -> dict[str, str]:
    factory = request.app.state.session_factory
    rows = await add_goal(factory, current.id)
    plan = sample_plan().model_copy(update={"title": "Python, le livre de recette"})
    draft = await AgentProgramStore(request.app.state.program).save_draft(
        current.id, new_id(), rows.goal_id, plan, revision=0, start_date=MONDAY, reason="Recette"
    )
    async with factory() as db:
        loaded = await load(db, current.id, draft.program_id)
        db.add(
            Lesson(
                user_id=current.id,
                program_id=draft.program_id,
                module_id=loaded.modules[0].id,
                title="Première boucle",
                markdown="## Explication\n\nUne boucle répète un bloc.\n",
                status="ready",
            )
        )
        await db.commit()
    return {"program_id": draft.program_id}


@router.post("/refresh", status_code=204)
async def refresh(request: Request) -> None:
    await refresh_books(request.app.state.book)
