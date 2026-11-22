"""Recette des relevés de marché et de la simulation, avec une base synthétique."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.future_self.support import ROLE, _run, seed


async def seed_market(app: FastAPI, user_id: str) -> None:
    await seed(app, user_id)
    async with app.state.session_factory() as db:
        db.add(_run(user_id, ROLE, 4, [["Python"], ["RAG"], ["Finance"], ["Docker"]]))
        await db.commit()


def attach_market(app: FastAPI) -> None:
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            await seed_market(current, current.state.local_user_id)
            yield

    app.router.lifespan_context = lifespan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8803)
    parser.add_argument("--origin", default="http://localhost:5203")
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings)
    attach_market(app)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
