"""Niveau 2 (10.B2) : l'historique des changements d'un appel et son annulation (P14)."""

from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.registry import GRAPHS
from app.bootstrap_mcp import install_adapter
from app.db.models.mcp import McpCall, McpChange
from tests.agents.graphs_for_tests import TEST_GRAPHS
from tests.features.auth.support import CAMILLE, DOMINIQUE
from tests.mcp.adapter_support import FEATURES, add_probe, call, declarations
from tests.mcp.support import API, Mcp

Browser = Callable[[str], Awaitable[httpx.AsyncClient]]
Factory = async_sessionmaker[AsyncSession]


async def changes(factory: Factory) -> list[McpChange]:
    async with factory() as db:
        stmt = select(McpChange).order_by(McpChange.created_at, McpChange.id)
        return list((await db.execute(stmt)).scalars())


async def add(amcp: Mcp, token: str, **fields: Any) -> str:
    envelope, is_error = await call(
        amcp, token, "applications_add", {"company": "Société Fictive", "title": "Dev", **fields}
    )
    assert not is_error, envelope
    return str(envelope["data"]["application"]["id"])


async def test_level2_records_insert_update_with_before_after(
    amcp: Mcp, writer: str, db_session_factory: Factory
) -> None:
    app_id = await add(amcp, writer, notes="première note")
    created = await changes(db_session_factory)
    inserted = [c for c in created if c.table_name == "applications"]
    assert len(inserted) == 1 and inserted[0].op == "insert" and inserted[0].row_id == app_id
    assert inserted[0].before is None and inserted[0].after is not None
    assert inserted[0].after["company"] == "Société Fictive"
    assert {c.table_name for c in created} >= {"applications"}  # fiche, et ses suites éventuelles

    await call(amcp, writer, "applications_update", {"application_id": app_id, "notes": "deuxième"})

    updated = [c for c in await changes(db_session_factory) if c.op == "update"]
    assert len(updated) == 1 and updated[0].table_name == "applications"
    assert updated[0].before is not None and updated[0].after is not None
    assert updated[0].before["notes"] == "première note"
    assert updated[0].after["notes"] == "deuxième"
    assert updated[0].call_id != inserted[0].call_id

    # L'appel journalisé porte le même identifiant que ses changements, et la table des changements
    # de l'interface le montre avec son outil.
    async with db_session_factory() as db:
        calls = {row.id: row for row in (await db.execute(select(McpCall))).scalars()}
    assert calls[inserted[0].call_id].ids == {"application_id": app_id}
    assert calls[updated[0].call_id].ids == {"id": app_id}
    listed = (await amcp.http.get(f"{API}/mcp/changes")).json()
    assert {item["action"] for item in listed} == {"applications_add", "applications_update"}
    assert all("applications" in item["tables"] and item["undone_at"] is None for item in listed)


async def test_failed_call_records_nothing_and_level1_never_records(
    amcp: Mcp, writer: str, db_session_factory: Factory
) -> None:
    await call(amcp, writer, "applications_add", {"company": "x"})  # titre manquant : refusé
    await call(amcp, writer, "applications_list")
    bad, is_error = await call(amcp, writer, "applications_update", {"application_id": "inconnu"})

    assert is_error and bad["data"]["error"]["code"] == "application_not_found"
    assert await changes(db_session_factory) == []


async def test_undo_insert_deletes_row(amcp: Mcp, writer: str, client: httpx.AsyncClient) -> None:
    app_id = await add(amcp, writer)
    call_id = (await amcp.http.get(f"{API}/mcp/changes")).json()[0]["call_id"]
    assert (await client.get(f"{API}/applications/{app_id}")).status_code == 200

    undone = await amcp.http.post(f"{API}/mcp/changes/{call_id}/undo")

    assert undone.status_code == 200 and undone.json()["call_id"] == call_id
    assert undone.json()["undone"] >= 1
    assert (await client.get(f"{API}/applications/{app_id}")).status_code == 404
    again = await amcp.http.post(f"{API}/mcp/changes/{call_id}/undo")
    assert again.status_code == 409 and again.json()["error"]["code"] == "already_undone"
    assert (await amcp.http.get(f"{API}/mcp/changes")).json()[0]["undone_at"] is not None


