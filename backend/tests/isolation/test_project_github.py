import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from app.db.models.daily import Project
from tests.features.study.conftest import seed
from tests.sessions_support import act_as
from tests.support.project_github import REPO_URL, SHA, github_commit
from tests.support.projects import sample_brief
from tests.support.research import FakeFetcher


async def test_github_claim_cannot_be_read_or_used_by_another_account(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    seeded = await seed(app, recording=False)
    other = "autre-compte-github"
    async with app.state.session_factory() as db:
        row = Project(
            user_id=seeded.user_id,
            module_id=seeded.modules[0],
            program_id=seeded.program_id,
            status="todo",
            title="Projet fictif",
            brief=sample_brief().model_dump(mode="json"),
        )
        db.add_all([row, User(id=other, user_id=other)])
        await db.commit()
    path = f"/api/v1/projects/{row.id}"
    fetcher = app.state.research_providers.fetcher
    assert isinstance(fetcher, FakeFetcher)
    github_commit(fetcher)
    body = {"repo_url": REPO_URL, "sha": SHA}
    claim = await client.post(f"{path}/github-claims", json=body)
    assert claim.status_code == 201
    calls = len(fetcher.calls)
    act_as(app, other)
    assert (await client.get(f"{path}/github-claims")).status_code == 404
    assert (await client.post(f"{path}/github-claims", json=body)).status_code == 404
    replay = await client.post(f"{path}/submit", data={"github_claim_id": claim.json()["id"]})
    assert replay.status_code == 404
    assert len(fetcher.calls) == calls
