"""Fiche et brief fictifs pour la recette PWA."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.db.models.study import Flashcard
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir

FRONT = "Quel outil traite ce jeu de données fictif ?"
BACK = "Un script Python."


async def seed_card(app: FastAPI) -> None:
    owner = app.state.local_user_id
    async with app.state.session_factory() as db:
        today = await app.state.quiz.today(db, owner)
        db.add(
            Flashcard(
                user_id=owner,
                front=FRONT,
                back=BACK,
                front_hash="mobile-example",
                source="capture",
                step=0,
                due_date=today,
            )
        )
        await db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8816)
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin="http://localhost:5216", port=args.port)
    migrate(settings)
    app = build_app(settings)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            await seed_card(current)
            yield

    app.router.lifespan_context = lifespan
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
