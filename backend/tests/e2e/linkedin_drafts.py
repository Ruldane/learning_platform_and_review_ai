"""Profil fictif et rédaction scriptée pour vérifier la relecture et la copie."""

import argparse
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.agents.tools.cv_schema import (
    Identity,
    MasterProfileData,
    SkillFact,
    SourcedLine,
    assign_fact_ids,
)
from app.db.models.career import MasterProfile
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir

SUMMARY = "Je développe des scripts Python."
EDIT = {"headline": "Python", "about": SUMMARY, "skills": ["Python"]}
SCRIPT = {**EDIT, "about": SUMMARY + " J’ai livré 900 projets."}


async def seed_profile(app: FastAPI, user_id: str) -> None:
    profile = assign_fact_ids(
        MasterProfileData(
            identity=Identity(name="Personne fictive"),
            title=SourcedLine(text="Python", sources=["january"]),
            summary=SourcedLine(text=SUMMARY, sources=["january"]),
            skills=[SkillFact(name="Python")],
        )
    )
    async with app.state.session_factory() as db:
        db.add(
            MasterProfile(
                user_id=user_id,
                version=1,
                status="validated",
                source="january",
                data=profile.model_dump(mode="json"),
            )
        )
        await db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8814)
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin="http://localhost:5214", port=args.port)
    migrate(settings)
    app = build_app(settings, scripts={"recruiter": [json.dumps(SCRIPT, ensure_ascii=False)]})
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            await seed_profile(current, current.state.local_user_id)
            yield

    app.router.lifespan_context = lifespan
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
