"""Une preuve GitHub exige l’attribution et ne se rejoue qu’une fois."""

from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI

from tests.features.projects.support import API, NOW, Env
from tests.support.project_github import AUTHOR, REPO_URL, SHA, github_commit, github_profile
from tests.support.research import FakeFetcher


@pytest.fixture
def github(app: FastAPI) -> FakeFetcher:
    found = app.state.research_providers.fetcher
    assert isinstance(found, FakeFetcher)
    github_commit(found)
    return found


async def test_github_attribution_and_replay(
    env: Env, github: FakeFetcher, client: httpx.AsyncClient
) -> None:
    project = await env.add_project()
    path = f"{API}/{project}"
    claim = await client.post(f"{path}/github-claims", json={"repo_url": REPO_URL, "sha": SHA})
    assert claim.status_code == 201, claim.text
    values = claim.json()
    assert values["profile_url"] == f"https://github.com/{AUTHOR}"
    body = {"github_claim_id": values["id"]}
    absent = await client.post(f"{path}/submit", data=body)
    assert absent.status_code == 409 and absent.json()["error"]["code"] == "github_code_missing"
    assert (await client.get(f"{path}/github-claims")).json() == []
    assert not await env.levels("pandas")

    github_profile(github, f"Bio de test {values['code']}", identity=7)
    assert (await client.post(f"{path}/submit", data=body)).status_code == 409
    github_profile(github, f"Bio de test {values['code']}")
    submitted = await client.post(f"{path}/submit", data=body)
    assert submitted.status_code == 202, submitted.text

    github_profile(github, "")
    replayed = await client.post(f"{path}/submit", data=body)
    assert replayed.json() == submitted.json() and replayed.status_code == 202
    assert len(env.launcher.started) == 1
    assert len((await env.row(project)).submissions) == 1
    [proof] = (await client.get(f"{path}/github-claims")).json()
    assert proof["commit_url"] == f"{REPO_URL}/commit/{SHA}"
    assert await env.levels("pandas") == {"pandas": ("in_progress", {"github"})}
    graph = (await client.get("/api/v1/skills/graph")).json()
    skill = next(node for node in graph["nodes"] if node["name"] == "pandas")
    [evidence] = (await client.get(f"/api/v1/skills/{skill['id']}")).json()["evidence"]
    assert evidence["kind"] == "github" and evidence["url"] == f"/competences/portfolio/{project}"
    second_project = await env.add_project(1)
    duplicate = await client.post(
        f"{API}/{second_project}/github-claims", json={"repo_url": REPO_URL, "sha": SHA}
    )
    assert (
        duplicate.status_code == 409
        and duplicate.json()["error"]["code"] == "github_commit_claimed"
    )


@pytest.mark.parametrize(
    ("condition", "error"),
    [
        ("public", "github_repo_not_public"),
        ("verified", "github_commit_unverified"),
        ("reachable", "github_commit_outside_branch"),
    ],
)
async def test_rejects_a_commit_without_public_attribution(
    env: Env, github: FakeFetcher, client: httpx.AsyncClient, condition: str, error: str
) -> None:
    project = await env.add_project()
    github_commit(github, **{condition: False})
    response = await client.post(
        f"{API}/{project}/github-claims", json={"repo_url": REPO_URL, "sha": SHA}
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == error
    if condition == "public":
        assert len(github.calls) == 1
    assert not env.launcher.started and not await env.levels("pandas")


async def test_failed_submission_keeps_challenge_and_expiry_discards_it(
    env: Env, github: FakeFetcher, client: httpx.AsyncClient
) -> None:
    project = await env.add_project()
    path = f"{API}/{project}"
    issued = await client.post(f"{path}/github-claims", json={"repo_url": REPO_URL, "sha": SHA})
    claim = issued.json()
    github_profile(github, claim["code"])
    data = {"github_claim_id": claim["id"]}
    env.launcher.refuse = True
    failed = await client.post(f"{path}/submit", data=data)
    assert failed.status_code == 503
    assert (await client.get(f"{path}/github-claims")).json() == []
    assert not await env.levels("pandas") and not (await env.row(project)).submissions

    env.launcher.refuse = False
    env.at(NOW + timedelta(minutes=16))
    expired = await client.post(f"{path}/submit", data=data)
    assert expired.status_code == 409 and expired.json()["error"]["code"] == "github_claim_expired"
    assert not env.launcher.started
