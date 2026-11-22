"""Une seule lecture choisie entre dans le programme, après accord explicite."""

from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.features.program.service.runtime import ProgramRuntime
from app.features.reading_stack.repository import ReadingRepository
from app.features.reading_stack.types import CollectedItem
from tests import sessions_support
from tests.features.replan.conftest import NOW, tasks_of, validated
from tests.sessions_support import use_test_runtime, wait_status

API = "/api/v1"
TITLE = "Guide de la lecture choisie"
ADDRESS = "https://example.org/lecture"


@pytest.fixture
async def reading_client(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setattr(sessions_support, "TIMEOUT", 20.0)
    use_test_runtime(monkeypatch, ['{"summary":"Réorganisons le programme."}'])
    async with (
        LifespanManager(app, startup_timeout=30.0),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


async def test_reading_becomes_one_task_only_after_acceptance(
    app: FastAPI, reading_client: httpx.AsyncClient
) -> None:
    client = reading_client
    user = app.state.local_user_id
    factory = app.state.session_factory
    app.state.replan.now = lambda: NOW
    program_id = await validated(ProgramRuntime(factory, app.state.memory), user)
    async with factory() as db:
        repo = ReadingRepository(db, user)
        reading_id = await repo.record(
            CollectedItem("article", ADDRESS, TITLE, "Résumé", "Texte", "Essai"), NOW
        )
        await repo.record(
            CollectedItem("article", "https://example.org/autre", "Autre lecture", "", "", "Essai"),
            NOW,
        )
        await db.commit()

    response = await client.post(
        f"{API}/reading-stack/{reading_id}/plan", json={"program_id": program_id}
    )
    assert response.status_code == 202, response.text
    sid = response.json()["session_id"]
    pending = await wait_status(client, sid, "waiting_user")
    assert pending["pending_interrupt"]["kind"] == "accept_replan"
    version = (await client.get(f"{API}/programs/{program_id}/versions")).json()[0]
    assert version["status"] == "pending"
    assert len(version["diff"]["added"]) == 1
    assert version["diff"]["added"][0].endswith(f"Lire : {TITLE}")
    assert version["diff"]["removed"] == []
    assert not any(
        task.title == f"Lire : {TITLE}" for task in await tasks_of(factory, program_id, user)
    )

    accepted = await client.post(
        f"{API}/sessions/{sid}/resume",
        json={"interrupt_id": pending["pending_interrupt"]["interrupt_id"], "value": "accept"},
    )
    assert accepted.status_code == 202, accepted.text
    await wait_status(client, sid, "completed")
    tasks = await tasks_of(factory, program_id, user)
    (task,) = [task for task in tasks if task.title == f"Lire : {TITLE}"]
    assert task.type == "lire"
    assert ADDRESS in task.done_criterion
