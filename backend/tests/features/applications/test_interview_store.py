"""Port réel de l'entretien blanc (`AgentInterviewStore`, D146) : contexte relu en base (fiche,
offre, dossier de moins de 30 jours, CV envoyé, écarts, profil), résultat rangé une seule fois par
session (échanges, débrief, fiche du fil, fiches de révision dues demain)."""

from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select

from app.core.errors import AppError
from app.db.models.applications import Application, ApplicationEvent
from app.db.models.study import Flashcard
from tests.features.applications.conftest import NOW, add_posting, add_version
from tests.features.applications.interview_support import (
    BODY,
    COMPANY,
    ROOT,
    add_profile,
    card,
    debrief,
    exchange,
    interview_row,
    interview_store,
    ready_application,
    running_application,
    save_done,
    set_gap,
    spy,
    store_dossier,
)
from tests.features.applications.kit_support import POSTING, TITLE
from tests.sessions_support import act_as
from tests.support.text_claims import P

pytestmark = pytest.mark.usefixtures("client")


async def _events(app: FastAPI, application_id: str) -> list[ApplicationEvent]:
    async with app.state.session_factory() as db:
        stmt = select(ApplicationEvent).where(ApplicationEvent.application_id == application_id)
        return list((await db.execute(stmt)).scalars())


async def _cards(app: FastAPI) -> list[Flashcard]:
    async with app.state.session_factory() as db:
        return list((await db.execute(select(Flashcard))).scalars())


async def test_context_from_application(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app)
    posting_id = await add_posting(app, company=COMPANY, title=TITLE)
    version_id = await add_version(app, posting_id)
    await set_gap(
        app,
        posting_id,
        [{"need": "Kubernetes", "known": None}, {"need": "Python", "known": "python"}],
    )
    await store_dossier(app, COMPANY, at=NOW - timedelta(days=3))
    application_id = await ready_application(client, app, posting_id=posting_id)
    r = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    ctx = await interview_store(app).context(str(app.state.local_user_id), r.json()["interview_id"])
    assert (ctx.mode, ctx.duration_min, ctx.language, ctx.role) == ("behavioral", 30, "fr", TITLE)
    assert ctx.posting_text and ctx.analysis is not None
    assert ctx.gaps == ["Kubernetes"]
    assert ctx.dossier is not None and ctx.profile == P
    assert version_id and ctx.cv_content is None  # contenu de version vide en base : ignoré


