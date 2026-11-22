from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
from fastapi import FastAPI
from pytest import MonkeyPatch

from app.features.dated_commitments import service
from app.features.dated_commitments.service.reminders import due_reminders
from tests.features.dated_commitments.test_dated_commitments import API, commitment
from tests.mcp.adapter_support import call
from tests.mcp.support import LOCAL, Mcp
from tests.mcp.test_direct_write import undo_last


async def test_routine_reads_what_is_due_and_todays_observed_gap(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    today = date(2030, 1, 8)
    monkeypatch.setattr(service, "utcnow", lambda: datetime(2030, 1, 8, 10, tzinfo=UTC))
    created = (await client.post(API, json={**commitment(), "due_on": today.isoformat()})).json()
    owner = app.state.local_user_id
    async with app.state.session_factory() as db:
        assert await due_reminders(db, owner, today, limit=0) == []
        assert await due_reminders(db, owner, today - timedelta(days=1)) == []
        assert await due_reminders(db, "missing-commitment-account", today) == []
        reminder = (await due_reminders(db, owner, today))[0]
        assert reminder.id == created["id"] and reminder.delta is None
        assert reminder.intention == created["intention"]
    measured = await client.post(f"{API}/{created['id']}/review", json={"observed": "4.75"})
    assert measured.status_code == 200, measured.text
    async with app.state.session_factory() as db:
        reviewed = (await due_reminders(db, owner, today))[0]
        assert reviewed.reviewed and reviewed.delta == Decimal("0.50")
        assert await due_reminders(db, owner, today + timedelta(days=1)) == [reviewed]
        assert await due_reminders(db, owner, today + timedelta(days=2)) == []


async def test_mcp_can_undo_an_observed_measure(client: httpx.AsyncClient) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    token = await mcp.token(("dated_commitments",), "write")
    created = await client.post(API, json={**commitment(), "due_on": "2020-01-01"})
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    observed, failed = await call(
        mcp,
        token,
        "dated_commitments_record_result",
        {"commitment_id": item_id, "observed": "0"},
    )
    assert not failed, observed
    assert observed["data"]["delta"] == "-4.25"
    undone = await undo_last(mcp)
    assert undone.status_code == 200, undone.text
    item = (await client.get(f"{API}/{item_id}")).json()
    assert item["status"] == "due" and item["observed"] is None and item["delta"] is None
