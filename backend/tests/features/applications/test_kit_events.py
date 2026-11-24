"""Fin du kit au fil de la fiche et nom d'entreprise sans lettre latine (D143)."""

import httpx
import pytest
from fastapi import FastAPI

from app.agents.tools.kit_schema import KIT_KINDS
from app.db.models.applications import ApplicationEvent
from app.features.postings.service.rules import company_key
from tests.features.applications.conftest import API
from tests.features.applications.kit_support import (
    OTHER_SESSION,
    SESSION,
    dossier,
    get_kit,
    kit_events,
    kit_store,
    ready_application,
    save,
    sources,
)

pytestmark = pytest.mark.usefixtures("client")


async def test_end_event_enters_the_thread_once_all_seven_are_in(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    for kind in KIT_KINDS[:-1]:
        await save(app, application_id, kind, status="to_check" if kind == "letter" else "ready")
    assert await kit_events(app, application_id) == []
    await save(app, application_id, KIT_KINDS[-1], status="failed")
    await save(app, application_id, KIT_KINDS[-1], status="failed")  # rejeu
    [event] = await kit_events(app, application_id)
    assert event.ref_id == SESSION
    assert event.text == "Application kit complete: 5 ready, 1 to review, 1 failed."
    historical = "Kit de candidature terminé : 5 prête(s), 1 à vérifier, 1 en échec."
    async with app.state.session_factory() as db:
        stored = await db.get(ApplicationEvent, event.id)
        assert stored is not None
        stored.text = historical
        await db.commit()
    await save(app, application_id, KIT_KINDS[-1], status="failed")
    [preserved] = await kit_events(app, application_id)
    assert preserved.id == event.id and preserved.text == historical


async def test_kept_pieces_count_for_the_end_event(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id = await ready_application(client, app)
    for kind in KIT_KINDS:
        await save(app, application_id, kind)
    await client.patch(f"{API}/{application_id}/kit/letter", json={"content": "À moi."})
    for kind in KIT_KINDS:
        if kind != "letter":
            await save(app, application_id, kind, session=OTHER_SESSION)
    events = await kit_events(app, application_id)
    assert [e.ref_id for e in events] == [SESSION, OTHER_SESSION]
    assert events[1].text.endswith("6 ready, 0 to review, 0 failed, 1 kept unchanged.")


async def test_end_event_is_written_when_the_last_piece_was_edited_meanwhile(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """Six pièces rangées par la session, la septième modifiée par January avant que sa branche
    n'arrive : la branche trouve la pièce modifiée et l'événement de fin entre quand même."""
    application_id = await ready_application(client, app)
    for kind in KIT_KINDS:
        await save(app, application_id, kind, session=OTHER_SESSION)
    for kind in KIT_KINDS:
        if kind != "letter":
            await save(app, application_id, kind)
    assert [e.ref_id for e in await kit_events(app, application_id)] == [OTHER_SESSION]
    await client.patch(f"{API}/{application_id}/kit/letter", json={"content": "À moi."})
    await save(app, application_id, "letter")  # la branche arrive : la pièce est gardée
    await save(app, application_id, "letter")  # rejeu
    events = await kit_events(app, application_id)
    assert [e.ref_id for e in events] == [OTHER_SESSION, SESSION]
    assert events[1].text.endswith("6 ready, 0 to review, 0 failed, 1 kept unchanged.")


async def test_non_latin_company_dossier_is_reused_and_keeps_its_sources(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    """`company_key` d'un nom sans lettre latine est vide : une seule clé, partout."""
    name = "株式会社テスト"
    assert company_key(name) == ""
    application_id = await ready_application(client, app, company=name)
    store = kit_store(app)
    ordered = sources(3)
    await store.save_dossier(me, SESSION, name, dossier(), ordered)
    ctx = await store.context(me, application_id)
    assert ctx.company_dossier is not None and ctx.company_dossier_sources == ordered
    await save(app, application_id, "company_brief", meta={"sources": 3})
    brief = next(
        i for i in (await get_kit(client, application_id))["items"] if i["kind"] == "company_brief"
    )
    assert [s["url"] for s in brief["sources"]] == [s.url for s in ordered]
