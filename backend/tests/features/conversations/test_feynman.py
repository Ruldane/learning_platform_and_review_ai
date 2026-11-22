import json
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.core.skills import evidence
from app.db.base import utcnow
from app.features.skills.service import SkillsService
from tests.features.lessons.test_router import seed
from tests.mcp.support import API
from tests.sessions_support import use_test_runtime, wait_status

QUESTION = "Quand le regroupement s’applique-t-il ?"
CARD = {"front": "Quand regrouper les lignes ?", "back": "Quand une clé relie plusieurs lignes."}


@pytest.fixture
def feynman_model(monkeypatch: pytest.MonkeyPatch) -> None:
    use_test_runtime(
        monkeypatch,
        [
            json.dumps({"follow_up": QUESTION, "summary": "À préciser.", "mastered": False}),
            json.dumps(
                {
                    "follow_up": "Autre relance ?",
                    "summary": "Distinction claire.",
                    "mastered": True,
                    "cards": [CARD],
                }
            ),
        ],
    )


async def respond(client: httpx.AsyncClient, session_id: str, answer: str) -> str:
    session = await wait_status(client, session_id, "waiting_user")
    prompt = session["pending_interrupt"]
    resumed = await client.post(
        f"{API}/sessions/{session_id}/resume",
        json={"interrupt_id": prompt["interrupt_id"], "value": {"answers": {"answer": answer}}},
    )
    assert resumed.status_code == 202, resumed.text
    return str(prompt["question"])


@pytest.mark.usefixtures("feynman_model")
async def test_lesson_explanation_caps_the_proof_and_applies_the_report_once(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    chapter = await seed(app)
    user = app.state.local_user_id
    async with app.state.session_factory() as db:
        skills = SkillsService(db, user)
        await skills.raise_levels(
            ["pandas"], "declare", evidence("capture", None, "Acquis déclaré", utcnow())
        )
        await db.commit()
    path = f"{API}/lessons/{chapter.lesson_id}/explain"
    request = {"request_id": str(uuid4())}
    started = await client.post(path, json=request)
    assert started.status_code == 202, started.text
    assert (await client.post(path, json=request)).json() == started.json()
    session_id = started.json()["session_id"]
    assert "tes mots" in await respond(client, session_id, "Je groupe les lignes.")
    assert await respond(client, session_id, "La clé détermine chaque groupe.") == QUESTION
    await wait_status(client, session_id, "completed")
    report = (await client.get(path)).json()
    assert report["report"]["summary"] == "Distinction claire."
    assert report["report"]["cards"] == [CARD]
    assert report["report"]["proof_skill"] == "pandas"
    assert report["report"]["saved"] is None
    accept = f"{API}/conversations/explain/{report['id']}/accept"
    first = await client.post(accept)
    assert first.status_code == 200 and first.json() == {"cards_added": 1, "proof_saved": True}
    assert (await client.post(accept)).json() == first.json()
    async with app.state.session_factory() as db:
        assert await SkillsService(db, user).levels_of(["pandas"]) == [("pandas", "en_cours")]
    graph = (await client.get(f"{API}/skills/graph")).json()
    skill = next(node for node in graph["nodes"] if node["name"] == "pandas")
    detail = (await client.get(f"{API}/skills/{skill['id']}")).json()
    assert [item["kind"] for item in detail["evidence"]].count("feynman") == 1
