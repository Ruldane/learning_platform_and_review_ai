"""Port de la création en une phrase (`AgentApplicationStore`, D141) : le jour de January, les
alertes de doublon (mêmes règles que la route), la création par le service de `POST
/applications` (mêmes doublons), idempotente par session (Review Focus n° 1 et n° 4)."""

import logging
from datetime import UTC, date, datetime

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.agents.tools.applications_port import IntakeDraft
from app.core.errors import AppError
from app.db.models.applications import Application, ApplicationEvent
from app.features.applications.service.agent_store import AgentApplicationStore
from app.features.settings.service import SettingsService
from tests.features.applications.conftest import API, created_id

SESSION = "11111111-1111-4111-8111-111111111111"
OTHER_SESSION = "22222222-2222-4222-8222-222222222222"
DRAFT = IntakeDraft(
    company="Société Fictive", title="Développeuse IA", applied_on=date(2026, 11, 14)
)


@pytest.fixture
def store(client: httpx.AsyncClient, app: FastAPI) -> AgentApplicationStore:
    store = app.state.career.application_store
    assert isinstance(store, AgentApplicationStore)
    return store


async def test_context_is_the_local_day_and_language(
    app: FastAPI, store: AgentApplicationStore, me: str
) -> None:
    context = await store.intake_context(me)
    assert (context.today, context.language) == (date(2026, 11, 15), "fr")
    async with app.state.session_factory() as db:
        settings = SettingsService(db, me)
        await settings.replace((await settings.get()).model_copy(update={"timezone": "Asia/Tokyo"}))
        await db.commit()
    app.state.career.applications.now = lambda: datetime(2026, 11, 15, 16, 30, tzinfo=UTC)
    assert (await store.intake_context(me)).today == date(2026, 11, 16)  # 1 h 30 à Tokyo


async def test_alert_for_the_same_application(
    client: httpx.AsyncClient, store: AgentApplicationStore, me: str
) -> None:
    existing = await created_id(
        client, company="Société Fictive", title="Développeuse IA", status="applied",
        applied_on="2026-11-03",
    )  # fmt: skip
    [alert] = await store.intake_alerts(me, DRAFT)
    assert (alert.level, alert.application_id) == ("probable", existing)
    assert "Attention, tu as déjà postulé chez Société Fictive" in alert.message
    assert "le 3 novembre" in alert.message and "Postulée" in alert.message


async def test_no_alert_for_another_company_or_for_a_mere_information(
    client: httpx.AsyncClient, store: AgentApplicationStore, me: str
) -> None:
    await created_id(client, company="Société Fictive", title="Chef de cuisine", status="applied")
    # Même entreprise dans les 30 jours, autre poste : une simple information, rien ne bloque.
    assert await store.intake_alerts(me, DRAFT) == []
    other = DRAFT.model_copy(update={"company": "Autre SA"})
    assert await store.intake_alerts(me, other) == []


async def test_intake_info_gives_the_same_company_information(
    client: httpx.AsyncClient, store: AgentApplicationStore, me: str
) -> None:
    """M4 : la simple information (même entreprise, autre poste, 30 jours) est lue à part."""
    other = await created_id(
        client, company="Société Fictive", title="Chef de cuisine", status="applied"
    )
    [info] = await store.intake_info(me, DRAFT)
    assert (info.application_id, info.company, info.title, info.status) == (
        other,
        "Société Fictive",
        "Chef de cuisine",
        "applied",
    )
    assert info.message.startswith("Pour info : tu as postulé chez Société Fictive")
    assert await store.intake_info(me, DRAFT.model_copy(update={"company": "Autre SA"})) == []


async def test_save_creates_the_application_like_the_route(
    client: httpx.AsyncClient, store: AgentApplicationStore, me: str
) -> None:
    draft = DRAFT.model_copy(
        update={
            "channel": "linkedin",
            "contact_name": "Camille Exemple",
            "contact_role": "Recruteuse",
            "notes": "Message envoyé.",
        }
    )
    application_id = await store.save_intake(me, SESSION, draft, [])
    detail = (await client.get(f"{API}/{application_id}")).json()
    assert (detail["company"], detail["title"], detail["status"]) == (
        "Société Fictive",
        "Développeuse IA",
        "applied",
    )
    assert (detail["applied_on"], detail["channel"], detail["notes"]) == (
        "2026-11-14",
        "linkedin",
        "Message envoyé.",
    )
    assert [(c["name"], c["role"]) for c in detail["contacts"]] == [
        ("Camille Exemple", "Recruteuse")
    ]
    [event] = detail["events"]
    assert (event["kind"], event["status_to"], event["ref_id"]) == ("created", "applied", SESSION)
    assert detail["reminders"]  # relances suggérées comme pour toute fiche postulée


