"""Agenda de recette en boucle locale, sans fournisseur ni modèle réels."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.providers.calendar.base import Interval
from app.providers.calendar.fake import FakeCalendar
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.e2e.study_script import study_scripts
from tests.features.calendar.support import seed_program
from tests.features.calendar.test_flow import NOW


def configure(app: FastAPI, port: int) -> None:
    app.state.injected_calendar = FakeCalendar(
        [Interval(NOW, NOW + timedelta(hours=14))],
        f"http://127.0.0.1:{port}/api/v1/calendar/callback",
    )
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            current.state.calendar.now = lambda: NOW
            current.state.replan.now = lambda: NOW
            await seed_program(current)
            yield

    app.router.lifespan_context = lifespan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8815)
    parser.add_argument("--origin", default="http://127.0.0.1:5215")
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin, port=args.port)
    settings.frontend_url = args.origin
    migrate(settings)
    app = build_app(settings, scripts=study_scripts())
    configure(app, args.port)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
