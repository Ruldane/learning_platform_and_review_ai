from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.lessons import Resource
from app.db.models.skills import UserSkill
from app.features.program.service.programs import load
from app.providers.github.base import GithubIssue, GithubPull, RepoRef
from tests.features.program.conftest import Draft
from tests.sessions_support import act_as

API = "/api/v1/contributions"
REPO = RepoRef("orga-fictive", "bibliotheque")
BODY = {"author": "camille", "head": "fix/tests", "title": "Tests", "body": "Ajout de cas"}


class GithubDouble:
    def __init__(self) -> None:
        self.pr = GithubPull(12, "camille", "main", "fix/tests", "", False)
        self.requests = 0

    async def open_issues(self, repo: RepoRef) -> tuple[GithubIssue, ...]:
        assert repo == REPO
        return (GithubIssue(7, "Tests pandas", "Cas limites", ("good first issue",)),)

    async def default_branch(self, repo: RepoRef) -> str:
        assert repo == REPO
        return "main"

    async def pull(self, repo: RepoRef, number: int) -> GithubPull:
        assert repo == REPO and number == 12
        self.requests += 1
        return self.pr


async def seed(app: FastAPI, program: Draft) -> GithubDouble:
    github = GithubDouble()
    app.state.contributions = replace(app.state.contributions, github=github)
    async with app.state.session_factory() as db:
        source = await load(db, program.user_id, program.program_id)
        db.add(
            Resource(
                user_id=program.user_id,
                program_id=program.program_id,
                module_id=source.modules[0].id,
                title="Dépôt de préparation",
                type="depot",
                url=f"https://github.com/{REPO.name}",
                url_hash="recette",
            )
        )
        await db.commit()
    return github


async def create(client: httpx.AsyncClient, program: Draft) -> str:
    payload = {"program_id": program.program_id, "repository": REPO.name, "issue_number": 7}
    result = await client.post(API, json=payload)
    assert result.status_code == 201
    assert result.json()["status"] == "draft"
    assert (await client.post(API, json=payload)).json()["id"] == result.json()["id"]
    return f"{API}/{result.json()['id']}"


async def test_contribution_requires_confirmation_and_adds_one_verified_proof(
    client: httpx.AsyncClient, app: FastAPI, draft_program: Draft
) -> None:
    github = await seed(app, draft_program)
    proposed = await client.get(
        f"{API}/suggestions", params={"program_id": draft_program.program_id}
    )
    assert proposed.json()["items"][0]["skills"] == ["pandas"]
    path = await create(client, draft_program)
    pull = {"url": REPO.pull_url(12)}
    assert (await client.post(f"{path}/pull", json=pull)).status_code == 409
    assert (
        await client.post(f"{path}/publication", json={**BODY, "confirm": False})
    ).status_code == 422
    assert (await client.get(path)).json()["publication_url"] is None
    approved = await client.post(f"{path}/publication", json={**BODY, "confirm": True})
    assert approved.json()["status"] == "confirmed"
    assert (await client.post(f"{path}/pull", json=pull)).status_code == 409
    preview_url = approved.json()["publication_url"]
    submitted = parse_qs(urlsplit(preview_url).query)["body"][0]
    github.pr = replace(github.pr, body=submitted)
    assert (await client.post(f"{path}/pull", json=pull)).json()["status"] == "open"

    github.pr = replace(github.pr, merged=True, state="closed")
    accepted = (await client.post(f"{path}/refresh")).json()
    assert accepted["status"] == "accepted"
    assert "Tests pandas" in accepted["cv_line"]
    assert (await client.post(f"{path}/refresh")).json() == accepted
    assert github.requests == 3
    async with app.state.session_factory() as db:
        stmt = select(UserSkill).where(UserSkill.user_id == draft_program.user_id)
        proofs = [
            proof
            for row in await db.scalars(stmt)
            for proof in row.evidence
            if proof.get("kind") == "contribution"
        ]
    assert len(proofs) == 1 and proofs[0]["ref_id"] == accepted["id"]


async def test_another_account_cannot_open_or_publish_a_contribution(
    client: httpx.AsyncClient, app: FastAPI, draft_program: Draft
) -> None:
    github = await seed(app, draft_program)
    path = await create(client, draft_program)
    act_as(app, "autre-compte")
    try:
        assert (await client.get(API)).json() == []
        assert (await client.get(path)).status_code == 404
        assert (
            await client.post(f"{path}/publication", json={**BODY, "confirm": True})
        ).status_code == 404
        assert (
            await client.post(f"{path}/pull", json={"url": REPO.pull_url(12)})
        ).status_code == 404
        assert (await client.post(f"{path}/refresh")).status_code == 404
    finally:
        app.dependency_overrides.clear()
    assert github.requests == 0