async def test_save_without_a_date_uses_today_and_to_apply_has_none(
    client: httpx.AsyncClient, store: AgentApplicationStore, me: str
) -> None:
    sent = await store.save_intake(me, SESSION, DRAFT.model_copy(update={"applied_on": None}), [])
    assert (await client.get(f"{API}/{sent}")).json()["applied_on"] == "2026-11-15"
    draft = IntakeDraft(company="Autre SA", title="Poste B", status="to_apply")
    planned = await store.save_intake(me, OTHER_SESSION, draft, [])
    detail = (await client.get(f"{API}/{planned}")).json()
    assert (detail["status"], detail["applied_on"]) == ("to_apply", None)


async def test_save_is_idempotent_per_session(
    client: httpx.AsyncClient, store: AgentApplicationStore, me: str
) -> None:
    first = await store.save_intake(me, SESSION, DRAFT, [])
    again = await store.save_intake(me, SESSION, DRAFT, [])
    assert again == first
    assert [a["id"] for a in (await client.get(API)).json()] == [first]
    detail = (await client.get(f"{API}/{first}")).json()
    assert [e["kind"] for e in detail["events"]] == ["created"]


async def test_save_refuses_a_duplicate_like_the_route(
    client: httpx.AsyncClient, store: AgentApplicationStore, me: str
) -> None:
    existing = await created_id(
        client, company="Société Fictive", title="Développeuse IA", status="applied"
    )
    with pytest.raises(AppError) as refused:
        await store.save_intake(me, SESSION, DRAFT, [])
    assert (refused.value.code, refused.value.status_code) == ("application_duplicate", 409)
    [alert] = refused.value.details["alerts"]
    assert alert["application_id"] == existing
    assert len((await client.get(API)).json()) == 1


async def test_distinct_confirmation_creates_and_records_the_pair(
    client: httpx.AsyncClient, app: FastAPI, store: AgentApplicationStore, me: str
) -> None:
    existing = await created_id(
        client, company="Société Fictive", title="Développeuse IA", status="applied"
    )
    [alert] = await store.intake_alerts(me, DRAFT)
    created = await store.save_intake(me, SESSION, DRAFT, [alert.application_id])
    assert created != existing
    async with app.state.session_factory() as db:
        rows = {r.id: r for r in (await db.execute(select(Application))).scalars()}
    assert existing in rows[created].distinct_from and created in rows[existing].distinct_from
    # Une phrase n'a pas d'identité : une troisième fiche pareille alerte sur les deux (comme la
    # route sans offre) ; le couple fiche-fiche confirmé reste inscrit dans les deux sens.
    assert {a.application_id for a in await store.intake_alerts(me, DRAFT)} == {existing, created}


async def test_replayed_save_after_distinct_keeps_one_application(
    client: httpx.AsyncClient, app: FastAPI, store: AgentApplicationStore, me: str
) -> None:
    existing = await created_id(
        client, company="Société Fictive", title="Développeuse IA", status="applied"
    )
    first = await store.save_intake(me, SESSION, DRAFT, [existing])
    assert await store.save_intake(me, SESSION, DRAFT, [existing]) == first
    async with app.state.session_factory() as db:
        found = await db.execute(select(ApplicationEvent).where(ApplicationEvent.ref_id == SESSION))
        assert len(found.scalars().all()) == 1


async def test_intake_data_never_logged(
    caplog: pytest.LogCaptureFixture, store: AgentApplicationStore, me: str
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    secret = IntakeDraft(
        company="Entreprise Ultra Secrète",
        title="Intitulé Ultra Secret",
        contact_name="Contact Ultra Secret",
        notes="Note ultra secrète",
    )
    await store.intake_alerts(me, secret)
    await store.save_intake(me, SESSION, secret, [])
    await store.save_intake(me, SESSION, secret, [])
    with pytest.raises(AppError):
        await store.save_intake(me, OTHER_SESSION, secret, [])  # doublon : 409
    for value in ("Ultra Secr", "ultra secr"):
        assert value not in caplog.text
    assert "Fiche créée" in caplog.text
