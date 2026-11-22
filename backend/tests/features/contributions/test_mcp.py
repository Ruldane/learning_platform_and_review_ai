"""Les sorties GitHub et les gestes de niveau 3 passent par le vrai adaptateur MCP."""

from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi import FastAPI

from tests.features.contributions.test_routes import API, BODY, REPO, create, seed
from tests.features.program.conftest import Draft
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp

CONFIRMATIONS = "/api/v1/mcp/confirmations"


@pytest.fixture
def mcp(client: httpx.AsyncClient) -> Mcp:
    client.headers["Host"] = "localhost"
    return Mcp(client)


async def test_contribution_tools_fence_github_text_and_urls(
    client: httpx.AsyncClient, app: FastAPI, draft_program: Draft, mcp: Mcp
) -> None:
    await seed(app, draft_program)
    token = await mcp.token(("contributions",))
    path = await create(client, draft_program)
    program = {"program_id": draft_program.program_id}
    found, failed = await call(mcp, token, "contributions_list_suggestions", program)
    assert not failed, found
    issue_fields = {"title": "Tests pandas", "body": "Cas limites", "url": REPO.issue_url(7)}
    assert all(
        found["data"]["items"][0][name] == f"<donnee_non_fiable>{value}</donnee_non_fiable>"
        for name, value in issue_fields.items()
    )
    params = {"contribution_id": path.rsplit("/", 1)[-1]}
    for tool, args in [
        ("contributions_read_dossier", params),
        ("contributions_list_dossiers", {}),
    ]:
        found, failed = await call(mcp, token, tool, args)
        assert not failed, found
        data = found["data"]
        dossier = data[0] if isinstance(data, list) else data
        for name in issue_fields:
            assert dossier["issue"][name] == (
                f"<donnee_non_fiable>{issue_fields[name]}</donnee_non_fiable>"
            )


async def test_mcp_contribution_changes_wait_for_each_confirmation(
    client: httpx.AsyncClient, app: FastAPI, draft_program: Draft, mcp: Mcp
) -> None:
    github = await seed(app, draft_program)
    token = await mcp.token(("contributions",), "write")
    draft = {"program_id": draft_program.program_id, "repository": REPO.name, "issue_number": 7}
    new, failed = await call(mcp, token, "contributions_create_dossier", draft)
    assert not failed and new["data"]["status"] == "pending_confirmation", new
    assert (await client.get(API)).json() == []
    confirmation_id = new["data"]["confirmation_id"]
    confirmed = await client.post(f"{CONFIRMATIONS}/{confirmation_id}/confirm")
    assert confirmed.json()["status"] == "confirmed", confirmed.text
    dossier = (await client.get(API)).json()[0]
    path = f"{API}/{dossier['id']}"
    params = {"contribution_id": dossier["id"]}

    approved = await client.post(f"{path}/publication", json={**BODY, "confirm": True})
    link = approved.json()["publication_url"]
    github.pr = replace(github.pr, body=parse_qs(urlsplit(link).query)["body"][0])
    for action, extra, before, after in [
        ("track_pull", {"url": REPO.pull_url(12)}, "confirmed", "open"),
        ("refresh_pull", {}, "open", "accepted"),
    ]:
        result, failed = await call(mcp, token, f"contributions_{action}", {**params, **extra})
        assert not failed and result["data"]["status"] == "pending_confirmation", result
        assert (await client.get(path)).json()["status"] == before
        assert github.requests == (0 if before == "confirmed" else 1)
        confirmation_id = result["data"]["confirmation_id"]
        confirmed = await client.post(f"{CONFIRMATIONS}/{confirmation_id}/confirm")
        assert confirmed.json()["status"] == "confirmed", confirmed.text
        assert (await client.get(path)).json()["status"] == after
        github.pr = replace(github.pr, merged=True, state="closed")
    found, failed = await call(mcp, token, "contributions_read_dossier", params)
    assert not failed, found
    assert found["data"]["pull_url"].startswith("<donnee_non_fiable>")
    assert found["data"]["cv_line"].startswith("<donnee_non_fiable>")
