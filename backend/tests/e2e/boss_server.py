"""Serveur de recette du Boss, sur base neuve et fournisseurs factices."""

import argparse
import ast
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.config import Settings
from app.db.base import utcnow
from app.providers.sandbox.base import SandboxJob
from app.providers.sandbox.fake import FakeSandbox
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.support.boss import CORRECTION, OUTPUT, RUBRIC, completed_program

_EXPECTED = ast.dump(ast.parse(CORRECTION))


def _matches_correction(source: str) -> bool:
    try:
        return ast.dump(ast.parse(source)) == _EXPECTED
    except SyntaxError:
        return False


class Clock:
    def __init__(self) -> None:
        self.wall = utcnow()
        self.started: float | None = None

    def __call__(self) -> datetime:
        now = time.monotonic()
        if self.started is None:
            self.started = now
        elapsed = now - self.started
        client_delay = timedelta(minutes=11) if elapsed >= 7 else timedelta()
        return self.wall + timedelta(seconds=elapsed) + client_delay


class BossSandbox(FakeSandbox):
    async def submit(self, job: SandboxJob) -> None:
        if _matches_correction(job.files.get("service.py", "")):
            self._scripted[job.run_id] = OUTPUT
        await super().submit(job)


def fixture_app(settings: Settings) -> FastAPI:
    app = build_app(settings, scripts={"boss_reviewer": [RUBRIC]})
    lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def with_boss(application: FastAPI):
        async with lifespan(application):
            application.state.providers.sandbox = BossSandbox()
            application.state.boss_clock = Clock()
            await completed_program(application)
            yield

    app.router.lifespan_context = with_boss
    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin)
    migrate(settings)
    uvicorn.run(fixture_app(settings), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
