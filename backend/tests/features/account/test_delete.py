"""`POST /account/delete` : la confirmation, tout ce qui part, ce qui reste à l'autre compte, les
sessions annulées, la reprise après une panne, les deux modes de connexion, les journaux."""

import logging
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import User
from app.db.models.agents import AgentSession
from app.db.models.learning import Goal
from app.features.ledger.service.ledger import scheduled_user_ids
from app.providers.vector.base import VectorStoreUnavailable
from tests.features.account.conftest import GoogleApp
from tests.sessions_support import act_as
from tests.support.account import OTHER, as_other, export_archive, seed_other_user
from tests.support.account_delete import (
    CAMILLE,
    DELETE,
    delete_account,
    goals_of,
    has_checkpoint,
    me_of,
    put_checkpoint,
    row_counts,
    saver_of,
    seed_footprint,
    seed_two_accounts,
    vector_count,
)

# --- La confirmation ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "wrong", ["supprimer", "", "SUPPRIMER ", " SUPPRIMER", "OUI-SUPPRIME-TOUT", "x" * 500]
)
async def test_wrong_confirmation_is_422_without_echo(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession, wrong: str
) -> None:
    await seed_footprint(db_session, app, me_of(app), "moi")
    response = await client.post(DELETE, json={"confirm": wrong})
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "confirmation_required",
            "message": "Écris SUPPRIMER pour confirmer.",
            "details": {"fields": ["confirm"]},
        }
    }
    if wrong.strip() and "SUPPRIMER" not in wrong:  # le message demande, lui, `SUPPRIMER`
        assert wrong not in response.text
    assert await goals_of(db_session, me_of(app)) == 1  # rien n'a bougé


@pytest.mark.parametrize("body", [{}, {"confirm": 12345}, {"confirm": None}, {"confirm": ["a"]}])
async def test_malformed_confirmation_is_422_on_the_field_only(
    client: httpx.AsyncClient, body: dict[str, Any]
) -> None:
    response = await client.post(DELETE, json=body)
    assert response.status_code == 422
    assert response.json()["error"]["details"] == {"fields": ["confirm"]}
    assert "12345" not in response.text


# --- Tout ce qui part ---------------------------------------------------------------------------


