from dataclasses import replace
from datetime import timedelta

import httpx
from fastapi import FastAPI

from app.agents.tools.replan_port import ReplanDraft
from app.features.program.service.programs import load
from app.features.replan.service.store import AgentReplanStore
from app.providers.calendar.base import Interval
from app.providers.calendar.fake import FakeCalendar
from tests.features.calendar.support import seed_program
from tests.features.calendar.test_flow import NOW, PATH, connect


async def test_replan_respects_an_occupied_day_without_sending_it_to_the_model(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    program, task = await seed_program(app)
    app.state.replan.now = lambda: NOW
    store = AgentReplanStore(app.state.replan)
    owner = app.state.local_user_id
    context = await store.context(
        owner,
        program,
        trigger="message",
        review_entry_id=None,
        available_minutes=None,
        message=None,
    )
    provider = FakeCalendar([Interval(NOW, NOW + timedelta(hours=14))])
    app.state.calendar.port = provider
    app.state.calendar.now = lambda: NOW
    await connect(client)
    saved = await store.preview(
        owner,
        "fixture-calendrier",
        program,
        ReplanDraft(summary="Range les exercices."),
        refs=context.refs(),
        option=None,
        revision=0,
        reason="Recette",
        week_cap_override=None,
    )
    assert saved.moved > 0
    assert not (await store.apply(owner, "fixture-calendrier", program, saved.version)).stale
    async with app.state.session_factory() as db:
        planned = await load(db, owner, program)
        assert next(row for row in planned.tasks if row.id == task).planned_date > NOW.date()
    assert provider.writes == 0


async def test_confirmation_checks_conflicts_and_disconnect_clears_upcoming(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    provider = FakeCalendar()
    app.state.calendar.port = provider
    app.state.calendar.now = lambda: NOW
    await connect(client)
    program, task = await seed_program(app)
    body = {"kind": "study", "program_id": program, "source_id": task}
    assert (await client.get(f"{PATH}/upcoming")).json() is None
    preview = (await client.post(f"{PATH}/proposals", json=body)).json()
    provider.intervals.append(Interval(NOW, NOW + timedelta(minutes=45)))
    denied = await client.post(f"{PATH}/proposals/{preview['id']}/confirm")
    assert denied.status_code == 409 and denied.json()["error"]["code"] == "calendar_conflict"
    assert provider.writes == 0
    preview = (await client.post(f"{PATH}/proposals", json=body)).json()
    assert preview["start"].startswith("2026-11-16T08:45:00")
    done = await client.post(f"{PATH}/proposals/{preview['id']}/confirm")
    assert done.status_code == 200
    upcoming = (await client.get(f"{PATH}/upcoming")).json()
    assert set(upcoming) == {"id", "kind", "start", "end", "timezone"}
    assert upcoming["kind"] == "study" and upcoming["start"] == preview["start"]

    async with app.state.session_factory() as db:
        plan = await load(db, app.state.local_user_id, program)
        next(row for row in plan.tasks if row.id == task).planned_date += timedelta(days=1)
        await db.commit()
    updated = (await client.post(f"{PATH}/proposals", json=body)).json()
    assert updated["action"] == "update"
    id_, prior = next(iter(provider.events.items()))
    provider.events[id_] = replace(prior, title="Modifié dans Agenda")
    assert (await client.post(f"{PATH}/proposals/{updated['id']}/confirm")).status_code == 409
    assert provider.writes == 1
    provider.events[id_] = prior
    assert (await client.post(f"{PATH}/proposals/{updated['id']}/confirm")).status_code == 200
    changed = (await client.get(f"{PATH}/upcoming")).json()
    assert changed["id"] == upcoming["id"] and changed["start"] == updated["start"]
    assert len(provider.events) == 1 and provider.writes == 2
    assert (await client.delete(f"{PATH}/connection")).json()["status"] == "disconnected"
    assert (await client.get(f"{PATH}/upcoming")).json() is None
    assert provider.revocations == 1


async def test_interview_at_the_confirmed_local_time(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    provider = FakeCalendar()
    app.state.calendar.port = provider
    app.state.calendar.now = lambda: NOW
    await connect(client)
    created = await client.post(
        "/api/v1/applications",
        json={"company": "Atelier fictif", "title": "Ingénierie", "status": "interview"},
    )
    assert created.status_code == 201, created.text
    ref = created.json()["application"]["id"]
    dated = await client.patch(f"/api/v1/applications/{ref}", json={"interview_on": "2026-11-17"})
    assert dated.status_code == 200
    payload = {"kind": "interview", "source_id": ref, "time": "10:30", "minutes": 45}
    preview = (await client.post(f"{PATH}/proposals", json=payload)).json()
    assert preview["start"] == "2026-11-17T10:30:00+01:00"
    assert preview["end"] == "2026-11-17T11:15:00+01:00"
    await client.patch(f"/api/v1/applications/{ref}", json={"interview_on": "2026-11-18"})
    stale = await client.post(f"{PATH}/proposals/{preview['id']}/confirm")
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "calendar_proposal_stale"
    assert provider.writes == 0
