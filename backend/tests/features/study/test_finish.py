"""Le port `AgentStudyStore` sur la base réelle (D103) : fin rangée une fois (rejouée : relue),
tâches du bloc cochées selon la fin, acquis à `en_cours` au plus, fiches depuis les erreurs,
journal, verrou du programme pris avant la transaction (F4), contexte filtré par utilisatrice."""

import asyncio
import logging
from dataclasses import replace
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select, update

from app.core.errors import AppError
from app.core.skills import evidence
from app.db.models.lessons import Lesson
from app.db.models.program import Task
from app.db.models.skills import UserSkill
from app.db.models.study import Flashcard, JournalEntry, StudySession
from app.features.program.schemas import TaskPatch
from app.features.program.service.editing import move_or_edit_task
from app.features.skills.service import SkillsService
from app.features.study.service.store import AgentStudyStore
from tests.features.study.conftest import Seeded
from tests.features.study.stub import full_outcome
from tests.features.study.support import count, row, started


async def _open(
    client: httpx.AsyncClient, s: Seeded, worked: int | None = 45, lesson_id: str | None = None
) -> str:
    """Session ouverte sur le bloc du jour (ou la leçon `lesson_id`), minuteur déjà gardé
    (comme la route « Terminer »)."""
    body = {"lesson_id": lesson_id} if lesson_id else {}
    study_id = str((await started(client, **body))["study_session_id"])
    async with s.rt.session_factory() as db:
        await db.execute(
            update(StudySession).where(StudySession.id == study_id).values(worked_minutes=worked)
        )
        await db.commit()
    return study_id


async def _done_titles(s: Seeded) -> set[str]:
    async with s.rt.session_factory() as db:
        rows = await db.execute(select(Task.title).where(Task.status == "done"))
        return set(rows.scalars())


async def _evidence(s: Seeded) -> int:
    async with s.rt.session_factory() as db:
        rows = (await db.execute(select(UserSkill.evidence))).scalars().all()
        return sum(len(e) for e in rows)


async def test_finish_replayed_writes_once(client: httpx.AsyncClient, seeded: Seeded) -> None:
    """Rejeu de `wrap_up` après l'écriture : la même fin, rien en double (tâches, fiches,
    journal, preuves, temps) ; deux appels simultanés n'écrivent qu'une fois."""
    study_id = await _open(client, seeded)
    store = AgentStudyStore(seeded.rt)
    first, second = await asyncio.gather(
        store.finish(seeded.user_id, "s-tutor", study_id, full_outcome()),
        store.finish(seeded.user_id, "s-tutor", study_id, full_outcome()),
    )
    marks = [
        await count(seeded, Task, status="done"),
        await count(seeded, Flashcard),
        await count(seeded, JournalEntry),
        await _evidence(seeded),
    ]
    replayed = await store.finish(seeded.user_id, "s-tutor", study_id, full_outcome())
    assert first == second == replayed
    assert marks == [3, 3, 1, 3]
    assert [
        await count(seeded, Task, status="done"),
        await count(seeded, Flashcard),
        await count(seeded, JournalEntry),
        await _evidence(seeded),
    ] == marks
    assert (await row(seeded, study_id)).minutes == 45


