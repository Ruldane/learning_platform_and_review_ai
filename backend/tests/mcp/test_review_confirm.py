"""La demande « À confirmer » après la relecture 10.B2 : journal (M1), revérification au clic
(M6), plafond avant le précontrôle, purge à 30 jours (M8)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bootstrap_mcp import install_adapter
from app.db.models.mcp import McpCall, McpChange, McpConfirmation, McpToken
from app.features.mcp.service.changes import purge_old_changes
from app.features.mcp.service.confirmation_support import purge_closed_confirmations
from app.mcp.base import PrecheckInput, Verdict
from app.mcp.limits import Limits
from tests.agents.graphs_for_tests import TEST_GRAPHS
from tests.mcp.adapter_support import FEATURES, add_probe, call, declarations
from tests.mcp.support import API, Mcp
from tests.mcp.test_confirmations import NOTE, events, make_application, pend

Factory = async_sessionmaker[AsyncSession]


async def shown(amcp: Mcp) -> dict[str, Any]:
    """La première demande de la liste, telle que January la voit."""
    listed = (await amcp.http.get(f"{API}/mcp/confirmations")).json()
    assert listed, "aucune demande"
    item: dict[str, Any] = listed[0]
    return item


# --- M1 : le journal de confirmation ne garde que des identifiants ----------------------------


async def test_confirmation_journal_keeps_identifiers_only(
    amcp: Mcp, writer: str, db_session_factory: Factory
) -> None:
    pending = (await call(amcp, writer, "probe_leak", {}))[0]["data"]

    done = await amcp.http.post(f"{API}/mcp/confirmations/{pending['confirmation_id']}/confirm")

    assert done.status_code == 200
    async with db_session_factory() as db:
        stmt = select(McpCall).where(McpCall.action == "probe_leak:confirm")
        row = (await db.execute(stmt)).scalar_one()
    assert row.ids == {"note_id": "n_1"}  # le texte libre de `thread_id` n'entre pas


# --- M6 : la demande est revérifiée à la confirmation -----------------------------------------


async def test_confirm_refuses_when_the_token_expired_meanwhile(
    amcp: Mcp, writer: str, client: httpx.AsyncClient, db_session_factory: Factory
) -> None:
    app_id = await make_application(client)
    confirmation = (await pend(amcp, writer, app_id))["confirmation_id"]
    async with db_session_factory() as db:
        past = datetime.now(UTC) - timedelta(minutes=1)
        await db.execute(update(McpToken).values(expires_at=past))
        await db.commit()

    late = await amcp.http.post(f"{API}/mcp/confirmations/{confirmation}/confirm")

    assert late.status_code == 409 and late.json()["error"]["code"] == "token_expired"
    assert await events(client, app_id) == 1
    assert (await shown(amcp))["status"] == "refused"


async def test_confirm_refuses_while_the_master_switch_is_off(
    amcp: Mcp, writer: str, client: httpx.AsyncClient
) -> None:
    app_id = await make_application(client)
    confirmation = (await pend(amcp, writer, app_id))["confirmation_id"]
    await amcp.enable(False)

    off = await amcp.http.post(f"{API}/mcp/confirmations/{confirmation}/confirm")

    assert off.status_code == 409 and off.json()["error"]["code"] == "mcp_disabled"
    assert await events(client, app_id) == 1 and (await shown(amcp))["status"] == "pending"
    await amcp.enable(True)
    again = await amcp.http.post(f"{API}/mcp/confirmations/{confirmation}/confirm")
    assert again.status_code == 200 and await events(client, app_id) == 2


async def test_confirm_reruns_the_precheck_and_refuses_a_stale_verdict(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    state = {"ok": True}

    async def precheck(asked: PrecheckInput) -> Verdict:
        if state["ok"]:
            return Verdict(ok=True)
        return Verdict(ok=False, reasons=("Le profil a changé.",))

    add_probe(app)
    models = {name: spec.input_model for name, spec in TEST_GRAPHS.items()}
    install_adapter(app, declarations(precheck=precheck), models)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        amcp = Mcp(http)
        token = await amcp.token(FEATURES, "write")
        app_id = await make_application(client)
        confirmation = (await pend(amcp, token, app_id))["confirmation_id"]
        state["ok"] = False  # entre la demande et le clic

        stale = await http.post(f"{API}/mcp/confirmations/{confirmation}/confirm")

        assert stale.status_code == 409 and stale.json()["error"]["code"] == "precheck_changed"
        assert await events(client, app_id) == 1
        now = await shown(amcp)
        assert now["status"] == "pending"
        assert now["precheck"]["ok"] is False and now["precheck"]["reasons"] == [
            "Le profil a changé."
        ]
        again = await http.post(f"{API}/mcp/confirmations/{confirmation}/confirm")
        assert again.status_code == 200 and await events(client, app_id) == 2


# --- M6 : 20 demandes en attente, contrôlées avant le précontrôle -----------------------------


async def test_pending_cap_is_checked_before_the_precheck(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    runs: list[int] = []

    async def precheck(asked: PrecheckInput) -> Verdict:
        runs.append(1)
        return Verdict(ok=True)

    add_probe(app)
    models = {name: spec.input_model for name, spec in TEST_GRAPHS.items()}
    open_limits = Limits(writes_per_minute=500, calls_per_minute=500, confirmations_per_day=500)
    install_adapter(app, declarations(precheck=precheck), models, open_limits)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        amcp = Mcp(http)
        token = await amcp.token(FEATURES, "write")
        app_id = await make_application(client)
        for _ in range(20):
            await pend(amcp, token, app_id)
        assert len(runs) == 20

        envelope, is_error = await call(
            amcp, token, "applications_event", {"application_id": app_id, **NOTE}
        )

    assert is_error and envelope["data"]["error"]["code"] == "too_many_pending"
    assert len(runs) == 20  # le 21e n'a pas lancé le précontrôle


# --- M8 : le contenu ne reste pas ---------------------------------------------------------------


async def test_old_changes_and_closed_confirmations_are_purged(db_session_factory: Factory) -> None:
    now = datetime.now(UTC)
    old, recent = now - timedelta(days=45), now - timedelta(days=2)
    states = [
        ("refused", old),
        ("expired", old),
        ("pending", old),
        ("confirmed", recent),
        ("refused", recent),
    ]
    async with db_session_factory() as db:
        for when in (old, recent):
            db.add(
                McpChange(
                    user_id="u1",
                    call_id="c",
                    table_name="applications",
                    row_id="r",
                    op="insert",
                    after={"x": 1},
                    created_at=when,
                )
            )
        for status, when in states:
            db.add(
                McpConfirmation(
                    user_id="u1",
                    token_id="t1",
                    action=f"a_{status}",
                    status=status,
                    expires_at=when,
                    created_at=when,
                    request={"body": "texte piégé"},
                )
            )
        await db.commit()

    assert await purge_old_changes(db_session_factory, now) == 1
    assert await purge_closed_confirmations(db_session_factory, now) == 2

    async with db_session_factory() as db:
        kept_changes = list((await db.execute(select(McpChange.created_at))).scalars())
        kept = {c.action for c in (await db.execute(select(McpConfirmation))).scalars()}
    assert len(kept_changes) == 1 and kept_changes[0] > now - timedelta(days=3)
    assert kept == {"a_pending", "a_confirmed", "a_refused"}  # la demande en attente reste
