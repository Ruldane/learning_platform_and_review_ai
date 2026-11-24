import json
import time
from collections.abc import Awaitable, Callable

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI

from app.config import Settings
from app.core.security import load_or_create_secret
from tests.features.auth.claim_support import (
    CLAIM,
    LOCAL_GOAL,
    Factory,
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
    set_cookie,
    sign_in,
)

Count = Callable[[], Awaitable[int]]
ME = "/api/v1/auth/me"


@pytest.fixture
def google_settings(google_settings: Settings) -> Settings:
    return named(google_settings)


async def test_first_google_account_offered_local(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: Factory,
    count_sessions: Count,
) -> None:
    await seed_local_space(db_session_factory)
    r = await sign_in(google_client, google)
    assert r.status_code == 302 and r.headers["location"] == f"{FRONT}/connexion/reprise"
    claim = (set_cookie(r, "tremplin_claim") or "").lower()
    assert "max-age=600" in claim and "path=/api/v1/auth/google" in claim and "httponly" in claim
    assert "samesite=lax" in claim
    assert set_cookie(r, "tremplin_session") is None
    # Rien n'est créé avant le choix : ni compte, ni session ; l'espace local n'est pas touché.
    (local,) = await users(db_session_factory)
    assert local.google_sub is None and local.email is None
    assert await count_sessions() == 0
    assert (await google_client.get(ME)).status_code == 401


async def test_no_local_space_means_no_offer(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count
) -> None:
    r = await sign_in(google_client, google)
    assert r.headers["location"] == f"{FRONT}/" and set_cookie(r, "tremplin_claim") is None
    assert await count_users() == 1


async def test_take_local_keeps_same_id_and_data(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: Factory,
    count_users: Count,
) -> None:
    local_id = await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    r = await choose(google_client, "take_local")
    assert r.status_code == 200
    me = r.json()
    assert me["id"] == local_id and me["email"] == CAMILLE and me["auth_mode"] == "google"
    assert me["name"] == "Camille Exemple"
    session = (set_cookie(r, "tremplin_session") or "").lower()
    assert "httponly" in session and "samesite=lax" in session and "max-age=2592000" in session
    assert "path=/" in session and "; secure" not in session
    cleared = (set_cookie(r, "tremplin_claim") or "").lower()
    assert "max-age=0" in cleared and "path=/api/v1/auth/google" in cleared
    assert (await google_client.get(ME)).json()["id"] == local_id
    assert await goal_texts(google_client) == [LOCAL_GOAL]  # l'objectif de l'espace local
    assert await count_users() == 1
    (row,) = await users(db_session_factory)
    assert row.id == row.user_id == local_id and row.google_sub == "sub-camille.exemple"


async def test_a_returning_account_is_signed_in_without_a_choice(
    google_client: httpx.AsyncClient, google: FakeGoogle, db_session_factory: Factory
) -> None:
    local_id = await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    await choose(google_client, "take_local")
    google_client.cookies.clear()
    r = await sign_in(google_client, google, CAMILLE)
    assert r.headers["location"] == f"{FRONT}/" and set_cookie(r, "tremplin_claim") is None
    assert (await google_client.get(ME)).json()["id"] == local_id


async def test_fresh_leaves_local_untouched(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: Factory,
    count_users: Count,
) -> None:
    local_id = await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    r = await choose(google_client, "fresh")
    assert r.status_code == 200 and r.json()["id"] != local_id
    assert r.json()["email"] == CAMILLE and set_cookie(r, "tremplin_session")
    assert await goal_texts(google_client) == []  # un espace vide
    assert await count_users() == 2
    by_id = {u.id: u for u in await users(db_session_factory)}
    assert by_id[local_id].google_sub is None and by_id[local_id].email is None
    assert by_id[local_id].name == "local"  # visible en repassant `AUTH_MODE=local`


async def test_claim_without_cookie_is_409(
    google_client: httpx.AsyncClient, db_session_factory: Factory, count_users: Count
) -> None:
    await seed_local_space(db_session_factory)
    for choice in ("take_local", "fresh"):
        r = await choose(google_client, choice)
        assert error_code(r) == "claim_expired"
        assert r.json()["error"]["message"] == "This choice expired. Sign in with Google again."
    assert await count_users() == 1 and set_cookie(r, "tremplin_session") is None


def sealed(settings: Settings, age_s: int) -> str:
    fernet = Fernet(load_or_create_secret(settings.secret_path))
    identity = {"sub": "sub-camille", "email": CAMILLE, "name": "Camille Exemple"}
    return fernet.encrypt_at_time(json.dumps(identity).encode(), int(time.time()) - age_s).decode()