async def test_finish_ticks_block_tasks_and_raises_en_cours_not_valide(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    async with seeded.rt.session_factory() as db:
        proof = evidence("quiz", "q1", "Quiz réussi", datetime(2026, 11, 10, tzinfo=UTC))
        await SkillsService(db, seeded.user_id).raise_levels(["pandas"], "valide", proof)
        await db.commit()
    study_id = await _open(client, seeded)
    done = await AgentStudyStore(seeded.rt).finish(
        seeded.user_id, "s-tutor", study_id, full_outcome()
    )
    assert done.minutes == 45
    assert done.tasks_done == ["Lire le chapitre 1", "Pratiquer les bases", "Lire le chapitre 2"]
    assert await _done_titles(seeded) == set(done.tasks_done)  # ni le quiz ni la suite
    assert sorted(done.skills) == [("Index", "en_cours"), ("Séries", "en_cours")]
    async with seeded.rt.session_factory() as db:
        levels = await SkillsService(db, seeded.user_id).levels_of(["pandas", "Index"])
        cards = (await db.execute(select(Flashcard))).scalars().all()
        [entry] = (await db.execute(select(JournalEntry))).scalars().all()
    assert dict(levels) == {"pandas": "valide", "Index": "en_cours"}  # jamais baissé ni validé
    assert sorted(c.front for c in cards) == [
        "Calcule la softmax.",
        "Pourquoi la racine ?",
        "Que cache le masque ?",
    ]  # partiel, faux, solution vue ; ni juste ni passé
    assert {(c.source, c.source_id, c.module_id) for c in cards} == {
        ("study", study_id, seeded.modules[0])
    }
    assert entry.kind == "study_session" and entry.ref_key == f"study:{study_id}"
    assert entry.text == "Session « Module Bases » : 45 min, 3 tâches cochées, 3 fiches."
    assert entry.study_session_id == study_id and entry.session_id is not None


async def test_ended_early_does_not_tick_reading_tasks(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    study_id = await _open(client, seeded)
    done = await AgentStudyStore(seeded.rt).finish(
        seeded.user_id, "s-tutor", study_id, full_outcome(ended_early=True)
    )
    assert done.tasks_done == ["Pratiquer les bases"]


@pytest.mark.parametrize("verdict", ["revealed", "skipped", "wrong"])
async def test_exercise_not_done_does_not_tick_practice(
    client: httpx.AsyncClient, seeded: Seeded, verdict: str
) -> None:
    """F13 : seuls `correct` et `partial` cochent la pratique."""
    study_id = await _open(client, seeded, worked=None)
    done = await AgentStudyStore(seeded.rt).finish(
        seeded.user_id, "s-tutor", study_id, full_outcome(exercise=verdict)
    )
    assert done.tasks_done == ["Lire le chapitre 1", "Lire le chapitre 2"]
    assert done.minutes == 0


async def test_finish_after_cancel_writes_nothing(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    study_id = await _open(client, seeded)
    async with seeded.rt.session_factory() as db:
        await db.execute(
            update(StudySession).where(StudySession.id == study_id).values(status="cancelled")
        )
        await db.commit()
    done = await AgentStudyStore(seeded.rt).finish(
        seeded.user_id, "s-tutor", study_id, full_outcome()
    )
    assert (done.minutes, done.tasks_done, done.flashcards_created) == (0, [], 0)
    assert await count(seeded, JournalEntry) == 0 and await count(seeded, Flashcard) == 0


async def test_finish_waits_for_the_program_lock(client: httpx.AsyncClient, seeded: Seeded) -> None:
    """F4 : le verrou du programme est pris AVANT la transaction d'écriture ; un déplacement de
    tâche qui le tient fait attendre la fin, sans « database is locked »."""
    study_id = await _open(client, seeded)
    store = AgentStudyStore(seeded.rt)
    async with seeded.rt.program.program_lock(seeded.user_id, seeded.program_id):
        pending = asyncio.create_task(
            store.finish(seeded.user_id, "s-tutor", study_id, full_outcome())
        )
        await asyncio.sleep(0.2)
        assert not pending.done()
        assert (await row(seeded, study_id)).status == "open"
    assert (await pending).minutes == 45
    second = await _open(client, seeded, lesson_id=seeded.lessons[1])
    patch = TaskPatch(minutes=30)
    done, moved = await asyncio.gather(
        store.finish(seeded.user_id, "s-tutor", second, full_outcome()),
        move_or_edit_task(
            seeded.rt.program, seeded.user_id, seeded.tasks["Lire l'article A"], patch
        ),
    )
    assert done.minutes == 45 and moved.minutes == 30


async def test_context_is_filtered_by_user(client: httpx.AsyncClient, seeded: Seeded) -> None:
    study_id = await _open(client, seeded)
    store = AgentStudyStore(seeded.rt)
    for call in (
        store.context("un-autre-utilisateur", study_id),
        store.finish("un-autre-utilisateur", "s-tutor", study_id, full_outcome()),
    ):
        with pytest.raises(AppError) as caught:
            await call
        assert caught.value.code == "study_session_not_found" and caught.value.status_code == 404
    assert (await row(seeded, study_id)).status == "open"


async def test_context_drops_an_exercise_without_solution(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    """m4 : jamais un « Voir la solution » vide ; l'exercice sans corrigé est omis."""
    study_id = await _open(client, seeded)
    async with seeded.rt.session_factory() as db:
        lesson = await db.get(Lesson, seeded.lessons[0])
        assert lesson is not None
        start = lesson.markdown.index("## Corrigé de l'exercice")
        end = lesson.markdown.index("## Sources")
        lesson.markdown = lesson.markdown[:start] + lesson.markdown[end:]
        await db.commit()
    found = await AgentStudyStore(seeded.rt).context(seeded.user_id, study_id)
    assert (found.exercise, found.solution) == ("", "")
    assert len(found.sections) == 5


async def test_logs_carry_ids_only(
    client: httpx.AsyncClient, seeded: Seeded, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app.features")
    study_id = await _open(client, seeded)
    outcome = replace(full_outcome(), summary="Bilan très personnel")
    await AgentStudyStore(seeded.rt).finish(seeded.user_id, "s-tutor", study_id, outcome)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert study_id in text and "Session guidée rangée" in text
    for secret in ("softmax", "Bilan très personnel", "Module Bases", "Lire le chapitre", "pandas"):
        assert secret not in text
