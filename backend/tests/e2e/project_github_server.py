"""Recette locale de l’attribution GitHub, entièrement servie par FakeFetcher."""

import argparse
from pathlib import Path

import uvicorn
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.core.deps import CurrentUserDep
from app.db.models.daily import Project
from tests.agents.graphs.project_support import evaluation_json
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.study.conftest import seed
from tests.support.project_github import github_commit, github_profile
from tests.support.projects import sample_brief
from tests.support.research import FakeFetcher

router = APIRouter(prefix="/__e2e/project-github")


def _fetcher(request: Request) -> FakeFetcher:
    fetcher = request.app.state.injected_research_providers.fetcher
    assert isinstance(fetcher, FakeFetcher)
    return fetcher


@router.post("/seed")
async def seed_project(request: Request, user: CurrentUserDep) -> dict[str, str]:
    found = await seed(request.app, user_id=user.id, recording=False)
    async with request.app.state.session_factory() as db:
        project = Project(
            user_id=user.id,
            title="Projet GitHub de recette",
            status="todo",
            program_id=found.program_id,
            module_id=found.modules[0],
            brief=sample_brief().model_dump(mode="json"),
        )
        db.add(project)
        await db.commit()
    github_commit(_fetcher(request))
    return {"project_id": project.id}


class ProfileSimulation(BaseModel):
    code: str = Field(pattern=r"^tremplin:[a-zA-Z0-9_-]{32}$")


@router.post("/profile", status_code=204, response_class=Response)
async def simulate_public_bio(request: Request, command: ProfileSimulation) -> Response:
    github_profile(_fetcher(request), command.code)
    return Response(status_code=204)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    config = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin)
    migrate(config)
    app = build_app(config, scripts={"practitioner": [evaluation_json([True, False, True, True])]})
    app.include_router(router)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
