"""`SessionView` est une lecture que le front applique selon `last_seq` (D56) : le statut doit être
au moins aussi récent que `last_seq`, donc lu APRÈS lui (SQLite : chaque SELECT a sa propre
image de la base, hors transaction d'écriture)."""

from collections.abc import Collection
from typing import Any

import httpx
import pytest

from app.db.models.agents import AgentSession
from app.features.sessions.repository import SessionReadRepository
from tests.sessions_support import API, wait_status


@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    order: list[str] = []
    real_get, real_seqs = SessionReadRepository.get, SessionReadRepository.last_seqs

    async def get(self: SessionReadRepository, session_id: str) -> AgentSession | None:
        order.append("status")
        return await real_get(self, session_id)

    async def last_seqs(self: SessionReadRepository, ids: Collection[str]) -> dict[str, int]:
        order.append("last_seq")
        return await real_seqs(self, ids)

    monkeypatch.setattr(SessionReadRepository, "get", get)
    monkeypatch.setattr(SessionReadRepository, "last_seqs", last_seqs)
    return order


async def test_get_reads_last_seq_before_the_status(client: httpx.AsyncClient, reads: list[str]):
    r = await client.post(API, json={"graph": "two_steps", "input": {}})
    sid = r.json()["session_id"]
    await wait_status(client, sid, "completed")
    reads.clear()
    view: dict[str, Any] = (await client.get(f"{API}/{sid}")).json()
    assert view["status"] == "completed"
    assert reads == ["last_seq", "status"]
