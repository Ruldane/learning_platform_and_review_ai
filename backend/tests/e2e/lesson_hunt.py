"""Recette du Vérificateur sur le vrai graphe et des réponses scriptées."""

import argparse
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.db.models.lessons import Lesson
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.lessons.test_router import seed

SOURCE = "# Module Bases\n\nUn tuple est immuable.\n\nUn ensemble élimine les doublons."
EDITS = [
    {
        "source": "Un tuple est immuable.",
        "replacement": "Un tuple est modifiable.",
        "explanation": "La structure d’un tuple est immuable après sa création.",
    },
    {
        "source": "Un ensemble élimine les doublons.",
        "replacement": "Un ensemble conserve les doublons.",
        "explanation": "Un ensemble ne contient qu’une occurrence de chaque valeur.",
    },
]
FEEDBACK = [
    {"spotted": True, "explained": True, "feedback": "Tu as repéré l’immuabilité du tuple."},
    {"spotted": True, "explained": True, "feedback": "Tu as repéré l’unicité des valeurs."},
]


def lesson_fixture(app: FastAPI) -> None:
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            seeded = await seed(current)
            async with current.state.session_factory() as db:
                row = await db.get(Lesson, seeded.lesson_id)
                assert row is not None
                row.markdown = SOURCE
                await db.commit()
            yield

    app.router.lifespan_context = lifespan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8796)
    parser.add_argument("--origin", default="http://localhost:5196")
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(
        settings,
        scripts={
            "verifier": [
                json.dumps({"edits": EDITS}, ensure_ascii=False),
                json.dumps({"answers": FEEDBACK}, ensure_ascii=False),
            ]
        },
    )
    lesson_fixture(app)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
