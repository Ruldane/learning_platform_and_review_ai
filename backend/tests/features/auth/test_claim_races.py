import asyncio
from collections.abc import Awaitable, Callable

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.config import Settings
from app.db.models.accounts import User
from tests.features.auth.claim_support import (
    CLAIM,
    Factory,
    another_browser,
    choose,
    error_code,
    goal_texts,
    named,
    offered,
    seed_local_space,
    users,
)
from tests.features.auth.support import (
    CAMILLE,
    DOMINIQUE,
    FRONT,
    FakeGoogle,
    cookie_value,
    set_cookie,
    sign_in,
)

Count = Callable[[], Awaitable[int]]
ME = "/api/v1/auth/me"


@pytest.fixture
def google_settings(google_settings: Settings) -> Settings:
    return named(google_settings)


async def test_concurrent_claims_one_owner(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: Factory,
    count_users: Count,
) -> None:
    """Deux onglets du même navigateur reprennent en même temps : un seul gagne."""
    local_id = await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    results = await asyncio.gather(*(choose(google_client, "take_local") for _ in range(4)))
    assert sorted(r.status_code for r in results) == [200, 409, 409, 409]
    loser = next(r for r in results if r.status_code == 409)
    assert error_code(loser) == "local_already_claimed"
    assert next(r for r in results if r.status_code == 200).json()["id"] == local_id
    assert await count_users() == 1
    (row,) = await users(db_session_factory)
    assert row.id == local_id and row.google_sub == "sub-camille.exemple"


async def test_two_accounts_racing_for_the_local_space_one_owner(
    google_app: FastAPI,
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: Factory,
) -> None:
    """Deux comptes Google se sont connectés avant le premier choix : un seul prend l'espace."""
    local_id = await seed_local_space(db_session_factory)
    async with another_browser(google_app) as second:
        await offered(google_client, google, CAMILLE)
        await offered(second, google, DOMINIQUE)
        first, other = await asyncio.gather(
            choose(google_client, "take_local"), choose(second, "take_local")
        )
        assert sorted([first.status_code, other.status_code]) == [200, 409]
        loser = first if first.status_code == 409 else other
        assert error_code(loser) == "local_already_claimed"
    owners = [u for u in await users(db_session_factory) if u.google_sub]
    assert [u.id for u in owners] == [local_id]  # jamais deux comptes sur l'espace local


async def test_second_account_never_offered_local(
    google_app: FastAPI,
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: Factory,
) -> None:
    local_id = await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    await choose(google_client, "take_local")
    async with another_browser(google_app) as second:
        r = await sign_in(second, google, DOMINIQUE)
        assert r.headers["location"] == f"{FRONT}/" and set_cookie(r, "tremplin_claim") is None
        me = (await second.get(ME)).json()
        assert me["email"] == DOMINIQUE and me["id"] != local_id
        assert await goal_texts(second) == []  # jamais les données de l'espace local


async def test_claim_after_fresh_choice_refused(
    google_app: FastAPI,
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: Factory,
) -> None:
    local_id = await seed_local_space(db_session_factory)
    async with another_browser(google_app) as second:
        await offered(google_client, google, CAMILLE)
        await offered(second, google, DOMINIQUE)  # proposée aux deux : aucun compte Google encore
        assert (await choose(google_client, "fresh")).status_code == 200
        late = await choose(second, "take_local")
        assert error_code(late) == "local_already_claimed"
        assert (await second.get(ME)).status_code == 401  # aucune session ouverte
    by_id = {u.id: u for u in await users(db_session_factory)}
    assert by_id[local_id].google_sub is None and by_id[local_id].email is None
    assert [u.email for u in by_id.values() if u.google_sub] == [CAMILLE]


async def test_claim_replayed_after_success_is_refused(
    google_client: httpx.AsyncClient, google: FakeGoogle, db_session_factory: Factory
) -> None:
    await seed_local_space(db_session_factory)
    first = await offered(google_client, google, CAMILLE)
    claim = cookie_value(first, "tremplin_claim")
    assert (await choose(google_client, "take_local")).status_code == 200
    # `take_local` : l'espace local a un propriétaire ; `fresh` (double clic sur « Espace vide »,
    # le compte existe déjà) : « reconnecte-toi », jamais « déjà un propriétaire » (revue 9.A3, M5).
    for choice, code in (("take_local", "local_already_claimed"), ("fresh", "claim_expired")):
        google_client.cookies.clear()
        again = await google_client.post(
            CLAIM, json={"choice": choice}, headers={"cookie": f"tremplin_claim={claim}"}
        )
        assert error_code(again) == code
    assert len(await users(db_session_factory)) == 1


async def test_concurrent_fresh_claims_create_one_account(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: Factory,
    count_users: Count,
) -> None:
    await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    results = await asyncio.gather(*(choose(google_client, "fresh") for _ in range(3)))
    assert sorted(r.status_code for r in results) == [200, 409, 409]
    assert {error_code(r) for r in results if r.status_code == 409} == {"claim_expired"}
    assert await count_users() == 2  # l'espace local et un seul compte


async def test_take_local_when_the_local_space_vanished_is_refused(
    google_client: httpx.AsyncClient, google: FakeGoogle, db_session_factory: Factory
) -> None:
    await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    async with db_session_factory() as db:
        for user in (await db.execute(select(User))).scalars():
            await db.delete(user)
        await db.commit()
    assert error_code(await choose(google_client, "take_local")) == "local_already_claimed"
