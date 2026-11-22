"""Recette isolée avec une leçon synthétique et les répliques scriptées du Tuteur."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.conversations.test_classroom import FIRST, SECOND
from tests.features.lessons.test_router import seed


def lesson_fixture(app: FastAPI) -> None:
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            await seed(current)
            yield

    app.router.lifespan_context = lifespan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8794)
    parser.add_argument("--origin", default="http://127.0.0.1:5194")
    args = parser.parse_args()
    data_dir = prepare_data_dir(args.data_dir)
    settings = e2e_settings(data_dir, origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings, scripts={"training_tutor": [*FIRST, *SECOND]})
    lesson_fixture(app)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
