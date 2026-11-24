from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.program import Task
from app.db.models.skills import UserSkill
from app.db.models.study import Flashcard, JournalEntry
from tests.features.study.conftest import NOW, SKILLS, seed
from tests.features.study.test_training import STUDY, TRAINING
from tests.sessions_support import use_test_runtime, wait_status


@pytest.fixture
def exercise(monkeypatch: pytest.MonkeyPatch) -> None:
    use_test_runtime(
        monkeypatch,
        [
            "Il manque la normalisation [1].\nÀ revoir [1] : Que normalise-t-on ? → Les poids.",
        ],
    )


@pytest.mark.usefixtures("exercise")
async def test_finish_twice_records_time_cards_and_study_evidence_without_ticking_tasks(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    seeded = await seed(app, recording=False)
    opened = await client.post(TRAINING, json={})
    study_id = opened.json()["id"]
    path = f"{TRAINING}/{study_id}"
    sent = await client.post(
        f"{path}/messages",
        json={
            "request_id": str(uuid4()),
            "question": "Dans le module Bases je ne normalise pas les poids.",
        },
    )
    assert sent.status_code == 202, sent.text
    await wait_status(client, sent.json()["session_id"], "completed")
    seeded.at(NOW + timedelta(minutes=5))
    done = await client.patch(path, json={"action": "finish", "worked_minutes": 8})
    assert done.is_success, done.text
    assert done.json()["status"] == "finished" and done.json()["minutes"] == 5
    assert done.json()["flashcards_created"] == 1
    assert {s["name"] for s in done.json()["skills"]} == set(SKILLS)
    assert {s["level"] for s in done.json()["skills"]} == {"in_progress"}
    assert (
        await client.patch(path, json={"action": "finish", "worked_minutes": 42})
    ).json() == done.json()
    summary = (await client.get(f"{STUDY}/summary")).json()
    assert summary["streak_days"] == 1 and summary["week_minutes"] == 5
    async with app.state.session_factory() as db:
        card = (await db.scalars(select(Flashcard))).one()
        assert (card.front, card.back, card.module_id, card.source, card.source_id) == (
            "Que normalise-t-on ?",
            "Les poids.",
            seeded.modules[0],
            "study",
            study_id,
        )
        entries = (await db.scalars(select(JournalEntry))).all()
        assert [entry.ref_key for entry in entries] == [f"study:{study_id}"]
        for skill in (await db.scalars(select(UserSkill))).all():
            assert [(p["kind"], p["ref_id"]) for p in skill.evidence] == [("study", study_id)]
        assert {t.status for t in (await db.scalars(select(Task))).all()} == {"todo"}


async def test_finish_without_any_lesson_keeps_time_and_journal(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    app.state.study.now = lambda: NOW
    opened = await client.post(TRAINING, json={})
    path = f"{TRAINING}/{opened.json()['id']}"
    app.state.study.now = lambda: NOW + timedelta(minutes=4)
    done = await client.patch(path, json={"action": "finish", "worked_minutes": 3})
    assert done.is_success, done.text
    assert [done.json()[key] for key in ("minutes", "flashcards_created", "skills")] == [3, 0, []]
    summary = (await client.get(f"{STUDY}/summary")).json()
    assert summary["week_minutes"] == 3 and summary["streak_days"] == 1
    journal = (await client.get("/api/v1/journal", params={"kind": "study_session"})).json()
    (entry_out,) = journal["entries"]
    assert entry_out["links"]["study_session_kind"] == "training"
    assert "data" not in entry_out
    async with app.state.session_factory() as db:
        entry = (await db.scalars(select(JournalEntry))).one()
        assert entry.data["kind"] == "training" and entry.study_session_id == opened.json()["id"]
