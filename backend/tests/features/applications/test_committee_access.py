"""Accès au comité de recrutement (D147) : isolation entre utilisatrices, connexion exigée,
journaux sans donnée personnelle."""

import logging

import httpx
import pytest
from fastapi import FastAPI

from tests.features.applications.committee_support import (
    ROOT,
    UNKNOWN,
    committee_store,
    launch,
    ready_committee,
    save_done,
    spy,
    synthesis_of,
    votes_of,
)
from tests.sessions_support import act_as

pytestmark = pytest.mark.usefixtures("client")


async def test_other_user_gets_404(client: httpx.AsyncClient, app: FastAPI) -> None:
    posting, version = await ready_committee(client, app)
    started = await launch(client, version)
    act_as(app, "autre-utilisatrice")
    get = await client.get(f"{ROOT}/committee/{started['run_id']}")
    assert (get.status_code, get.json()["error"]["code"]) == (404, "committee_not_found")
    assert (await client.get(f"{ROOT}/committee")).json() == []
    assert (await client.get(f"{ROOT}/committee", params={"posting_id": posting})).json() == []
    post = await client.post(f"{ROOT}/committee", json={"cv_version_id": version})
    assert (post.status_code, post.json()["error"]["code"]) == (404, "version_not_found")
    assert spy(app).started == [("hiring_committee", {"run_id": started["run_id"]})]


async def test_unknown_run_404(client: httpx.AsyncClient) -> None:
    r = await client.get(f"{ROOT}/committee/{UNKNOWN}")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "committee_not_found")


async def test_needs_a_user(client_google_mode: httpx.AsyncClient) -> None:
    for method, url in (
        ("POST", f"{ROOT}/committee"),
        ("GET", f"{ROOT}/committee"),
        ("GET", f"{ROOT}/committee/x"),
    ):
        r = await client_google_mode.request(method, url, json={"cv_version_id": "x"})
        assert r.status_code == 401, url


async def test_committee_never_logged(
    caplog: pytest.LogCaptureFixture, client: httpx.AsyncClient, app: FastAPI
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    secrets = ("Entreprise Ultra Secrète", "Objection ultra secrète", "Raison ultra secrète")
    posting, version = await ready_committee(client, app, company=secrets[0])
    started = await launch(client, version)
    await client.post(f"{ROOT}/committee", json={"cv_version_id": version})  # 409
    await client.post(f"{ROOT}/committee", json={})  # 422
    user = str(app.state.local_user_id)
    await committee_store(app).context(user, started["run_id"])
    votes = votes_of("yes", "no", "no", "yes", objection=secrets[1])
    for vote in votes:
        vote.reason = secrets[2]
    await save_done(app, started, votes, synthesis_of("maybe", secrets[1]))
    await spy(app).end(user, started["session_id"])
    await client.get(f"{ROOT}/committee", params={"posting_id": posting})
    await client.get(f"{ROOT}/committee/{started['run_id']}")
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for secret in (*secrets, "LangGraph", "AI Engineer Python", "Offre : agents"):
        assert secret not in logged, secret
    assert started["run_id"] in logged
