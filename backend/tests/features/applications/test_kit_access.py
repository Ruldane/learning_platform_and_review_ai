"""Accès au kit (D143) : isolation entre utilisatrices, connexion exigée, journaux sans donnée
personnelle."""

import logging

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete

from app.agents.tools.kit_schema import KIT_KINDS
from app.core.errors import AppError
from app.db.models.career import MasterProfile
from tests.features.applications.conftest import API
from tests.features.applications.kit_support import (
    dossier,
    kit_store,
    ready_application,
    save,
    sources,
    spy,
)
from tests.sessions_support import act_as

pytestmark = pytest.mark.usefixtures("client")


async def test_other_user_kit_404(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app)
    application_id = await ready_application(client, app)
    await save(app, application_id, "letter")
    act_as(app, "autre-utilisatrice")
    urls = (f"{API}/{application_id}/kit", f"{API}/{application_id}/kit.zip")
    for url in urls:
        r = await client.get(url)
        assert (r.status_code, r.json()["error"]["code"]) == (404, "application_not_found")
    post = await client.post(f"{API}/{application_id}/kit")
    assert (post.status_code, post.json()["error"]["code"]) == (404, "application_not_found")
    patch = await client.patch(f"{API}/{application_id}/kit/letter", json={"content": "x"})
    assert (patch.status_code, patch.json()["error"]["code"]) == (404, "application_not_found")
    with pytest.raises(AppError):  # le port : même isolation
        await kit_store(app).save_piece(
            "autre-utilisatrice", "s", application_id, "letter", "ready", "x", {}
        )


async def test_kit_needs_a_user(client_google_mode: httpx.AsyncClient) -> None:
    for method, url in (
        ("POST", f"{API}/x/kit"),
        ("GET", f"{API}/x/kit"),
        ("PATCH", f"{API}/x/kit/letter"),
        ("GET", f"{API}/x/kit.zip"),
    ):
        r = await client_google_mode.request(method, url, json={"content": "x"})
        assert r.status_code == 401, url


async def test_kit_never_logged(
    caplog: pytest.LogCaptureFixture, client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    spy(app)
    secrets = ("Entreprise Ultra Secrète", "Intitulé Ultra Secret", "Contact Ultra Secret")
    piece = "Texte ultra secret de la pièce"
    application_id = await ready_application(
        client,
        app,
        company=secrets[0],
        title=secrets[1],
        contacts=[{"name": secrets[2], "url": "https://ultra-secret.example.org/c"}],
        url="https://ultra-secret.example.org/offre",
    )
    session_id = (await client.post(f"{API}/{application_id}/kit")).json()["session_id"]
    await client.post(f"{API}/{application_id}/kit")  # 409
    store = kit_store(app)
    await store.context(me, application_id)
    for kind in KIT_KINDS:
        meta = {"error": piece, "version_id": "v"} if kind == "pitch" else {"flags": [piece]}
        status = "failed" if kind == "pitch" else "to_check"
        await save(
            app, application_id, kind, session=session_id, status=status, content=piece, meta=meta
        )
    await store.save_dossier(me, session_id, secrets[0], dossier(), sources())
    await client.get(f"{API}/{application_id}/kit")
    await client.patch(
        f"{API}/{application_id}/kit/letter", json={"content": piece + " 5 Kubernetes"}
    )
    zipped = await client.get(f"{API}/{application_id}/kit.zip")
    assert zipped.status_code == 200
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for secret in (*secrets, piece, "ultra-secret", "source-1.example.org", "Kit_", "CV_"):
        assert secret not in logged, secret
    assert application_id in logged and session_id in logged


async def test_patch_speaks_of_the_edit_when_the_profile_is_gone(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    await save(app, application_id, "letter", status="to_check")
    async with app.state.session_factory() as db:
        await db.execute(delete(MasterProfile))
        await db.commit()
    r = await client.patch(f"{API}/{application_id}/kit/letter", json={"content": "Mon texte."})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "profile_required")
    message = r.json()["error"]["message"]
    assert "modification" in message and "kit" not in message.lower()
