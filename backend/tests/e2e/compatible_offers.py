"""Relevé et programme synthétiques pour la recette des alertes compatibles."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.db.models.daily import RadarRun
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.brief.support import posting
from tests.features.study.conftest import seed

TITLE = "Ingénieure recherche documentaire"
SKILL = "Recherche hybride"


async def seed_alert(app: FastAPI, owner: str) -> str:
    async with app.state.session_factory() as db:
        run = RadarRun(
            user_id=owner,
            role="Ingénieure données",
            role_norm="ingenieure donnees",
            zone="France",
            zone_norm="france",
            trigger="schedule",
            status="done",
            finished_at=datetime.now(UTC),
            analyzed=1,
            postings=[posting(1, 85, title=TITLE, skills=[{"name": SKILL, "required": True}])],
        )
        db.add(run)
        await db.commit()
    return run.id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8811)
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin="http://localhost:5211", port=args.port)
    migrate(settings)
    app = build_app(settings)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            await seed(current, recording=False)
            await seed_alert(current, current.state.local_user_id)
            yield

    app.router.lifespan_context = lifespan
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