async def test_stale_or_forged_claim_cookie_is_409(
    google_client: httpx.AsyncClient,
    google_settings: Settings,
    db_session_factory: Factory,
    count_users: Count,
) -> None:
    local_id = await seed_local_space(db_session_factory)
    bad = [
        sealed(google_settings, 11 * 60),  # de plus de 10 minutes
        "garbage",
        "gAAAAAB-not-a-real-token",
        Fernet(Fernet.generate_key()).encrypt(b"{}").decode(),  # chiffré par une autre clé
    ]
    for value in bad:
        r = await google_client.post(
            CLAIM, json={"choice": "take_local"}, headers={"cookie": f"tremplin_claim={value}"}
        )
        assert error_code(r) == "claim_expired"
    assert await count_users() == 1
    (row,) = await users(db_session_factory)
    assert row.id == local_id and row.google_sub is None
    # Le même témoin à 5 minutes passe : seul l'âge l'a fait refuser.
    ok = await google_client.post(
        CLAIM,
        json={"choice": "take_local"},
        headers={"cookie": f"tremplin_claim={sealed(google_settings, 5 * 60)}"},
    )
    assert ok.status_code == 200 and ok.json()["id"] == local_id


async def test_claim_cookie_without_the_identity_fields_is_409(
    google_client: httpx.AsyncClient, google_settings: Settings, db_session_factory: Factory
) -> None:
    await seed_local_space(db_session_factory)
    fernet = Fernet(load_or_create_secret(google_settings.secret_path))
    for payload in (b'{"sub": "s"}', b'{"sub": 1, "email": "a@b.c", "name": "x"}', b"[]", b"nope"):
        value = fernet.encrypt(payload).decode()
        r = await google_client.post(
            CLAIM, json={"choice": "fresh"}, headers={"cookie": f"tremplin_claim={value}"}
        )
        assert error_code(r) == "claim_expired"


async def test_claim_rechecks_the_allowlist(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    google_app: FastAPI,
    db_session_factory: Factory,
    count_users: Count,
) -> None:
    await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    google_app.state.settings.allowed_emails = DOMINIQUE  # retirée entre-temps
    r = await choose(google_client, "fresh")
    assert error_code(r) == "claim_expired" and set_cookie(r, "tremplin_session") is None
    assert await count_users() == 1


async def test_claim_in_local_mode_is_404(client: httpx.AsyncClient) -> None:
    r = await client.post(CLAIM, json={"choice": "take_local"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "google_auth_disabled"


async def test_a_claimed_session_can_be_closed(
    google_client: httpx.AsyncClient, google: FakeGoogle, db_session_factory: Factory
) -> None:
    await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    await choose(google_client, "take_local")
    assert (await google_client.post("/api/v1/auth/logout")).status_code == 204
    assert (await google_client.get(ME)).status_code == 401


async def test_star_in_the_allowlist_never_offers_the_local_space(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    google_app: FastAPI,
    db_session_factory: Factory,
    count_users: Count,
) -> None:
    """Avec `*` (même dans une liste), la première venue ne peut pas prendre les données locales."""
    local_id = await seed_local_space(db_session_factory)
    google_app.state.settings.allowed_emails = f"{CAMILLE},*"  # `*` n'importe où : tous admis
    r = await sign_in(google_client, google, CAMILLE)
    assert r.headers["location"] == f"{FRONT}/" and set_cookie(r, "tremplin_claim") is None
    me = (await google_client.get(ME)).json()
    assert me["email"] == CAMILLE and me["id"] != local_id
    assert await goal_texts(google_client) == []
    (local,) = [u for u in await users(db_session_factory) if u.id == local_id]
    assert local.google_sub is None and local.email is None  # l'espace local reste intact
    assert await count_users() == 2


async def test_claim_cookie_made_under_a_named_list_is_refused_once_the_list_is_star(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    google_app: FastAPI,
    db_session_factory: Factory,
    count_users: Count,
) -> None:
    await seed_local_space(db_session_factory)
    await offered(google_client, google, CAMILLE)
    google_app.state.settings.allowed_emails = "*"
    assert error_code(await choose(google_client, "take_local")) == "claim_expired"
    assert await count_users() == 1


async def test_an_address_not_named_in_the_list_is_not_offered_the_local_space(
    google_client: httpx.AsyncClient, google: FakeGoogle, db_session_factory: Factory
) -> None:
    await seed_local_space(db_session_factory)
    r = await sign_in(google_client, google, "inconnue.exemple@example.org")
    assert r.headers["location"].endswith("/connexion?erreur=email_not_allowed")
