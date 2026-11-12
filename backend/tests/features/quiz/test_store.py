"""Port des quiz `AgentQuizStore` (D100, D101) : module et leçon, rangement idempotent du quiz,
échec qui ne touche pas un quiz prêt, tentative à noter, note rangée une seule fois, verrou du
programme pris avant la transaction (F4), isolation."""

import asyncio
import logging
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select

from app.agents.tools.quiz_port import QuizDraft
from app.core.errors import AppError
from app.db.models.program import Task
from app.db.models.study import Flashcard, JournalEntry, QuizAttempt, QuizQuestion
from app.features.program.schemas import TaskPatch
from app.features.program.service.editing import move_or_edit_task
from app.features.quiz.service.quizzes import start_quiz
from app.features.quiz.service.store import AgentQuizStore
from tests.features.quiz.conftest import LESSON, SKILLS, Seeded
from tests.features.quiz.support import FAIL_35, count, grade, ready_quiz, started_attempt
from tests.support.quiz import quiz_draft


async def test_material_then_save_quiz_is_idempotent(seeded: Seeded) -> None:
    store = AgentQuizStore(seeded.rt)
    started = await start_quiz(seeded.rt, seeded.user_id, seeded.modules[0])
    material = await store.material(seeded.user_id, started.quiz_id)
    assert (material.module_title, material.skills) == ("Module Bases", SKILLS)
    assert material.lesson_markdown == LESSON and material.language == "fr"
    draft = QuizDraft.model_validate(quiz_draft())  # compétence « Attention », hors du module
    assert await store.save_quiz(seeded.user_id, "s1", started.quiz_id, draft) == 10
    assert await store.save_quiz(seeded.user_id, "s1", started.quiz_id, draft) == 10
    assert await count(seeded, QuizQuestion) == 10
    assert await count(seeded, Flashcard, source="lesson") == 4
    async with seeded.rt.session_factory() as db:
        skills = set((await db.execute(select(QuizQuestion.skill))).scalars())
        cards = set((await db.execute(select(Flashcard.skill))).scalars())
    assert skills == cards == {"pandas"}  # rattachées à la première compétence du module
    await store.quiz_failed(seeded.user_id, started.quiz_id, "trop tard")
    view = await store.material(seeded.user_id, started.quiz_id)
    assert view.quiz_id == started.quiz_id  # toujours prêt, l'échec ne l'a pas touché


async def test_store_isolates_users(client: httpx.AsyncClient, seeded: Seeded) -> None:
    store = AgentQuizStore(seeded.rt)
    quiz_id = await ready_quiz(seeded)
    attempt_id = await started_attempt(client, quiz_id)
    for call, code in [
        (store.material("autre", quiz_id), "quiz_not_found"),
        (store.attempt("autre", attempt_id), "attempt_not_found"),
        (store.save_grades("autre", "s", attempt_id, {}), "attempt_not_found"),
    ]:
        with pytest.raises(AppError) as caught:
            await call
        assert caught.value.code == code


async def test_attempt_to_grade_sends_open_items_only(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    quiz_id = await ready_quiz(seeded)
    attempt_id = await started_attempt(client, quiz_id)
    found = await AgentQuizStore(seeded.rt).attempt(seeded.user_id, attempt_id)
    assert found.qcm_points == {"q1": 1.0, "q5": 1.0, "q9": 1.0}
    assert [item.ref for item in found.open_items] == ["q2", "q3", "q4", "q6", "q7", "q8", "q10"]
    assert all(item.type != "qcm" and item.answer == "Ma réponse." for item in found.open_items)
    assert found.lesson_markdown == LESSON and found.module_title == "Module Bases"


async def test_save_grades_twice_writes_once(client: httpx.AsyncClient, seeded: Seeded) -> None:
    quiz_id = await ready_quiz(seeded)
    attempt_id = await started_attempt(client, quiz_id, right=False)
    first = await grade(seeded, attempt_id, FAIL_35)
    counts = [
        await count(seeded, Flashcard),
        await count(seeded, Task),
        await count(seeded, JournalEntry),
    ]
    again = await grade(seeded, attempt_id, [1.0] * 7)  # rejoué : la première note reste
    assert again == first
    assert counts == [
        await count(seeded, Flashcard),
        await count(seeded, Task),
        await count(seeded, JournalEntry),
    ]
    assert await count(seeded, JournalEntry) == 1


async def test_save_grades_waits_for_the_program_lock(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    """F4 : le verrou du programme est pris AVANT la transaction d'écriture ; un déplacement de
    tâche qui le tient fait attendre la note, sans « database is locked »."""
    quiz_id = await ready_quiz(seeded)
    attempt_id = await started_attempt(client, quiz_id, right=False)
    async with seeded.rt.program.program_lock(seeded.user_id, seeded.program_id):
        pending = asyncio.create_task(grade(seeded, attempt_id, FAIL_35))
        await asyncio.sleep(0.2)
        assert not pending.done()
        assert await count(seeded, QuizAttempt, status="grading") == 1
    assert (await pending).score == 35
    async with seeded.rt.session_factory() as db:
        task_id = (
            await db.execute(select(Task.id).where(Task.title == "Lire l'article A"))
        ).scalar_one()
    seeded.at(datetime(2026, 11, 19, 9, 0, tzinfo=UTC))  # nouvel essai permis
    second = await started_attempt(client, quiz_id, right=False)
    patch = TaskPatch(minutes=30)
    graded, moved = await asyncio.gather(
        grade(seeded, second, FAIL_35),
        move_or_edit_task(seeded.rt.program, seeded.user_id, task_id, patch),
    )
    assert graded.score == 35 and moved.minutes == 30


async def test_logs_carry_ids_only(
    client: httpx.AsyncClient, seeded: Seeded, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app.features")
    quiz_id = await ready_quiz(seeded)
    await grade(seeded, await started_attempt(client, quiz_id, right=False), FAIL_35)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert quiz_id in text and "Tentative rangée" in text
    for secret in ("Ma réponse", "softmax", "Elle normalise", "Module Bases", "Réviser"):
        assert secret not in text
