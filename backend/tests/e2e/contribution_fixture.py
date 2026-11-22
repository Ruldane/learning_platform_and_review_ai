"""Données GitHub fictives du parcours Contributrice open source."""

import json

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.core.deps import CurrentUserDep
from app.db.base import new_id
from app.db.models.lessons import Resource
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, add_goal, sample_plan
from tests.support.research import FakeFetcher

router = APIRouter(prefix="/__e2e/contributions")
REPOSITORY = "orga-fictive/bibliotheque"
REPO_API = f"https://api.github.com/repos/{REPOSITORY}"


class PullSimulation(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    merged: bool


def _mock(request: Request, url: str, payload: object) -> None:
    fetcher = request.app.state.research_providers.fetcher
    assert isinstance(fetcher, FakeFetcher)
    fetcher.files[url] = ("application/json", json.dumps(payload).encode())


@router.post("/seed")
async def seed_contribution(request: Request, current: CurrentUserDep) -> dict[str, str]:
    factory = request.app.state.session_factory
    goal = await add_goal(factory, current.id)
    plan = sample_plan().model_copy(update={"title": "Contribuer avec pandas · recette"})
    draft = await AgentProgramStore(request.app.state.program).save_draft(
        current.id, new_id(), goal.goal_id, plan, revision=0, start_date=MONDAY, reason="Recette"
    )
    async with factory() as db:
        program = await load(db, current.id, draft.program_id)
        db.add(
            Resource(
                user_id=current.id,
                program_id=draft.program_id,
                module_id=program.modules[0].id,
                title="Bibliothèque fictive",
                type="depot",
                url=f"https://github.com/{REPOSITORY}",
                url_hash="recette-contribution",
            )
        )
        await db.commit()
    label = {"name": "good first issue"}
    _mock(request, REPO_API, {"default_branch": "main"})
    _mock(
        request,
        f"{REPO_API}/issues?state=open&per_page=50",
        [
            {
                "number": 7,
                "title": "Tests pandas",
                "body": "Ajouter des cas limites.",
                "state": "open",
                "labels": [label],
            },
            {"number": 8, "title": "Tests numpy", "state": "open", "labels": [label]},
        ],
    )
    return {"program_id": draft.program_id}


@router.post("/pull", status_code=204, response_class=Response)
async def simulate_pull(request: Request, payload: PullSimulation) -> Response:
    _mock(
        request,
        f"{REPO_API}/pulls/12",
        {
            "number": 12,
            "user": {"login": "camille"},
            "base": {"ref": "main"},
            "head": {"ref": "fix/tests"},
            "body": payload.body,
            "state": "closed" if payload.merged else "open",
            "merged": payload.merged,
        },
    )
    return Response(status_code=204)
