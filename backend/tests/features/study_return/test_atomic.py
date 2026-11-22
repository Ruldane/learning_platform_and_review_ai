from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow
from app.features.study_return import service
from tests.features.study_return.support import seed_return
from tests.mcp.adapter_support import call
from tests.mcp.support import API, LOCAL, Mcp
from tests.mcp.test_direct_write import undo_last

RETURN = f"{API}/study-return"
TRAINING = f"{API}/study-sessions/training"


async def test_failed_link_rolls_back_training_and_keeps_the_reminder(
    app: FastAPI,
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await seed_return(app)
    assert (await client.post(f"{RETURN}/prepare")).status_code == 200
    yesterday = utcnow().date() - timedelta(days=1)
    assert (
        await client.put(f"{RETURN}/reminder", json={"day": yesterday.isoformat()})
    ).status_code == 200

    async def stop_after_link(db: AsyncSession, user_id: str, training_id: str) -> None:
        await link(db, user_id, training_id)
        raise AppError("synthetic_return_link", "Échec simulé du rattachement.", 409)

    link = service.link_training
    monkeypatch.setattr(service, "link_training", stop_after_link)
    failed = await client.post(f"{RETURN}/start")
    assert failed.status_code == 409 and failed.json()["error"]["code"] == "synthetic_return_link"
    assert (await client.get(f"{TRAINING}/open")).json() is None
    state = (await client.get(RETURN)).json()
    assert state["reminder_due"] is True and state["plan"]["training_id"] is None


async def test_mcp_undo_restores_return_and_reminder_together(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    token = await mcp.token(("study_return",), "write")
    await seed_return(app)
    assert (await client.post(f"{RETURN}/prepare")).status_code == 200
    yesterday = utcnow().date() - timedelta(days=1)
    assert (
        await client.put(f"{RETURN}/reminder", json={"day": yesterday.isoformat()})
    ).status_code == 200
    ready, failed = await call(mcp, token, "study_return_start_block")
    assert not failed, ready
    assert ready["data"]["plan"]["training_id"]
    assert ready["data"]["reminder_on"] is None
    undone = await undo_last(mcp)
    assert undone.status_code == 200, undone.text
    assert (await client.get(f"{TRAINING}/open")).json() is None
    state = (await client.get(RETURN)).json()
    assert state["plan"]["training_id"] is None and state["reminder_due"] is True