async def test_undo_update_restores_values(
    amcp: Mcp, writer: str, client: httpx.AsyncClient
) -> None:
    app_id = await add(amcp, writer, notes="avant")
    await call(amcp, writer, "applications_update", {"application_id": app_id, "notes": "après"})
    update_call = next(
        item["call_id"]
        for item in (await amcp.http.get(f"{API}/mcp/changes")).json()
        if item["action"] == "applications_update"
    )
    before = (await client.get(f"{API}/applications/{app_id}")).json()
    assert before["notes"] == "après"

    assert (await amcp.http.post(f"{API}/mcp/changes/{update_call}/undo")).status_code == 200

    restored = (await client.get(f"{API}/applications/{app_id}")).json()
    assert restored["notes"] == "avant"
    assert restored["updated_at"] != before["updated_at"]


async def test_undo_refused_when_row_changed_since(
    amcp: Mcp, writer: str, client: httpx.AsyncClient
) -> None:
    app_id = await add(amcp, writer, notes="faite par Claude")
    call_id = (await amcp.http.get(f"{API}/mcp/changes")).json()[0]["call_id"]
    # January la retouche elle-même, depuis l'interface.
    edited = await client.patch(f"{API}/applications/{app_id}", json={"notes": "retouchée"})
    assert edited.status_code == 200

    refused = await amcp.http.post(f"{API}/mcp/changes/{call_id}/undo")

    assert refused.status_code == 409 and refused.json()["error"]["code"] == "undo_refused"
    assert "has changed since" in refused.json()["error"]["message"]
    assert "retouchée" not in refused.text and "faite par Claude" not in refused.text
    kept = (await client.get(f"{API}/applications/{app_id}")).json()
    assert kept["notes"] == "retouchée"  # rien n'est écrasé
    assert (await amcp.http.get(f"{API}/mcp/changes")).json()[0]["undone_at"] is None


async def test_undo_unknown_call_is_404(amcp: Mcp) -> None:
    response = await amcp.http.post(f"{API}/mcp/changes/inconnu/undo")

    assert response.status_code == 404 and response.json()["error"]["code"] == "call_not_found"


async def test_undo_other_users_call_is_404(
    google_app: FastAPI,  # noqa: F811
    google_client_factory: Browser,
) -> None:
    models = {name: spec.input_model for name, spec in {**GRAPHS, **TEST_GRAPHS}.items()}
    add_probe(google_app)
    install_adapter(google_app, declarations(), models)
    camille = await google_client_factory(CAMILLE)
    dominique = await google_client_factory(DOMINIQUE)
    await camille.put(f"{API}/mcp/settings", json={"enabled": True})
    created = await camille.post(
        f"{API}/mcp/tokens", json={"label": "C", "features": list(FEATURES), "mode": "write"}
    )
    transport = httpx.ASGITransport(app=google_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        mcp = Mcp(http)
        app_id = await add(mcp, created.json()["token"])
    call_id = (await camille.get(f"{API}/mcp/changes")).json()[0]["call_id"]

    assert (await dominique.get(f"{API}/mcp/changes")).json() == []
    stranger = await dominique.post(f"{API}/mcp/changes/{call_id}/undo")
    assert stranger.status_code == 404
    assert (await camille.get(f"{API}/applications/{app_id}")).status_code == 200  # intacte
    assert (await camille.post(f"{API}/mcp/changes/{call_id}/undo")).status_code == 200
    assert (await camille.get(f"{API}/applications/{app_id}")).status_code == 404


async def test_changes_never_copy_secrets_or_secret_tables(
    amcp: Mcp, writer: str, db_session_factory: Factory
) -> None:
    from app.db.models.accounts import ApiKey  # noqa: PLC0415
    from app.mcp.rowstate import recordable  # noqa: PLC0415

    assert not recordable(ApiKey.__table__)  # type: ignore[arg-type]
    await add(amcp, writer)
    rows = await changes(db_session_factory)
    assert rows and all(not row.table_name.startswith(("mcp_", "api_keys")) for row in rows)
    assert all("hash" not in (row.after or {}) for row in rows)
