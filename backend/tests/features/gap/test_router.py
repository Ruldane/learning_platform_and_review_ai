"""Routes de l'écart (D122) : `pending` tant que l'analyse tourne, `ready` avec lignes et score
recalculés (un niveau qui monte change le tableau), `failed` pour une analyse arrêtée ou une offre
refusée ; compétences les plus manquantes, dix au plus, avec `required_in`."""

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI

from app.agents.tools.gap_port import SkillMatch
from app.core.skills import evidence
from app.features.skills.service import SkillsService
from scripts.sample_posting import POSTING_TEXT
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.postings.conftest import API, analysis
from tests.support.gap import LEVELS, MATCHES

NOW = datetime(2026, 11, 18, 9, tzinfo=UTC)


async def _create(client: httpx.AsyncClient, text: str = POSTING_TEXT) -> dict[str, str]:
    r = await client.post(f"{API}/postings", json={"text": text})
    assert r.status_code == 201, r.text
    return {"id": r.json()["posting"]["id"], "session": r.json()["session_id"]}


async def _analyze(
    app: FastAPI, created: dict[str, str], matches: dict[str, str | None], **over: Any
) -> None:
    store, user = app.state.career.gap, app.state.local_user_id
    await store.save_analysis(user, created["session"], created["id"], analysis(**over))
    found = [SkillMatch(need=n, known=k) for n, k in matches.items()]
    await store.save_gap(user, created["session"], created["id"], found)


async def _levels(app: FastAPI, levels: dict[str, Any]) -> None:
    async with app.state.session_factory() as db:
        skills = SkillsService(db, app.state.local_user_id)
        for name, level in levels.items():
            if level is not None:
                await skills.raise_levels([name], level, evidence("quiz", name, name, NOW))
        await db.commit()


async def test_gap_pending_while_analyzing(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher
) -> None:
    created = await _create(client)
    r = await client.get(f"{API}/postings/{created['id']}/gap")
    assert r.status_code == 200
    assert r.json() == {
        "posting_id": created["id"], "status": "pending", "score": None, "rows": [],
        "session_id": created["session"],
    }  # fmt: skip


async def test_gap_rows_follow_current_levels(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    await _levels(app, LEVELS)
    created = await _create(client)
    await _analyze(app, created, MATCHES)
    gap = (await client.get(f"{API}/postings/{created['id']}/gap")).json()
    assert (gap["status"], gap["score"], len(gap["rows"])) == ("ready", 62, 10)
    assert gap["rows"][1] == {
        "skill": "LangGraph", "required": True, "level": None, "action": "to_add", "week": None,
        "source": "posting",
    }  # fmt: skip
    await _levels(app, {"LangGraph": "valide"})
    gap = (await client.get(f"{API}/postings/{created['id']}/gap")).json()
    assert gap["rows"][1]["level"] == "valide" and gap["score"] == 74
    listed = (await client.get(f"{API}/postings")).json()
    assert listed[0]["score"] == 74


async def test_gap_failed_when_the_session_stops_or_the_posting_is_rejected(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    created = await _create(client)
    await launcher_spy.end(app.state.local_user_id, created["session"], "failed")
    gap = (await client.get(f"{API}/postings/{created['id']}/gap")).json()
    assert (gap["status"], gap["session_id"]) == ("failed", created["session"])
    other = await _create(client, POSTING_TEXT + "\nAutre version.")
    await app.state.career.gap.reject(app.state.local_user_id, other["id"], "Pas une offre.")
    gap = (await client.get(f"{API}/postings/{other['id']}/gap")).json()
    assert gap["status"] == "failed" and gap["rows"] == []


async def test_top_missing_limits_to_ten(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    def need(name: str, required: bool) -> dict[str, Any]:
        return {"name": name, "required": required, "domain": None, "learnable": True}

    await _levels(app, {"Python": "valide"})
    first = await _create(client)
    many = [need(f"Outil {n:02d}", n % 2 == 0) for n in range(12)] + [need("Python", True)]
    await _analyze(app, first, {"Python": "Python"}, skills=many)
    second = await _create(client, POSTING_TEXT + "\nAutre version.")
    await _analyze(app, second, {}, skills=[need("Outil 05", True), need("Outil 07", False)])
    top = (await client.get(f"{API}/gap/top-missing")).json()
    assert len(top) == 10
    assert top[:3] == [
        {"skill": "Outil 05", "postings": 2, "required_in": 1},
        {"skill": "Outil 07", "postings": 2, "required_in": 0},
        {"skill": "Outil 00", "postings": 1, "required_in": 1},
    ]
    assert all(row["skill"] != "Python" for row in top)


async def test_top_missing_leaves_out_of_scope_needs(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    skills = [
        {"name": "Permis B", "required": True, "domain": None, "learnable": False},
        {"name": "Rust", "required": False, "domain": None, "learnable": True},
    ]
    created = await _create(client)
    await _analyze(app, created, {}, skills=skills)
    top = (await client.get(f"{API}/gap/top-missing")).json()
    assert top == [{"skill": "Rust", "postings": 1, "required_in": 0}]
