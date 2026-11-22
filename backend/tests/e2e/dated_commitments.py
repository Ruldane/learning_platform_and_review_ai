"""Serveur local de recette, avec l’horloge métier avancée par le test."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from pytest import MonkeyPatch

from app.features.dated_commitments import service
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir


def install_clock(app: FastAPI) -> None:
    current_time = datetime(2030, 1, 7, 10, tzinfo=UTC)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(active: FastAPI) -> AsyncIterator[None]:
        with MonkeyPatch.context() as patch:
            patch.setattr(service, "utcnow", lambda: current_time)
            async with original(active):
                yield

    app.router.lifespan_context = lifespan

    @app.post("/__e2e/dated-commitments/advance")
    async def advance() -> dict[str, str]:
        nonlocal current_time
        current_time += timedelta(days=1)
        return {"now": current_time.isoformat()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8937)
    parser.add_argument("--origin", default="http://127.0.0.1:5337")
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings)
    install_clock(app)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
