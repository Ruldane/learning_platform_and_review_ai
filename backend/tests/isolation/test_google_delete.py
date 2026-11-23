"""9.I (revue 9.B5, M2) : en mode Google, après « Tout supprimer », le témoin de la session close ne
rouvre rien, et l'autre compte reste connecté."""

import asyncio

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.features.account.repository import pending_vector_purges
from app.features.account.schemas import DELETE_CONFIRMATION
from app.main import create_app
from app.providers.vector.base import VectorStoreUnavailable
from app.scheduler.registry import JOBS
from tests.features.auth.support import CAMILLE, DOMINIQUE
from tests.isolation.conftest import Browser
from tests.support.account_delete import vector_count
from tests.support.memory import make_chunk

P = "/api/v1"


async def test_old_cookie_is_refused_after_delete(google_client_factory: Browser) -> None:
    camille = await google_client_factory(CAMILLE)
    dominique = await google_client_factory(DOMINIQUE)
    old_cookies = dict(camille.cookies)
    assert old_cookies and (await camille.get(f"{P}/auth/me")).status_code == 200

    me = (await camille.get(f"{P}/auth/me")).json()["id"]
    r = await camille.post(
        f"{P}/account/delete", json={"confirm": DELETE_CONFIRMATION, "expected_user_id": me}
    )
    assert r.status_code == 204

    camille.cookies.clear()
    for name, value in old_cookies.items():
        camille.cookies.set(name, value)
    assert (await camille.get(f"{P}/auth/me")).status_code == 401
    assert (await dominique.get(f"{P}/auth/me")).status_code == 200


async def test_delete_requires_consent_for_the_current_google_account(
    google_client_factory: Browser,
) -> None:
    camille = await google_client_factory(CAMILLE)
    dominique = await google_client_factory(DOMINIQUE)
    camille_id = (await camille.get(f"{P}/auth/me")).json()["id"]
    body = {"confirm": DELETE_CONFIRMATION}

    missing = await dominique.post(f"{P}/account/delete", json=body)
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "account_identity_required"
    mismatch = await dominique.post(
        f"{P}/account/delete", json=body | {"expected_user_id": camille_id}
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "account_changed"
    assert camille_id not in mismatch.text
    assert "set-cookie" not in mismatch.headers
    assert (await camille.get(f"{P}/auth/me")).status_code == 200
    assert (await dominique.get(f"{P}/auth/me")).status_code == 200


async def test_google_final_vector_purge_survives_restart_and_account_recreation(
    google_app: FastAPI,
    google_client_factory: Browser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camille = await google_client_factory(CAMILLE)
    old_id = (await camille.get(f"{P}/auth/me")).json()["id"]
    index = google_app.state.memory_providers.index
    original = index.delete_user
    started_retry = asyncio.Event()
    calls: list[str] = []

    async def fail_final_pass(user_id: str) -> None:
        calls.append(user_id)
        if len(calls) == 2:
            raise VectorStoreUnavailable()
        await original(user_id)
        if len(calls) == 1:
            await index.index([make_chunk(user_id, "vecteur arrivé après la première purge")])
        else:
            started_retry.set()

    monkeypatch.setattr(index, "delete_user", fail_final_pass)
    response = await camille.post(
        f"{P}/account/delete",
        json={"confirm": DELETE_CONFIRMATION, "expected_user_id": old_id},
    )
    assert response.status_code == 202
    assert (await camille.get(f"{P}/auth/me")).status_code == 401
    assert await vector_count(google_app, old_id) == 1
    assert await _pending(google_app) == [old_id]

    late_chunk = make_chunk(old_id, "écriture préparée avant la suppression")
    await google_app.state.memory.indexer.push(old_id, late_chunk.payload.item_id, [late_chunk])
    assert await vector_count(google_app, old_id) == 1

    recreated = await google_client_factory(CAMILLE)
    new_id = (await recreated.get(f"{P}/auth/me")).json()["id"]
    assert new_id != old_id
    await index.index([make_chunk(new_id, "vecteur du nouveau compte")])

    restarted = _restart_for_purge(google_app, monkeypatch)
    async with LifespanManager(restarted):
        await asyncio.wait_for(started_retry.wait(), timeout=10)
        assert await vector_count(restarted, old_id) == 0
        assert await vector_count(restarted, new_id) == 1
        async with asyncio.timeout(10):
            while await _pending(restarted):
                await asyncio.sleep(0.01)
    assert calls == [old_id, old_id, old_id]


async def _pending(app: FastAPI) -> list[str]:
    async with app.state.session_factory() as db:
        return await pending_vector_purges(db)


def _restart_for_purge(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    job = next(spec for spec in JOBS if spec.name == "account_vector_purges")
    monkeypatch.setattr("app.main.JOBS", [job])
    return create_app(
        app.state.settings.model_copy(update={"scheduler_enabled": True}),
        memory_providers=app.state.injected_memory_providers,
        research_providers=app.state.injected_research_providers,
        publishing_providers=app.state.injected_publishing_providers,
    )
