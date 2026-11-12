"""Gestes communs des tests des quiz : préparer un quiz prêt (vrai port, brouillon scripté),
répondre, noter une tentative par le vrai port avec des notes choisies, compter des lignes."""

from collections.abc import Sequence
from typing import Any

import httpx
from sqlalchemy import func, select

from app.agents.tools.quiz_port import GradedSaved, QuizDraft
from app.features.quiz.service.quizzes import start_quiz
from app.features.quiz.service.store import AgentQuizStore
from tests.features.quiz.conftest import SKILLS, Seeded
from tests.support.quiz import quiz_draft

API = "/api/v1"
RIGHT = "Elle normalise"  # bon choix des QCM de `quiz_draft`


def draft() -> QuizDraft:
    """10 questions (QCM aux rangs 1, 5 et 9), compétences tournant sur `SKILLS`, 4 fiches."""
    raw = quiz_draft()
    for number, question in enumerate(raw["questions"]):
        question["skill"] = SKILLS[number % len(SKILLS)]
    return QuizDraft.model_validate(raw)


async def ready_quiz(s: Seeded, module: int = 0) -> str:
    started = await start_quiz(s.rt, s.user_id, s.modules[module])
    assert started.session_id is not None
    await AgentQuizStore(s.rt).save_quiz(s.user_id, started.session_id, started.quiz_id, draft())
    return started.quiz_id


async def quiz_view(client: httpx.AsyncClient, quiz_id: str) -> dict[str, Any]:
    r = await client.get(f"{API}/quizzes/{quiz_id}")
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


async def answers(client: httpx.AsyncClient, quiz_id: str, right: bool = True) -> list[Any]:
    """Une réponse par question : le bon choix (affiché) des QCM, ou le premier faux."""
    out: list[Any] = []
    for q in (await quiz_view(client, quiz_id))["questions"]:
        if q["type"] == "qcm":
            good = q["choices"].index(RIGHT)
            out.append({"question_id": q["id"], "choice": good if right else (good + 1) % 3})
        else:
            out.append({"question_id": q["id"], "text": "Ma réponse."})
    return out


async def post_attempt(
    client: httpx.AsyncClient, quiz_id: str, right: bool = True
) -> httpx.Response:
    body = {"answers": await answers(client, quiz_id, right)}
    return await client.post(f"{API}/quizzes/{quiz_id}/attempts", json=body)


async def started_attempt(client: httpx.AsyncClient, quiz_id: str, right: bool = True) -> str:
    r = await post_attempt(client, quiz_id, right)
    assert r.status_code == 202, r.text
    return str(r.json()["attempt_id"])


async def grade(s: Seeded, attempt_id: str, open_scores: Sequence[float]) -> GradedSaved:
    """Note par le vrai port : QCM par le code, ouvertes dans l'ordre avec `open_scores`."""
    store = AgentQuizStore(s.rt)
    found = await store.attempt(s.user_id, attempt_id)
    grades = {ref: (p, "") for ref, p in found.qcm_points.items()}
    for item, score in zip(found.open_items, open_scores, strict=True):
        grades[item.ref] = (score, "Retour de l'Examinateur.")
    return await store.save_grades(s.user_id, "s-grade", attempt_id, grades)


PASS_85 = [1, 1, 1, 1, 1, 0.5, 0]  # QCM justes (3) + 5,5 sur 7 : 85 %
FAIL_35 = [0.5] * 7  # avec des QCM faux : 3,5 sur 10, soit 35 %


async def count(s: Seeded, model: type, **where: Any) -> int:
    async with s.rt.session_factory() as db:
        stmt = select(func.count()).select_from(model)
        for key, value in where.items():
            stmt = stmt.where(getattr(model, key) == value)
        return int((await db.execute(stmt)).scalar_one())
