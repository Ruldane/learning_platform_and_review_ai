"""Couverture fonctionnelle des actions ouvertes par la réorganisation."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.ide import IdeRun
from app.db.models.mcp import McpCall
from app.providers.sandbox.fake import FakeSandbox
from app.providers.vector.base import VectorStoreUnavailable
from tests.features.auth.support import CAMILLE, DOMINIQUE
from tests.features.ide.support import new_session
from tests.isolation.conftest import Browser
from tests.mcp.adapter_support import call
from tests.mcp.support import API, LOCAL, Mcp


async def test_account_delete_waits_for_confirmation_and_leaves_no_history(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    token = await mcp.token(("account",), "write")
    answer, failed = await call(mcp, token, "account_delete_data", {"confirm": "SUPPRIMER"})
    assert not failed, answer
    assert answer["data"]["status"] == "pending_confirmation"
    confirmation = answer["data"]["confirmation_id"]
    assert (await client.get(f"{API}/mcp/tokens")).json()

    response = await client.post(f"{API}/mcp/confirmations/{confirmation}/confirm")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "confirmed"
    assert (await client.get(f"{API}/mcp/tokens")).json() == []
    user = app.state.local_user_id
    async with app.state.session_factory() as db:
        assert (await db.scalars(select(McpCall).where(McpCall.user_id == user))).all() == []


async def test_account_export_returns_a_local_download_link(client: httpx.AsyncClient) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    token = await mcp.token(("account",), "read")
    answer, failed = await call(mcp, token, "account_export_data", {})
    assert not failed, answer
    assert answer["data"]["content_type"] == "application/zip"
    assert answer["data"]["local_url"] == "/api/v1/account/export"
    assert answer["data"]["filename"].endswith(".zip")
    assert set(answer["data"]) == {"content_type", "filename", "local_url"}


async def test_overview_lists_features_and_only_tools_available_to_the_token(
    client: httpx.AsyncClient,
) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    token = await mcp.token(("brain", "account"), "read")
    data, failed = await call(mcp, token, "tremplin_overview", {})
    assert not failed, data
    sections = {section["id"]: section for section in data["data"]["sections"]}
    assert {"home", "learn", "code", "memory", "career", "lab", "settings"} == sections.keys()
    features = {
        feature["id"]: feature for section in sections.values() for feature in section["features"]
    }
    assert features["brain"]["tools"]
    assert "brain_relay" in features["brain"]["missing_prerequisites"]
    assert features["account"]["tools"] == [{"name": "account_export_data", "level": 1}]
    assert features["mcp"]["tools"] == []
    assert features["applications"]["tools"] == []


async def test_other_account_cannot_confirm_a_deletion(
    google_app: FastAPI,
    google_client_factory: Browser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camille = await google_client_factory(CAMILLE)
    dominique = await google_client_factory(DOMINIQUE)
    mcp_a = Mcp(camille)
    token_a = await mcp_a.token(("account",), "write")
    token_b = await Mcp(dominique).token(("account",), "read")
    camille_id = (await camille.get(f"{API}/auth/me")).json()["id"]
    index = google_app.state.memory_providers.index
    delete_user = index.delete_user
    calls: list[str] = []

    async def fail_final_pass(user_id: str) -> None:
        calls.append(user_id)
        if len(calls) == 2:
            raise VectorStoreUnavailable()
        await delete_user(user_id)

    monkeypatch.setattr(index, "delete_user", fail_final_pass)
    answer, failed = await call(mcp_a, token_a, "account_delete_data", {"confirm": "SUPPRIMER"})
    assert not failed, answer
    confirmation = answer["data"]["confirmation_id"]
    path = f"{API}/mcp/confirmations/{confirmation}/confirm"
    assert (await dominique.post(path)).status_code == 404
    assert (await camille.get(f"{API}/auth/me")).status_code == 200
    assert calls == []
    response = await camille.post(path)
    assert response.status_code == 200 and response.json()["status"] == "confirmed"
    assert calls == [camille_id, camille_id]
    assert (await camille.get(f"{API}/auth/me")).status_code == 401
    export, failed = await call(Mcp(dominique), token_b, "account_export_data", {})
    assert not failed and export["data"]["local_url"] == "/api/v1/account/export"


async def test_notebook_reads_do_not_persist_output_from_a_finished_run(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    client.headers.update(LOCAL)
    app.state.providers.sandbox = FakeSandbox({"*": "3\n"})
    mcp = Mcp(client)
    token = await mcp.token(("ide",), "read")
    session = await new_session(client, {"main.py": ""})
    session_id = session["id"]
    root = f"{API}/ide/sessions/{session_id}"
    cell = {"id": "a", "kind": "code", "source": "print(3)"}
    created = await client.put(
        f"{root}/notebook",
        json={"path": "test.ipynb", "cells": [cell], "version": session["files_version"]},
    )
    assert created.status_code == 200, created.text
    running = await client.post(f"{root}/notebook/run", json={"path": "test.ipynb", "cell_id": "a"})
    assert running.status_code == 202, running.text
    run_id = running.json()["id"]
    opened, failed = await call(
        mcp, token, "ide_read_notebook", {"session_id": session_id, "path": "test.ipynb"}
    )
    assert not failed, opened
    assert opened["data"]["cells"][0]["output"] is None
    result, failed = await call(mcp, token, "ide_read_notebook_run", {"run_id": run_id})
    assert not failed and result["data"]["status"] == "done"
    persisted = (await client.get(root)).json()
    assert persisted["files_version"] == created.json()["files_version"]
    async with app.state.session_factory() as db:
        stored_run = await db.get(IdeRun, run_id)
        assert stored_run is not None
        assert stored_run.status == "running" and stored_run.notebook_cell is not None
    observed_in_ui = (await client.get(f"{root}/notebook", params={"path": "test.ipynb"})).json()
    assert observed_in_ui["cells"][0]["output"] == "3\n"
