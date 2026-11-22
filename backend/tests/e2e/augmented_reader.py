"""Article et glossaire synthétiques pour la recette de lecture."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.agents.tools.plan_schema import NotionDraft
from app.db.models.lessons import Lesson
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from app.features.reading_stack.repository import ReadingRepository
from app.features.reading_stack.types import CollectedItem
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.program.support import MONDAY, add_goal, sample_plan

TITLE = "Comprendre les index"
TERM = "Index inversé"
DEFINITION = "Un index qui associe un terme aux documents qui le contiennent."
PASSAGE = "Le terme mène à une liste de documents."


async def seed_glossary(app: FastAPI, user_id: str) -> str:
    factory = app.state.session_factory
    goal = await add_goal(factory, user_id)
    plan = sample_plan()
    plan.weeks[0].modules[0].introduces = [NotionDraft(name=TERM, definition=DEFINITION)]
    saved = await AgentProgramStore(app.state.program).save_draft(
        user_id,
        "glossaire-lecture",
        goal.goal_id,
        plan.with_chapter_indices(),
        revision=0,
        start_date=MONDAY,
        reason="Glossaire de lecture",
    )
    async with factory() as db:
        program = await load(db, user_id, saved.program_id)
        program.program.status = "validated"
        lesson = Lesson(
            user_id=user_id,
            module_id=program.modules[0].id,
            program_id=saved.program_id,
            title=program.modules[0].title,
            status="ready",
            markdown="# Index inversé",
        )
        db.add(lesson)
        await db.commit()
    return lesson.id


async def seed_article(app: FastAPI, user_id: str) -> str:
    async with app.state.session_factory() as db:
        article = await ReadingRepository(db, user_id).record(
            CollectedItem(
                "paper",
                "https://example.org/index",
                TITLE,
                "Un résumé de lecture.",
                f"🔎 Un index inversé facilite la recherche.\n{PASSAGE}",
                "Recherche documentaire",
            ),
            datetime.now(UTC),
        )
        assert article is not None
        await db.commit()
    return article


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8806)
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin="http://localhost:5206", port=args.port)
    migrate(settings)
    app = build_app(settings)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            user = current.state.local_user_id
            await seed_glossary(current, user)
            await seed_article(current, user)
            yield

    app.router.lifespan_context = lifespan
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
