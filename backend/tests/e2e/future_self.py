"""Serveur de recette isolé pour la projection avec études, radar et leçon synthétiques."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from pytest import MonkeyPatch

from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.future_self.support import freeze_clock, seed


def seed_projection(app: FastAPI) -> None:
    default_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        with MonkeyPatch.context() as monkeypatch:
            freeze_clock(monkeypatch)
            async with default_lifespan(current):
                await seed(current, current.state.local_user_id)
                yield

    app.router.lifespan_context = lifespan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8786)
    parser.add_argument("--origin", default="http://127.0.0.1:5186")
    args = parser.parse_args()
    data_dir = prepare_data_dir(args.data_dir)
    settings = e2e_settings(data_dir, origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings)
    seed_projection(app)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
