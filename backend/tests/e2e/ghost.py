"""Serveur local du fantôme, avec des tentatives synthétiques et le vrai quiz."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.db.models.study import QuizAttempt
from app.features.capture.service.journal import JournalLinks, add_entry
from app.features.quiz.repository import QuestionRepository
from app.features.quiz.service.ghost import question_version
from app.providers.sandbox.fake import FakeSandbox
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.e2e.study_script import study_scripts
from tests.features.quiz.conftest import seed
from tests.features.quiz.support import ready_quiz

OLD_ANSWER = "Texte historique synthétique à garder masqué."


async def _seed_attempts(app: FastAPI) -> None:
    launcher = app.state.quiz.launcher
    seeded = await seed(app)
    quiz_id = await ready_quiz(seeded)
    app.state.quiz.launcher = launcher
    async with seeded.rt.session_factory() as db:
        questions = await QuestionRepository(db, seeded.user_id).for_quiz(quiz_id)
        for day, version in ((15, None), (16, question_version(questions))):
            at = datetime(2026, 11, day, 8, tzinfo=UTC)
            row = QuizAttempt(
                user_id=seeded.user_id,
                quiz_id=quiz_id,
                status="graded",
                score=90,
                created_at=at,
                graded_at=at,
                question_version=version,
                elapsed_ms=71_000 if version else None,
                answers=[
                    {"question_id": q.id, "choice": None, "text": OLD_ANSWER} for q in questions
                ],
                results=[
                    {"question_id": q.id, "points": float(i != 0), "feedback": OLD_ANSWER}
                    for i, q in enumerate(questions)
                ],
            )
            db.add(row)
            await db.flush()
            await add_entry(
                db,
                seeded.user_id,
                kind="quiz",
                text="Quiz de référence, 90 %.",
                occurred_on=at.date(),
                ref_key=f"quiz:{row.id}",
                links=JournalLinks(quiz_attempt_id=row.id),
                data={"quiz_id": quiz_id, "score": 90, "passed": True},
            )
        await db.commit()


def ghost_fixture(app: FastAPI) -> None:
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            await _seed_attempts(current)
            current.state.providers.sandbox = FakeSandbox({"*": ("Test", " réussi")})
            yield

    app.router.lifespan_context = lifespan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8804)
    parser.add_argument("--origin", default="http://127.0.0.1:5204")
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings, scripts=study_scripts())
    ghost_fixture(app)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
