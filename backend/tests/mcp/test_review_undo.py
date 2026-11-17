"""Annulation après la relecture 10.B2 : lignes liées (I2), double clic et contrainte (M9), appel
sans historique (M7)."""

import asyncio
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.mcp import McpCall
from app.mcp import recorder, undo
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.mcp.test_changes import add, changes
from tests.mcp.test_confirmations import NOTE, events

Factory = async_sessionmaker[AsyncSession]


# --- I2 : annulation et lignes liées ----------------------------------------------------------


async def test_undo_refused_when_rows_were_added_to_an_added_row(
    amcp: Mcp, writer: str, client: httpx.AsyncClient, db_session_factory: Factory
) -> None:
    app_id = await add(amcp, writer)
    call_id = (await amcp.http.get(f"{API}/mcp/changes")).json()[0]["call_id"]
    # January consigne un événement sur la candidature que Claude a ajoutée.
    added = await client.post(f"{API}/applications/{app_id}/events", json=NOTE)
    assert added.status_code == 200, added.text
    before = await events(client, app_id)

    refused = await amcp.http.post(f"{API}/mcp/changes/{call_id}/undo")

    assert refused.status_code == 409 and refused.json()["error"]["code"] == "undo_has_dependents"
    assert "événements" in refused.json()["error"]["message"] or "events" in refused.text
    assert "Relance faite" not in refused.text  # jamais de contenu
    assert (await client.get(f"{API}/applications/{app_id}")).status_code == 200
    assert await events(client, app_id) == before  # rien n'est supprimé
    assert (await amcp.http.get(f"{API}/mcp/changes")).json()[0]["undone_at"] is None
    assert all(row.undone_at is None for row in await changes(db_session_factory))


# --- M9 : annulation à l'abri du double clic et d'une contrainte -------------------------------


async def test_double_click_undo_runs_once(
    amcp: Mcp, writer: str, client: httpx.AsyncClient
) -> None:
    app_id = await add(amcp, writer)
    call_id = (await amcp.http.get(f"{API}/mcp/changes")).json()[0]["call_id"]
    url = f"{API}/mcp/changes/{call_id}/undo"

    first, second = await asyncio.gather(amcp.http.post(url), amcp.http.post(url))

    assert sorted([first.status_code, second.status_code]) == [200, 409]
    assert (await client.get(f"{API}/applications/{app_id}")).status_code == 404


async def test_integrity_error_on_undo_is_a_409_and_changes_nothing(
    amcp: Mcp,
    writer: str,
    client: httpx.AsyncClient,
    db_session_factory: Factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_id = await add(amcp, writer)
    call_id = (await amcp.http.get(f"{API}/mcp/changes")).json()[0]["call_id"]

    async def boom(*args: Any, **kwargs: Any) -> None:
        raise IntegrityError("DELETE", {}, Exception("contrainte"))

    monkeypatch.setattr(undo, "_apply", boom)

    refused = await amcp.http.post(f"{API}/mcp/changes/{call_id}/undo")

    assert refused.status_code == 409 and refused.json()["error"]["code"] == "undo_refused"
    assert (await client.get(f"{API}/applications/{app_id}")).status_code == 200
    assert all(row.undone_at is None for row in await changes(db_session_factory))


# --- M7 : un appel de niveau 2 sans historique le dit -----------------------------------------


async def test_level2_call_without_history_says_so(
    amcp: Mcp, writer: str, db_session_factory: Factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    ordinary, _ = await call(amcp, writer, "applications_add", {"company": "A", "title": "B"})
    assert "annul" not in ordinary["notice"]

    monkeypatch.setattr(recorder, "MAX_ROWS", 0)  # plus de lignes que le plafond : rien gardé
    envelope, is_error = await call(
        amcp, writer, "applications_add", {"company": "C", "title": "D"}
    )

    assert not is_error and envelope["data"]["application"]["id"]
    assert "ne pourra pas être annulé" in envelope["notice"]
    async with db_session_factory() as db:
        stmt = select(McpCall).where(McpCall.action == "applications_add")
        rows = list((await db.execute(stmt.order_by(McpCall.created_at))).scalars())
    assert "history" not in rows[0].ids and rows[1].ids["history"] == "none"


async def test_level2_call_whose_history_cannot_be_written_says_so(
    amcp: Mcp, writer: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken(self: Any) -> int:
        raise RuntimeError("disque plein")

    monkeypatch.setattr(recorder.ChangeRecorder, "persist", broken)

    envelope, is_error = await call(
        amcp, writer, "applications_add", {"company": "C", "title": "D"}
    )

    assert not is_error and "ne pourra pas être annulé" in envelope["notice"]
