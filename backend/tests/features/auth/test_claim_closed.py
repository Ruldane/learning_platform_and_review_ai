"""Revue finale 9.R (B-I1) : une fois le premier compte Google créé (reprise ou « Espace vide »), la
reprise de l'espace local est close pour toujours, même si « Tout supprimer » efface ce compte."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.config import Settings
from app.db.models.accounts import UserSettingsRow
from app.features.account.schemas import DELETE_CONFIRMATION
from app.features.auth.repository import UserRepository
from app.features.settings.repository import UserSettingsRepository
from tests.features.auth.claim_support import (
    CLAIM,
    Factory,
    another_browser,
    choose,
    named,
    offered,
    seed_local_space,
    users,
)
from tests.features.auth.support import CAMILLE, DOMINIQUE, FRONT, FakeGoogle, set_cookie, sign_in

ME = "/api/v1/auth/me"


@pytest.fixture
def google_settings(google_settings: Settings) -> Settings:
    return named(google_settings)


async def _delete(client: httpx.AsyncClient) -> None:
    me = (await client.get(ME)).json()["id"]
    r = await client.post(
        "/api/v1/account/delete",
        json={"confirm": DELETE_CONFIRMATION, "expected_user_id": me},
    )
    assert r.status_code == 204, r.text


async def test_claim_is_never_offered_again_after_a_fresh_account_is_deleted(
    google_app: FastAPI,
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: Factory,
) -> None:
    local_id = await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    assert (await choose(google_client, "fresh")).status_code == 200
    await _delete(google_client)
    assert [u.id for u in await users(db_session_factory)] == [local_id]

    # Dominique, nommée dans la liste, ne se voit pas proposer l'espace local de quelqu'un d'autre.
    async with another_browser(google_app) as other:
        back = await sign_in(other, google, DOMINIQUE)
        assert back.headers["location"] == f"{FRONT}/"
        assert set_cookie(back, "tremplin_claim") is None and set_cookie(back, "tremplin_session")
        assert (await other.post(CLAIM, json={"choice": "take_local"})).status_code == 409
        assert (await other.get("/api/v1/goals")).json() == []
    assert all(u.id != local_id or u.google_sub is None for u in await users(db_session_factory))


async def test_camille_is_not_offered_the_claim_again_after_deleting_her_account(
    google_client: httpx.AsyncClient, google: FakeGoogle, db_session_factory: Factory
) -> None:
    await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    assert (await choose(google_client, "fresh")).status_code == 200
    await _delete(google_client)

    back = await sign_in(google_client, google, CAMILLE)
    assert back.headers["location"] == f"{FRONT}/" and set_cookie(back, "tremplin_claim") is None


async def test_attach_identity_refuses_once_the_claim_is_closed(
    google_client: httpx.AsyncClient, google: FakeGoogle, db_session_factory: Factory
) -> None:
    local_id = await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    assert (await choose(google_client, "fresh")).status_code == 200
    await _delete(google_client)  # plus aucun compte Google : seule la mémoire de la reprise reste
    async with db_session_factory() as db:
        repo = UserRepository(db)
        assert not await repo.any_google_user()
        assert await repo.attach_identity(local_id, "sub-x", "x@example.org", "X") is False
        assert await repo.get_local() is not None


async def test_the_memory_survives_the_local_user_saving_settings(
    google_client: httpx.AsyncClient, google: FakeGoogle, db_session_factory: Factory
) -> None:
    local_id = await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    assert (await choose(google_client, "fresh")).status_code == 200
    async with db_session_factory() as db:
        repo = UserSettingsRepository(db, local_id)
        stored = await repo.get_data()
        assert stored is not None and stored["local_claim_closed"] is True
        assert stored["onboarding_done"] is True  # l'objectif du compte local compte (D183)
        await repo.save_data({"onboarding_done": True})  # PUT /settings en mode local
        await db.commit()
        row = (
            await db.execute(select(UserSettingsRow).where(UserSettingsRow.user_id == local_id))
        ).scalar_one()
        assert row.data["local_claim_closed"] is True
