"""Note d'une tentative (D101) : ≥ 80 % → acquis `valide` (preuve quiz, reflet mémoire) ;
< 80 % → révisions et nouvel essai dans le budget ; fiches depuis les erreurs ; tâche `quiz` de
la semaine cochée quand tous ses modules sont notés ; « Refaire le quiz » cochée (F18)."""

from datetime import UTC, date, datetime

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.core.skills import read_evidence
from app.db.models.program import Task
from app.db.models.skills import Skill, UserSkill
from app.db.models.study import Flashcard, JournalEntry
from app.features.memory.service.skill_levels import acquis_levels
from tests.features.program.support import CAP, view
from tests.features.quiz.conftest import SKILLS, Seeded, seed
from tests.features.quiz.support import FAIL_35, PASS_85, grade, ready_quiz, started_attempt
from tests.support.program import module, plan, task, week


async def _levels(s: Seeded) -> dict[str, tuple[str, list[object]]]:
    async with s.rt.session_factory() as db:
        stmt = select(Skill.name, UserSkill.level, UserSkill.evidence).join(
            UserSkill, UserSkill.skill_id == Skill.id
        )
        return {row[0]: (row[1], list(row[2])) for row in (await db.execute(stmt)).all()}


async def _tasks(s: Seeded) -> list[Task]:
    async with s.rt.session_factory() as db:
        rows = await db.execute(select(Task).where(Task.program_id == s.program_id))
        return list(rows.scalars().all())


async def _journal(s: Seeded) -> list[str]:
    async with s.rt.session_factory() as db:
        return list((await db.execute(select(JournalEntry.text))).scalars().all())


async def test_passing_attempt_raises_skills_to_valide(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    quiz_id = await ready_quiz(seeded)
    attempt_id = await started_attempt(client, quiz_id)
    saved = await grade(seeded, attempt_id, PASS_85)
    assert (saved.score, saved.passed, saved.followup_tasks) == (85, True, 0)
    levels = await _levels(seeded)
    assert {name: level for name, (level, _) in levels.items()} == dict.fromkeys(SKILLS, "valide")
    [proof] = read_evidence(levels["pandas"][1])
    assert (proof["kind"], proof["ref_id"]) == ("quiz", quiz_id)  # F21
    assert proof["label"] == "Quiz « Module Bases » : 85 % (17/11)"
    async with seeded.rt.session_factory() as db:
        memory = await acquis_levels(db, seeded.user_id)
    assert memory["pandas"] == "valide" and memory["series"] == "valide"
    assert await _journal(seeded) == ["Quiz « Module Bases » : 85 % — acquis validés."]
    quiz_task = next(t for t in await _tasks(seeded) if t.title == "Faire le quiz 1")
    assert quiz_task.status == "done"  # un seul module en semaine 1


async def test_failing_attempt_adds_followup_within_budget(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    quiz_id = await ready_quiz(seeded)
    attempt_id = await started_attempt(client, quiz_id, right=False)
    saved = await grade(seeded, attempt_id, FAIL_35)
    assert (saved.score, saved.passed, saved.followup_tasks) == (35, False, 4)
    out = (await client.get(f"/api/v1/quizzes/{quiz_id}/attempts/{attempt_id}")).json()
    followup = out["followup"]
    assert followup["revision_tasks"] == [f"Réviser : {skill}" for skill in SKILLS]
    assert followup["retry_on"] == "2026-11-19" and followup["unplaced"] == 0
    added = {t.title: t.planned_date for t in await _tasks(seeded) if t.title.startswith("R")}
    assert added == {
        "Réviser : pandas": date(2026, 11, 18),  # dès demain, semaine 1 (665 → 685)
        "Réviser : Séries": date(2026, 11, 18),  # 705
        "Réviser : Index": date(2026, 11, 23),  # 725 > 714 : semaine 2
        "Refaire le quiz : Module Bases": date(2026, 11, 23),  # au plus tôt J+2, même raison
    }
    program = await view(client, seeded.program_id)
    assert all(w["load_minutes"] <= CAP for w in program["weeks"])
    assert await _journal(seeded) == [
        "Quiz « Module Bases » : 35 % — 3 révisions et un nouvel essai le 19/11."
    ]
    assert {level for level, _ in (await _levels(seeded)).values()} <= {"en_cours", "declare"}


async def test_followup_without_room_is_reported_unplaced(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    """Samedi de la dernière semaine : demain est un dimanche, puis le programme est fini."""
    seeded.at(datetime(2026, 11, 28, 10, 0, tzinfo=UTC))
    quiz_id = await ready_quiz(seeded)
    attempt_id = await started_attempt(client, quiz_id, right=False)
    saved = await grade(seeded, attempt_id, FAIL_35)
    assert saved.followup_tasks == 0
    out = (await client.get(f"/api/v1/quizzes/{quiz_id}/attempts/{attempt_id}")).json()
    assert out["followup"] == {"revision_tasks": [], "retry_on": "2026-11-30", "unplaced": 4}


async def test_errors_become_cards_due_tomorrow(client: httpx.AsyncClient, seeded: Seeded) -> None:
    quiz_id = await ready_quiz(seeded)
    attempt_id = await started_attempt(client, quiz_id, right=False)
    saved = await grade(seeded, attempt_id, [1, 1, 1, 1, 1, 1, 0.5])
    async with seeded.rt.session_factory() as db:
        rows = (await db.execute(select(Flashcard).where(Flashcard.source == "quiz"))).scalars()
        cards = list(rows)
    # 3 QCM faux, 1 ouverte à 0,5 ; mais les énoncés de `quiz_draft` diffèrent par leur numéro.
    assert saved.cards_created == len(cards) == 4
    assert {c.due_date for c in cards} == {date(2026, 11, 18)}
    assert all(c.source_id == attempt_id and c.step == 0 for c in cards)
    qcm = next(c for c in cards if c.front.startswith("Question 1 "))
    assert qcm.back.startswith("Elle normalise")


async def test_week_quiz_task_ticked_when_all_modules_graded(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    reads = [task(f"Lire {n}", minutes=120) for n in range(1, 4)]
    first = module("Module A", [*reads, task("Pratiquer", "pratiquer", 45), task("Quiz", "quiz")])
    second = module("Module B", [task("Lire B", minutes=60)])
    draft = plan([week("Bases", [first, second]), week("Suite", [first.model_copy()])])
    s = await seed(app, draft, ready=2)
    quiz_a, quiz_b = await ready_quiz(s, 0), await ready_quiz(s, 1)

    def week_quiz(tasks: list[Task]) -> str:
        return next(t.status for t in tasks if t.title == "Quiz" and t.module_id == s.modules[0])

    await grade(s, await started_attempt(client, quiz_a), PASS_85)
    assert week_quiz(await _tasks(s)) == "todo"  # le module B n'est pas noté
    await grade(s, await started_attempt(client, quiz_b, right=False), FAIL_35)
    assert week_quiz(await _tasks(s)) == "done"  # noté suffit, réussi ou non


async def test_graded_attempt_ticks_retry_task(client: httpx.AsyncClient, seeded: Seeded) -> None:
    """F18 : la tentative suivante coche « Refaire le quiz : {module} »."""
    quiz_id = await ready_quiz(seeded)
    await grade(seeded, await started_attempt(client, quiz_id, right=False), FAIL_35)
    seeded.at(datetime(2026, 11, 23, 9, 0, tzinfo=UTC))
    await grade(seeded, await started_attempt(client, quiz_id), PASS_85)
    retry = next(t for t in await _tasks(seeded) if t.title.startswith("Refaire le quiz"))
    assert retry.status == "done"
