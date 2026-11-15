"""Accès aux entretiens blancs (D146) : isolation entre utilisatrices, connexion exigée, journaux
sans donnée personnelle."""

import logging

import httpx
import pytest
from fastapi import FastAPI

from tests.features.applications.interview_support import (
    BODY,
    ROOT,
    SECRET_ANSWER,
    SECRET_QUESTION,
    exchange,
    interview_store,
    launch,
    ready_application,
    running_application,
    save_done,
    spy,
)
from tests.sessions_support import act_as

pytestmark = pytest.mark.usefixtures("client")


async def test_other_user_gets_404(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id, started = await running_application(client, app)
    act_as(app, "autre-utilisatrice")
    get = await client.get(f"{ROOT}/interviews/{started['interview_id']}")
    assert (get.status_code, get.json()["error"]["code"]) == (404, "interview_not_found")
    assert (await client.get(f"{ROOT}/interviews")).json() == []
    listed = await client.get(f"{ROOT}/interviews", params={"application_id": application_id})
    assert (listed.status_code, listed.json()["error"]["code"]) == (404, "application_not_found")
    post = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    assert (post.status_code, post.json()["error"]["code"]) == (404, "application_not_found")


async def test_needs_a_user(client_google_mode: httpx.AsyncClient) -> None:
    for method, url in (
        ("POST", f"{ROOT}/applications/x/interviews"),
        ("POST", f"{ROOT}/interviews"),
        ("GET", f"{ROOT}/interviews"),
        ("GET", f"{ROOT}/interviews/x"),
    ):
        r = await client_google_mode.request(method, url, json=BODY)
        assert r.status_code == 401, url


async def test_interview_never_logged(
    caplog: pytest.LogCaptureFixture, client: httpx.AsyncClient, app: FastAPI
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    launcher = spy(app)
    secrets = ("Entreprise Ultra Secrète", "Intitulé Ultra Secret", "Contact Ultra Secret")
    application_id = await ready_application(
        client,
        app,
        company=secrets[0],
        title=secrets[1],
        contacts=[{"name": secrets[2], "url": "https://ultra-secret.example.org/c"}],
        url="https://ultra-secret.example.org/offre",
    )
    started = await launch(client, application_id)
    await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)  # 409
    await client.post(f"{ROOT}/interviews", json=BODY)  # 422
    user = str(app.state.local_user_id)
    await interview_store(app).context(user, started["interview_id"])
    await save_done(
        app,
        started,
        exchanges=[
            exchange(0, 2, question=SECRET_QUESTION, answer=SECRET_ANSWER),
            exchange(1, 4, answer=SECRET_ANSWER),
        ],
        flags=["Terme ultra secret"],
    )
    await launcher.end(user, started["session_id"])
    await client.get(f"{ROOT}/interviews")
    await client.get(f"{ROOT}/interviews/{started['interview_id']}")
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for secret in (
        *secrets,
        SECRET_ANSWER,
        SECRET_QUESTION,
        "ultra-secret",
        "Terme ultra",
        "Point",
    ):
        assert secret not in logged, secret
    assert started["interview_id"] in logged