async def test_delete_empties_every_scoped_table(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    me = me_of(app)
    mine = await seed_footprint(db_session, app, me, "moi", statuses=("completed", "paused"))
    before = await row_counts(db_session, me)
    assert before["auth_sessions"] == 1 and before["sessions"] == 2 and before["goals"] == 1

    response = await delete_account(client)

    assert response.status_code == 204 and response.content == b""
    assert "set-cookie" not in response.headers  # mode local : aucun cookie à effacer
    after = await row_counts(db_session, me)
    assert {name: n for name, n in after.items() if n} == {"users": 1}
    storage = app.state.memory_providers.storage
    assert await storage.list_user(me) == []
    assert await vector_count(app, me) == 0
    for thread in mine.threads:
        assert not await has_checkpoint(saver_of(app), thread)


async def test_delete_keeps_other_user(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    mine, theirs = await seed_two_accounts(db_session, app)
    theirs_before = await row_counts(db_session, OTHER)
    as_other(app)
    exported_before = await export_archive(client)
    app.dependency_overrides.clear()
    mine_archive = await export_archive(client)
    assert OTHER not in mine_archive.text() and "dominique" not in mine_archive.text().lower()

    assert (await delete_account(client)).status_code == 204

    assert await row_counts(db_session, OTHER) == theirs_before
    storage = app.state.memory_providers.storage
    assert (
        await storage.list_user(OTHER) == theirs.files
        and await storage.list_user(mine.user_id) == []
    )
    assert await vector_count(app, OTHER) == 1 and await vector_count(app, mine.user_id) == 0
    for thread in theirs.threads:
        assert await has_checkpoint(saver_of(app), thread)
    assert await db_session.get(AgentSession, theirs.threads[1]) is not None  # reste `running`
    as_other(app)
    exported_after = await export_archive(client)
    assert {n: exported_after.table(n) for n in exported_after.manifest["tables"]} == {
        n: exported_before.table(n) for n in exported_before.manifest["tables"]
    }
    assert exported_after.read(f"files/{theirs.files[0]}") == b"fichier-dominique"


async def test_delete_twice_is_204_and_the_second_finds_nothing(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await seed_footprint(db_session, app, me_of(app), "moi")
    assert (await delete_account(client)).status_code == 204
    assert (await delete_account(client)).status_code == 204
    assert (await row_counts(db_session, me_of(app)))["users"] == 1


async def test_delete_removes_checkpoints(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    mine, theirs = await seed_two_accounts(db_session, app)
    saver = saver_of(app)
    await put_checkpoint(saver, "fil-sans-session")  # un fil qui n'est à personne : intact
    assert all([await has_checkpoint(saver, t) for t in [*mine.threads, *theirs.threads]])

    assert (await delete_account(client)).status_code == 204

    assert not await has_checkpoint(saver, mine.threads[0])
    assert all([await has_checkpoint(saver, t) for t in theirs.threads])
    assert await has_checkpoint(saver, "fil-sans-session")


# --- Les deux modes de connexion ----------------------------------------------------------------


async def test_local_mode_usable_after_delete(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    me = me_of(app)
    await seed_footprint(db_session, app, me, "moi")
    done = await client.put(
        "/api/v1/settings",
        json={**(await client.get("/api/v1/settings")).json(), "onboarding_done": True},
    )
    assert done.status_code == 200 and done.json()["onboarding_done"] is True
    assert me in await scheduled_user_ids(db_session)

    assert (await delete_account(client)).status_code == 204

    settings = await client.get("/api/v1/settings")
    assert settings.status_code == 200 and settings.json()["onboarding_done"] is False
    # D197 : l'espace remis à zéro ne reçoit rien de planifié avant un nouveau premier lancement.
    assert me not in await scheduled_user_ids(db_session)
    assert settings.json()["timezone"] == "Europe/Paris"
    who = await client.get("/api/v1/auth/me")
    assert who.status_code == 200 and who.json()["id"] == me
    assert (await client.get("/api/v1/goals")).json() == []
    assert (await client.get("/api/v1/memory/items")).status_code == 200


async def test_google_mode_delete_removes_user_and_clears_cookie(google_app: GoogleApp) -> None:
    app, client = google_app.app, google_app.client
    async with app.state.session_factory() as db:
        db.add(
            User(
                id=CAMILLE,
                user_id=CAMILLE,
                email="camille.exemple@example.org",
                name="Camille Exemple",
            )
        )
        await db.commit()
        await seed_other_user(db)
        mine = await seed_footprint(db, app, CAMILLE, "camille")
        theirs = await seed_footprint(db, app, OTHER, "dominique")
        theirs_before = await row_counts(db, OTHER)
    act_as(app, CAMILLE)
    client.cookies.set("tremplin_session", "jeton-de-camille")

    response = await delete_account(client)

    assert response.status_code == 204
    cookie = response.headers["set-cookie"]
    assert cookie.startswith('tremplin_session="";') or cookie.startswith("tremplin_session=;")
    assert "Max-Age=0" in cookie and "Path=/" in cookie and "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()
    async with app.state.session_factory() as db:
        assert {n: c for n, c in (await row_counts(db, CAMILLE)).items() if c} == {}
        assert await row_counts(db, OTHER) == theirs_before
        assert await db.get(User, OTHER) is not None
    assert await app.state.memory_providers.storage.list_user(CAMILLE) == []
    assert await app.state.memory_providers.storage.list_user(OTHER) == theirs.files
    assert await vector_count(app, CAMILLE) == 0 and await vector_count(app, OTHER) == 1
    assert not await has_checkpoint(saver_of(app), mine.threads[0])
    assert await has_checkpoint(saver_of(app), theirs.threads[0])


async def test_google_mode_wrong_confirmation_keeps_the_account_and_the_cookie(
    google_app: GoogleApp,
) -> None:
    app, client = google_app.app, google_app.client
    async with app.state.session_factory() as db:
        db.add(User(id=CAMILLE, user_id=CAMILLE, name="Camille"))
        await db.commit()
    act_as(app, CAMILLE)
    response = await client.post(DELETE, json={"confirm": "non"})
    assert response.status_code == 422 and "set-cookie" not in response.headers
    async with app.state.session_factory() as db:
        assert await db.get(User, CAMILLE) is not None


# --- Journaux -----------------------------------------------------------------------------------


async def test_delete_never_logged(
    caplog: pytest.LogCaptureFixture,
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    me = me_of(app)
    user = await db_session.get(User, me)
    assert user is not None
    user.email, user.name = "camille.exemple@example.org", "Camille Exemple"
    mine = await seed_footprint(db_session, app, me, "tag-secret")
    db_session.add(Goal(user_id=me, text="contenu-ultra-secret"))
    await db_session.commit()
    caplog.set_level(logging.DEBUG)

    assert (await client.post(DELETE, json={"confirm": "mon-mot-faux"})).status_code == 422
    assert (await delete_account(client)).status_code == 204

    logged = "\n".join(
        f"{record.name} {record.getMessage()} {record.exc_text or ''}" for record in caplog.records
    )
    for secret in (
        "camille.exemple@example.org",
        "Camille",
        "contenu-ultra-secret",
        "tag-secret",
        "mon-mot-faux",
        "SUPPRIMER",
        mine.files[0].rsplit("/", 1)[1],
        "fichier-tag-secret",
    ):
        assert secret not in logged, secret
    [line] = [r.getMessage() for r in caplog.records if r.name.endswith("service.delete")]
    assert f"user={me}" in line and "duration_ms=" in line and "rows=" in line


async def test_delete_failure_never_logs_the_confirmation(
    caplog: pytest.LogCaptureFixture,
    client: httpx.AsyncClient,
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = app.state.memory_providers.index

    async def down(user_id: str) -> None:
        raise VectorStoreUnavailable()

    monkeypatch.setattr(index, "delete_user", down)
    caplog.set_level(logging.DEBUG)
    assert (await delete_account(client)).status_code == 503
    assert "SUPPRIMER" not in "\n".join(r.getMessage() for r in caplog.records)
