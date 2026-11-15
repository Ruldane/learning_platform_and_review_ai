"""Synchronisation des relances (D140) : les délais des réglages déplacent les relances en attente
non reportées ; une relance reportée, faite ou ignorée ne bouge ni ne disparaît jamais."""

from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, update

from app.db.models.applications import Application, Reminder
from app.features.applications.repository import ReminderRepository
from app.features.applications.service.reminder_sync import sync_user
from tests.features.applications.conftest import API, created_id

TODAY = date(2026, 11, 15)
REMINDERS = "/api/v1/reminders"


async def _every(client: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    r = await client.get(REMINDERS, params={"due": "false"})
    assert r.status_code == 200, r.text
    return {x["kind"]: x for x in r.json()}


async def _delays(client: httpx.AsyncClient, delays: list[int]) -> None:
    current = (await client.get("/api/v1/settings")).json()
    current.pop("weekly_budget_minutes", None)
    r = await client.put("/api/v1/settings", json={**current, "reminder_delays_days": delays})
    assert r.status_code == 200, r.text


async def test_changed_delays_move_pending_not_postponed(client: httpx.AsyncClient) -> None:
    await created_id(
        client,
        company="Société Fictive",
        title="Développeuse IA",
        status="applied",
        applied_on=str(TODAY - timedelta(days=1)),
    )
    before = await _every(client)
    assert [before[k]["due_on"] for k in ("linkedin_7", "email_14", "close_21")] == [
        "2026-11-21",
        "2026-11-28",
        "2026-12-05",
    ]
    postponed = (
        await client.patch(f"{REMINDERS}/{before['linkedin_7']['id']}", json={"action": "postpone"})
    ).json()
    assert postponed["due_on"] == "2026-11-24"
    done = await client.patch(f"{REMINDERS}/{before['email_14']['id']}", json={"action": "done"})
    assert done.status_code == 200
    await _delays(client, [5, 10, 15])
    after = await _every(client)
    assert after["linkedin_7"]["due_on"] == "2026-11-24"  # reportée : garde son report
    assert after["email_14"]["due_on"] == "2026-11-28"  # faite : jamais déplacée
    assert after["email_14"]["status"] == "done"
    assert after["close_21"]["due_on"] == "2026-11-29"  # en attente : suit les nouveaux délais
    assert after["close_21"]["id"] == before["close_21"]["id"]  # déplacée, pas recréée
    await _delays(client, [7, 14, 21])
    assert (await _every(client))["close_21"]["due_on"] == "2026-12-05"


async def test_sync_never_deletes_done_or_ignored(
    client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La relance est lue « en attente » puis close par une autre requête avant la suppression :
    la suppression garde sa condition sur le statut."""
    application_id = await created_id(
        client,
        company="Société Fictive",
        title="Développeuse IA",
        status="applied",
        applied_on=str(TODAY - timedelta(days=7)),
    )
    async with app.state.session_factory() as db:
        await db.execute(  # l'ancre change : les trois relances en attente ne sont plus attendues
            update(Application)
            .where(Application.id == application_id)
            .values(applied_on=TODAY - timedelta(days=2))
        )
        await db.commit()
    real = ReminderRepository.of_applications

    async def snapshot_then_close(self: ReminderRepository, ids: Any = None) -> list[Reminder]:
        rows = await real(self, ids)
        async with app.state.session_factory() as other:  # une autre requête vient de la clore
            await other.execute(
                update(Reminder)
                .where(Reminder.id == next(r.id for r in rows if r.kind == "linkedin_7"))
                .values(status="done")
            )
            await other.commit()
        return rows

    monkeypatch.setattr(ReminderRepository, "of_applications", snapshot_then_close)
    async with app.state.session_factory() as db:
        await sync_user(db, app.state.local_user_id, TODAY)
        await db.commit()
    monkeypatch.undo()
    async with app.state.session_factory() as db:
        rows = (await db.execute(select(Reminder).order_by(Reminder.due_on))).scalars().all()
    by_anchor = {(r.anchor_on, r.kind): r.status for r in rows}
    assert by_anchor[(TODAY - timedelta(days=7), "linkedin_7")] == "done"  # gardée
    assert (TODAY - timedelta(days=7), "email_14") not in by_anchor  # les autres : retirées
    assert by_anchor[(TODAY - timedelta(days=2), "linkedin_7")] == "pending"  # nouvelle ancre
    detail = (await client.get(f"{API}/{application_id}")).json()
    assert detail["status"] == "applied"
