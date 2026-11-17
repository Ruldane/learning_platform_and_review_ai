"""Premier lancement (P20, phase 9) : `onboarding_done` ne repasse jamais à faux, et un compte
d'avant la phase 9 sans ligne de réglages mais avec des données n'y est pas renvoyé (D183)."""

import asyncio

import httpx
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.accounts import ApiKey, UserSettingsRow
from app.db.models.learning import Goal
from app.features.settings.repository import UserSettingsRepository
from app.features.settings.service import SettingsModelReader, SettingsService

API = "/api/v1/settings"


async def rows(db: AsyncSession, user_id: str) -> int:
    stmt = (
        select(func.count()).select_from(UserSettingsRow).where(UserSettingsRow.user_id == user_id)
    )
    return int((await db.execute(stmt)).scalar_one())


def a_key(user_id: str) -> ApiKey:
    return ApiKey(user_id=user_id, provider="glm", encrypted_key="chiffre", last4="abcd")


def a_goal(user_id: str) -> Goal:
    return Goal(user_id=user_id, text="Devenir ingénieure en apprentissage automatique")


async def test_onboarding_done_never_reset(client: httpx.AsyncClient) -> None:
    body = (await client.get(API)).json()
    assert body["onboarding_done"] is False
    done = await client.put(API, json=body | {"onboarding_done": True})
    assert done.json()["onboarding_done"] is True
    # Une autre page renvoie l'ancien réglage, ou l'oublie : le premier lancement ne revient pas.
    back = await client.put(API, json=body | {"onboarding_done": False})
    assert back.status_code == 200 and back.json()["onboarding_done"] is True
    without = {key: value for key, value in body.items() if key != "onboarding_done"}
    again = await client.put(API, json=without | {"debate_rounds": 4})
    assert again.json()["onboarding_done"] is True and again.json()["debate_rounds"] == 4
    assert (await client.get(API)).json()["onboarding_done"] is True


async def test_onboarding_done_can_be_set_once(client: httpx.AsyncClient) -> None:
    body = (await client.get(API)).json()
    assert (await client.put(API, json=body)).json()["onboarding_done"] is False
    done = await client.put(API, json=body | {"onboarding_done": True})
    assert done.json()["onboarding_done"] is True


async def test_service_replace_keeps_onboarding_done(db_session: AsyncSession) -> None:
    service = SettingsService(db_session, "u1")
    first = await service.get()
    await service.replace(first.model_copy(update={"onboarding_done": True}))
    kept = await service.replace(first.model_copy(update={"onboarding_done": False}))
    assert kept.onboarding_done is True
    assert (await SettingsService(db_session, "u1").get(initialize=True)).onboarding_done is True


async def test_new_account_starts_the_first_launch(db_session: AsyncSession) -> None:
    assert (await SettingsService(db_session, "u1").get(initialize=True)).onboarding_done is False


async def test_existing_account_without_settings_row_but_with_a_key_is_not_sent_back(
    db_session: AsyncSession,
) -> None:
    db_session.add(a_key("u1"))
    await db_session.commit()
    assert await rows(db_session, "u1") == 0
    assert (await SettingsService(db_session, "u1").get(initialize=True)).onboarding_done is True


async def test_existing_account_without_settings_row_but_with_a_goal_is_not_sent_back(
    db_session: AsyncSession,
) -> None:
    db_session.add(a_goal("u1"))
    await db_session.commit()
    assert (await SettingsService(db_session, "u1").get(initialize=True)).onboarding_done is True


async def test_other_accounts_data_does_not_count(db_session: AsyncSession) -> None:
    db_session.add_all([a_key("u2"), a_goal("u2")])
    await db_session.commit()
    assert (await SettingsService(db_session, "u1").get(initialize=True)).onboarding_done is False


async def test_key_added_during_the_first_launch_does_not_end_it(
    db_session: AsyncSession,
) -> None:
    """Le choix est fixé à la première lecture : l'étape « clé d'API » ne ferme pas l'accueil."""
    assert (await SettingsService(db_session, "u1").get(initialize=True)).onboarding_done is False
    await db_session.commit()
    db_session.add_all([a_key("u1"), a_goal("u1")])
    await db_session.commit()
    assert (await SettingsService(db_session, "u1").get(initialize=True)).onboarding_done is False


async def test_legacy_decision_is_kept_once_taken(db_session: AsyncSession) -> None:
    db_session.add(a_key("u1"))
    await db_session.commit()
    assert (await SettingsService(db_session, "u1").get(initialize=True)).onboarding_done is True
    await db_session.commit()
    await db_session.delete((await db_session.execute(select(ApiKey))).scalar_one())
    await db_session.commit()
    assert (await SettingsService(db_session, "u1").get(initialize=True)).onboarding_done is True


async def test_first_read_creates_the_row_and_keeps_other_defaults(
    db_session: AsyncSession,
) -> None:
    settings = await SettingsService(db_session, "u1").get(initialize=True)
    await db_session.commit()
    assert await rows(db_session, "u1") == 1
    assert settings.debate_rounds == 3 and settings.session_token_cap == 300_000
    stored = await UserSettingsRepository(db_session, "u1").get_data()
    assert stored == {"onboarding_done": False}  # les autres défauts restent ceux du code


async def test_plain_reads_never_write(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Les autres lecteurs (features, agents, planificateur) ne gardent jamais le verrou
    d'écriture de la base : `get()` seul n'écrit rien."""
    db_session.add(a_key("u1"))
    await db_session.commit()
    await SettingsModelReader(db_session_factory).get_model_choice("u1", "fort", None)
    async with db_session_factory() as other:
        await SettingsService(other, "u1").get()
        await other.commit()
    assert await rows(db_session, "u1") == 0


async def test_plain_read_leaves_the_database_writable_by_another_session(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Une session qui lit les réglages puis une autre qui écrit avant son commit : pas de
    « database is locked » (le cas du brief du jour)."""
    service = SettingsService(db_session, "u1")
    await service.get()
    async with db_session_factory() as other:
        other.add(a_goal("u1"))
        await other.commit()
    assert await rows(db_session, "u1") == 0


async def test_simultaneous_first_reads_make_one_row(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    db_session.add(a_goal("u1"))
    await db_session.commit()

    async def read() -> bool:
        async with db_session_factory() as session:
            value = (await SettingsService(session, "u1").get(initialize=True)).onboarding_done
            await session.commit()
            return value

    assert await asyncio.gather(*(read() for _ in range(4))) == [True] * 4
    assert await rows(db_session, "u1") == 1


async def test_legacy_row_keeps_what_the_migration_wrote(db_session: AsyncSession) -> None:
    db_session.add(
        UserSettingsRow(user_id="u1", data={"debate_rounds": 4, "onboarding_done": True})
    )
    await db_session.commit()
    settings = await SettingsService(db_session, "u1").get(initialize=True)
    assert settings.onboarding_done is True and settings.debate_rounds == 4


async def test_get_settings_route_creates_only_the_callers_row(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await client.get(API)
    assert await rows(db_session, app.state.local_user_id) == 1
    assert await rows(db_session, "autre-compte") == 0
