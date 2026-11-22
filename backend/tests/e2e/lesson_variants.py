"""Recette locale de l'édition multiformat à partir d'une leçon fictive publiée."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.lesson_variants.support import seed_lesson


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8903)
    parser.add_argument("--origin", default="http://127.0.0.1:5303")
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            await seed_lesson(current)
            yield

    app.router.lifespan_context = lifespan
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