async def test_context_frozen_text_and_stale_dossier(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    spy(app)
    await store_dossier(app, COMPANY, at=NOW - timedelta(days=45))
    application_id = await ready_application(client, app)
    r = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    ctx = await interview_store(app).context(str(app.state.local_user_id), r.json()["interview_id"])
    assert ctx.posting_text == POSTING.strip()
    assert ctx.analysis is not None and ctx.analysis.company == COMPANY
    assert ctx.dossier is None and ctx.gaps == [] and ctx.cv_content is None


async def test_context_of_a_free_interview(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app)
    await add_profile(app)
    r = await client.post(f"{ROOT}/interviews", json=BODY | {"role": "Data engineer"})
    ctx = await interview_store(app).context(str(app.state.local_user_id), r.json()["interview_id"])
    assert ctx.role == "Data engineer"
    assert (ctx.posting_text, ctx.analysis, ctx.dossier, ctx.cv_content, ctx.gaps) == (
        None,
        None,
        None,
        None,
        [],
    )
    posting_id = await add_posting(app, company="Autre SA", title="Ingénieure agents")
    await store_dossier(app, "Autre SA", at=NOW - timedelta(days=1))
    await set_gap(app, posting_id, [{"need": "Rust", "known": None}])
    app.state.career.applications.launcher.refuse = False
    # Un premier entretien est ouvert : on le ferme avant d'en lancer un sur l'offre.
    await app.state.career.applications.launcher.end(
        str(app.state.local_user_id), r.json()["session_id"], "cancelled"
    )
    r = await client.post(f"{ROOT}/interviews", json=BODY | {"posting_id": posting_id})
    ctx = await interview_store(app).context(str(app.state.local_user_id), r.json()["interview_id"])
    assert ctx.role == "Ingénieure agents" and ctx.posting_text and ctx.analysis is not None
    assert ctx.dossier is not None and ctx.gaps == ["Rust"]


async def test_context_other_user_and_unknown_404(client: httpx.AsyncClient, app: FastAPI) -> None:
    _, started = await running_application(client, app)
    store = interview_store(app)
    with pytest.raises(AppError) as exc:
        await store.context("autre-utilisatrice", started["interview_id"])
    assert (exc.value.status_code, exc.value.code) == (404, "interview_not_found")
    with pytest.raises(AppError):
        await store.context(str(app.state.local_user_id), "00000000-0000-4000-8000-000000000000")
    with pytest.raises(AppError):
        await store.save_result(
            "autre-utilisatrice",
            started["session_id"],
            started["interview_id"],
            [exchange()],
            debrief(),
            [],
            [],
        )
    act_as(app, "autre-utilisatrice")
    assert (await interview_row(app, started["interview_id"])).status == "running"


async def test_result_attached_to_application_timeline(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id, started = await running_application(client, app)
    await save_done(app, started, flags=["Rust"])
    row = await interview_row(app, started["interview_id"])
    assert row.status == "done"
    assert [e["index"] for e in row.exchanges] == [0, 1]
    assert row.exchanges[0]["answer"] == "Ma réponse numéro 0."
    assert row.debrief is not None and row.debrief["flags"] == ["Rust"]
    assert row.debrief["cards_created"] == 1 and row.debrief["improved_answer"]
    events = [e for e in await _events(app, application_id) if e.kind == "interview"]
    assert len(events) == 1
    assert events[0].ref_id == started["interview_id"] and events[0].at == NOW
    assert "Entretien blanc" in (events[0].text or "")
    detail = (await client.get(f"/api/v1/applications/{application_id}")).json()
    assert [e["ref_id"] for e in detail["events"] if e["kind"] == "interview"] == [
        started["interview_id"]
    ]
    out = (await client.get(f"{ROOT}/interviews/{started['interview_id']}")).json()
    assert out["flags"] == ["Rust"] and out["cards_created"] == 1
    assert out["debrief"]["expected"] == [
        {"index": 0, "points": ["Point attendu 0a", "Point attendu 0b"]}
    ]


async def test_free_interview_writes_nothing_to_any_timeline(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    spy(app)
    application_id = await ready_application(client, app)
    r = await client.post(f"{ROOT}/interviews", json=BODY | {"role": "Poste libre"})
    await save_done(app, r.json())
    assert (await interview_row(app, r.json()["interview_id"])).status == "done"
    assert [e for e in await _events(app, application_id) if e.kind == "interview"] == []
    async with app.state.session_factory() as db:
        kinds = {e.kind for e in (await db.execute(select(ApplicationEvent))).scalars()}
    assert "interview" not in kinds


async def test_cards_created_due_tomorrow(client: httpx.AsyncClient, app: FastAPI) -> None:
    _, started = await running_application(client, app)
    await save_done(app, started, cards=[card(1), card(2)])
    cards = await _cards(app)
    assert len(cards) == 2
    assert {c.source for c in cards} == {"interview"}
    assert {c.source_id for c in cards} == {started["interview_id"]}
    assert {c.due_date for c in cards} == {NOW.date() + timedelta(days=1)}
    assert {c.step for c in cards} == {0} and {c.skill for c in cards} == {None}
    assert (await client.get(f"{ROOT}/interviews/{started['interview_id']}")).json()[
        "cards_created"
    ] == 2


async def test_save_is_idempotent_per_session(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id, started = await running_application(client, app)
    await save_done(app, started, cards=[card(1)])
    await save_done(app, started, cards=[card(1), card(2)], exchanges=[exchange(0, 1)])
    assert len(await _cards(app)) == 1
    assert len([e for e in await _events(app, application_id) if e.kind == "interview"]) == 1
    row = await interview_row(app, started["interview_id"])
    assert len(row.exchanges) == 2 and row.debrief is not None
    assert row.debrief["cards_created"] == 1


async def test_cards_already_known_are_not_counted(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app)
    application_id = await ready_application(client, app)
    first = (
        await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    ).json()
    await save_done(app, first, cards=[card(1)])
    await app.state.career.applications.launcher.end(
        str(app.state.local_user_id), first["session_id"]
    )
    second = (
        await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    ).json()
    await save_done(app, second, cards=[card(1), card(2)])
    assert len(await _cards(app)) == 2
    out = (await client.get(f"{ROOT}/interviews/{second['interview_id']}")).json()
    assert out["cards_created"] == 1


async def test_stopped_before_any_answer(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id, started = await running_application(client, app)
    await save_done(app, started, exchanges=[], debrief=None, cards=[])
    row = await interview_row(app, started["interview_id"])
    assert (row.status, row.exchanges, row.debrief) == ("stopped", [], None)
    assert [e for e in await _events(app, application_id) if e.kind == "interview"] == []
    assert await _cards(app) == []
    out = (await client.get(f"{ROOT}/interviews/{started['interview_id']}")).json()
    assert (out["status"], out["debrief"], out["flags"], out["cards_created"]) == (
        "stopped",
        None,
        [],
        0,
    )


async def test_debrief_failed_keeps_the_answers(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id, started = await running_application(client, app)
    await save_done(app, started, debrief=None, cards=[])
    row = await interview_row(app, started["interview_id"])
    assert row.status == "debrief_failed" and len(row.exchanges) == 2 and row.debrief is None
    assert [e for e in await _events(app, application_id) if e.kind == "interview"] == []
    assert await _cards(app) == []
    out = (await client.get(f"{ROOT}/interviews/{started['interview_id']}")).json()
    assert out["status"] == "debrief_failed" and out["debrief"] is None
    assert [e["answer"] for e in out["exchanges"]] == [
        "Ma réponse numéro 0.",
        "Ma réponse numéro 1.",
    ]
    # Une session terminée n'efface pas ce statut (pas de `failed` à la lecture).
    await app.state.career.applications.launcher.end(
        str(app.state.local_user_id), started["session_id"]
    )
    out = (await client.get(f"{ROOT}/interviews/{started['interview_id']}")).json()
    assert out["status"] == "debrief_failed"


async def test_interview_survives_a_deleted_application(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id, started = await running_application(client, app)
    async with app.state.session_factory() as db:
        await db.execute(delete(Application).where(Application.id == application_id))
        await db.commit()
    ctx = await interview_store(app).context(str(app.state.local_user_id), started["interview_id"])
    assert ctx.role == TITLE and ctx.posting_text is None
    await save_done(app, started)
    assert (await interview_row(app, started["interview_id"])).status == "done"
