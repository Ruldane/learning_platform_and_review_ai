"""Niveau 3 (10.B2) : une demande « À confirmer » ne s'exécute jamais avant le clic, une seule fois,
sous l'identité enregistrée ; expirée ou refusée, jamais (P15)."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bootstrap_mcp import install_adapter
from app.db.models.mcp import McpCall, McpConfirmation
from app.features.mcp.service.confirmations import expire_due
from app.mcp.limits import Limits
from tests.agents.graphs_for_tests import TEST_GRAPHS
from tests.mcp.adapter_support import FEATURES, add_probe, call, declarations
from tests.mcp.support import API, Mcp

Factory = async_sessionmaker[AsyncSession]
NOTE = {"kind": "note", "text": "Relance faite par téléphone."}


async def make_application(client: httpx.AsyncClient) -> str:
    created = await client.post(f"{API}/applications", json={"company": "Fictive", "title": "Dev"})
    assert created.status_code == 201, created.text
    return str(created.json()["application"]["id"])


async def events(client: httpx.AsyncClient, app_id: str) -> int:
    return len((await client.get(f"{API}/applications/{app_id}")).json()["events"])


async def pend(amcp: Mcp, token: str, app_id: str, **extra: Any) -> dict[str, Any]:
    envelope, is_error = await call(
        amcp, token, "applications_event", {"application_id": app_id, **NOTE, **extra}
    )
    assert not is_error, envelope
    data: dict[str, Any] = envelope["data"]
    assert data["status"] == "pending_confirmation"
    return data


async def test_level3_executes_nothing_before_confirm(
    amcp: Mcp, writer: str, client: httpx.AsyncClient
) -> None:
    app_id = await make_application(client)
    before = await events(client, app_id)

    data = await pend(amcp, writer, app_id)

    assert set(data) == {"status", "confirmation_id", "expires_at"}
    assert datetime.fromisoformat(data["expires_at"]) > datetime.now(UTC) + timedelta(hours=23)
    assert await events(client, app_id) == before  # rien n'a été fait
    listed = (await amcp.http.get(f"{API}/mcp/confirmations")).json()
    assert len(listed) == 1 and listed[0]["id"] == data["confirmation_id"]
    assert listed[0]["status"] == "pending" and listed[0]["action"] == "applications_event"
    assert "POST /applications/" in listed[0]["summary"] and "Relance faite" in listed[0]["summary"]
    # Jamais d'historique annulable : une action de niveau 3 ne s'annule pas.
    assert (await amcp.http.get(f"{API}/mcp/changes")).json() == []


async def test_confirm_runs_once_under_stored_identity(
    amcp: Mcp, writer: str, client: httpx.AsyncClient, app: FastAPI, db_session_factory: Factory
) -> None:
    app_id = await make_application(client)
    data = await pend(amcp, writer, app_id)

    confirmed = await amcp.http.post(f"{API}/mcp/confirmations/{data['confirmation_id']}/confirm")

    assert confirmed.status_code == 200 and confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["decided_at"] is not None
    assert await events(client, app_id) == 2  # la création de la fiche et la note
    async with db_session_factory() as db:
        row = (await db.execute(select(McpConfirmation))).scalar_one()
        names = {call.action for call in (await db.execute(select(McpCall))).scalars()}
    assert row.result_code == 200 and row.token_id
    assert {"applications_event", "applications_event:confirm"} <= names


async def test_confirm_replays_under_the_identity_of_the_token(
    amcp: Mcp, app: FastAPI, client: httpx.AsyncClient
) -> None:
    token = await amcp.token(FEATURES, "write", label="Claude du bureau")
    data = (await call(amcp, token, "probe_who", {}))[0]["data"]
    user_id = (await client.get(f"{API}/auth/me")).json()["id"]

    result = await app.state.mcp_confirmations(user_id).confirm(data["confirmation_id"])

    assert result.data == {"user": user_id, "caller": "mcp", "label": "Claude du bureau"}


async def test_confirm_twice_runs_once(amcp: Mcp, writer: str, client: httpx.AsyncClient) -> None:
    app_id = await make_application(client)
    confirmation = (await pend(amcp, writer, app_id))["confirmation_id"]
    url = f"{API}/mcp/confirmations/{confirmation}/confirm"

    first, second = await asyncio.gather(amcp.http.post(url), amcp.http.post(url))
    third = await amcp.http.post(url)

    assert sorted([first.status_code, second.status_code]) == [200, 409]
    assert third.status_code == 409 and third.json()["error"]["code"] == "confirmation_closed"
    assert await events(client, app_id) == 2  # la note n'est ajoutée qu'une fois


async def test_expired_never_runs(
    amcp: Mcp,
    writer: str,
    client: httpx.AsyncClient,
    db_session_factory: Factory,
) -> None:
    app_id = await make_application(client)
    confirmation = (await pend(amcp, writer, app_id))["confirmation_id"]
    async with db_session_factory() as db:
        past = datetime.now(UTC) - timedelta(minutes=1)
        await db.execute(update(McpConfirmation).values(expires_at=past))
        await db.commit()

    late = await amcp.http.post(f"{API}/mcp/confirmations/{confirmation}/confirm")

    assert late.status_code == 409 and "expirée" in late.json()["error"]["message"]
    assert await events(client, app_id) == 1
    assert (await amcp.http.get(f"{API}/mcp/confirmations")).json()[0]["status"] == "expired"
    assert (
        await amcp.http.post(f"{API}/mcp/confirmations/{confirmation}/refuse")
    ).status_code == 409


async def test_expire_due_marks_only_late_pending_ones(
    amcp: Mcp, writer: str, client: httpx.AsyncClient, db_session_factory: Factory
) -> None:
    app_id = await make_application(client)
    late = (await pend(amcp, writer, app_id))["confirmation_id"]
    fresh = (await pend(amcp, writer, app_id))["confirmation_id"]
    async with db_session_factory() as db:
        past = datetime.now(UTC) - timedelta(hours=1)
        await db.execute(
            update(McpConfirmation).where(McpConfirmation.id == late).values(expires_at=past)
        )
        await db.commit()

    assert await expire_due(db_session_factory, datetime.now(UTC)) == 1
    assert await expire_due(db_session_factory, datetime.now(UTC)) == 0

    async with db_session_factory() as db:
        states = {c.id: c.status for c in (await db.execute(select(McpConfirmation))).scalars()}
    assert states == {late: "expired", fresh: "pending"}


async def test_refused_never_runs(amcp: Mcp, writer: str, client: httpx.AsyncClient) -> None:
    app_id = await make_application(client)
    confirmation = (await pend(amcp, writer, app_id))["confirmation_id"]

    refused = await amcp.http.post(f"{API}/mcp/confirmations/{confirmation}/refuse")
    late = await amcp.http.post(f"{API}/mcp/confirmations/{confirmation}/confirm")

    assert refused.status_code == 200 and refused.json()["status"] == "refused"
    assert late.status_code == 409 and "refusée" in late.json()["error"]["message"]
    assert await events(client, app_id) == 1
    assert (await amcp.http.post(f"{API}/mcp/confirmations/inconnue/confirm")).status_code == 404


async def test_confirm_after_the_token_is_revoked_is_refused(
    amcp: Mcp, writer: str, client: httpx.AsyncClient
) -> None:
    app_id = await make_application(client)
    confirmation = (await pend(amcp, writer, app_id))["confirmation_id"]
    token_id = (await amcp.http.get(f"{API}/mcp/tokens")).json()[0]["id"]
    assert (await amcp.http.delete(f"{API}/mcp/tokens/{token_id}")).status_code == 204

    late = await amcp.http.post(f"{API}/mcp/confirmations/{confirmation}/confirm")

    assert late.status_code == 409 and late.json()["error"]["code"] == "token_revoked"
    assert await events(client, app_id) == 1
    assert (await amcp.http.get(f"{API}/mcp/confirmations")).json()[0]["status"] == "refused"


async def test_failed_execution_is_marked_failed(amcp: Mcp, writer: str) -> None:
    envelope, _ = await call(
        amcp, writer, "applications_event", {"application_id": "inconnue", **NOTE}
    )
    confirmation = envelope["data"]["confirmation_id"]

    done = await amcp.http.post(f"{API}/mcp/confirmations/{confirmation}/confirm")

    assert done.status_code == 200 and done.json()["status"] == "failed"


async def test_pending_cap_20_per_token(
    app: FastAPI, client: httpx.AsyncClient, db_session_factory: Factory
) -> None:
    add_probe(app)
    models = {name: spec.input_model for name, spec in TEST_GRAPHS.items()}
    open_limits = Limits(writes_per_minute=500, calls_per_minute=500, confirmations_per_day=500)
    install_adapter(app, declarations(), models, open_limits)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        amcp = Mcp(http)
        token = await amcp.token(FEATURES, "write")
        other = await amcp.token(FEATURES, "write", label="Autre")
        app_id = await make_application(client)
        for _ in range(20):
            await pend(amcp, token, app_id)

        envelope, is_error = await call(
            amcp, token, "applications_event", {"application_id": app_id, **NOTE}
        )
        elsewhere = await pend(amcp, other, app_id)  # le plafond est par jeton

    assert is_error and envelope["data"]["error"]["code"] == "too_many_pending"
    assert elsewhere["status"] == "pending_confirmation"
    async with db_session_factory() as db:
        count = len(list((await db.execute(select(McpConfirmation))).scalars()))
    assert count == 21


async def test_precheck_verdict_stored_and_shown(
    amcp: Mcp, writer: str, client: httpx.AsyncClient
) -> None:
    app_id = await make_application(client)
    await pend(amcp, writer, app_id)

    shown = (await amcp.http.get(f"{API}/mcp/confirmations")).json()[0]

    assert shown["precheck"] == {
        "ok": False,
        "reasons": ["Une ligne n'est pas dans le profil."],
        "summary": "1 écart",
    }


async def test_profile_write_is_pending_never_validated(
    amcp: Mcp, writer: str, client: httpx.AsyncClient
) -> None:
    before = (await client.get(f"{API}/profile")).json()

    envelope, is_error = await call(amcp, writer, "profile_update", {"data": {}})

    assert not is_error, envelope
    assert envelope["data"]["status"] == "pending_confirmation"
    assert (await client.get(f"{API}/profile")).json() == before  # aucune version écrite
    shown = (await amcp.http.get(f"{API}/mcp/confirmations")).json()[0]
    assert shown["action"] == "profile_update" and shown["precheck"]["ok"] is False
    assert shown["status"] == "pending"


async def test_read_only_token_cannot_create_a_request(
    amcp: Mcp, client: httpx.AsyncClient
) -> None:
    reader = await amcp.token(FEATURES, "read")
    app_id = await make_application(client)

    response = await amcp.call(reader, "applications_event", {"application_id": app_id, **NOTE})

    assert response.status_code == 403
    assert (await amcp.http.get(f"{API}/mcp/confirmations")).json() == []
