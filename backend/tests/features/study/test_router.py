"""Départ d'une session guidée, résumé et isolation (D103) : lanceur factice, aucune session
réelle ; la fin passe par `test_finish_route.py` (vrai moteur, parcours de test)."""

import asyncio
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI
from sqlalchemy import update

from app.db.models.lessons import Lesson
from app.db.models.program import Task
from app.db.models.study import StudySession
from app.features.study.service.store import AgentStudyStore
from tests.features.study.conftest import BLOCK, MONDAY, Seeded, seed
from tests.features.study.support import API, count, row, start, started, study
from tests.sessions_support import act_as


async def test_start_block_picks_today_tasks_of_first_ready_module(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    body = await started(client)
    assert body["lesson_id"] == seeded.lessons[0] and body["session_id"]
    found = await row(seeded, body["study_session_id"])
    assert found.task_ids == [seeded.tasks[t] for t in BLOCK]  # retard d'abord, sans le quiz
    assert found.mode == "socratic" and found.status == "open" and found.question is None
    assert seeded.launcher is not None
    assert seeded.launcher.started == [
        ("study_session", {"study_session_id": body["study_session_id"]})
    ]
    summary = (await client.get(f"{API}/summary")).json()
    assert summary["open_session_id"] == body["study_session_id"]
    assert [t["title"] for t in summary["block"]["tasks"]] == BLOCK
    assert summary["block"]["module_title"] == "Module Bases"
    assert summary["block"]["tasks"][1] == {
        "id": seeded.tasks["Pratiquer les bases"],
        "title": "Pratiquer les bases",
        "minutes": 45,
        "type": "pratiquer",
    }


async def test_block_skips_a_module_whose_lesson_is_not_ready(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    s = await seed(app, ready=(False, True))
    async with s.rt.session_factory() as db:
        await db.execute(
            update(Task).where(Task.id == s.tasks["Lire l'article A"]).values(planned_date=MONDAY)
        )
        await db.commit()
    body = await started(client)
    assert body["lesson_id"] == s.lessons[1]
    assert (await row(s, body["study_session_id"])).task_ids == [s.tasks["Lire l'article A"]]


async def test_no_block_today_is_404(client: httpx.AsyncClient, app: FastAPI) -> None:
    await seed(app, ready=(False, False))
    r = await start(client)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "no_block_today"
    assert r.json()["error"]["message"] == "Rien de prévu aujourd'hui : choisis une leçon."
    assert (await client.get(f"{API}/summary")).json()["block"] is None


async def test_draft_program_has_no_block(client: httpx.AsyncClient, app: FastAPI) -> None:
    await seed(app, validated=False)
    assert (await start(client)).status_code == 404


async def test_concurrent_starts_open_one_session(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    first, second = await asyncio.gather(start(client), start(client))
    assert sorted([first.status_code, second.status_code]) == [200, 202]
    assert first.json()["study_session_id"] == second.json()["study_session_id"]
    assert await count(seeded, StudySession) == 1
    assert seeded.launcher is not None and len(seeded.launcher.started) == 1


async def test_start_with_question_passes_it_to_the_graph(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    body = await started(
        client, lesson_id=seeded.lessons[0], mode="feynman", question="  Pourquoi la racine ?  "
    )
    found = await AgentStudyStore(seeded.rt).context(seeded.user_id, body["study_session_id"])
    assert found.question == "Pourquoi la racine ?" and found.mode == "feynman"
    assert found.module_title == "Module Bases"
    assert [s.title for s in found.sections] == [
        "L'essentiel en 5 lignes",
        "Explication",
        "Schémas",
        "Exemple travaillé",
        "Erreurs fréquentes",
    ]
    assert found.exercise.startswith("Calculer") and found.solution.startswith("Les poids")
    assert [(c.index, c.title) for c in found.sources] == [
        (1, "Premier article"),
        (2, "Second article"),
    ]


async def test_open_session_same_lesson_200_other_lesson_409(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    body = await started(client, lesson_id=seeded.lessons[0])
    again = await start(client, lesson_id=seeded.lessons[0], mode="direct")
    assert again.status_code == 200 and again.json() == body
    other = await start(client, lesson_id=seeded.lessons[1])
    assert other.status_code == 409
    error = other.json()["error"]
    assert error["code"] == "study_already_open"
    assert error["details"] == {"study_session_id": body["study_session_id"]}


async def test_lesson_not_ready_or_unknown(client: httpx.AsyncClient, app: FastAPI) -> None:
    s = await seed(app, ready=(True, False))
    r = await start(client, lesson_id=s.lessons[1])
    assert r.status_code == 409 and r.json()["error"]["code"] == "lesson_not_ready"
    r = await start(client, lesson_id="inconnue")
    assert r.status_code == 404 and r.json()["error"]["code"] == "lesson_not_found"


async def test_question_too_long_is_422_without_echo(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    secret = "secret-" + "x" * 2000
    r = await start(client, lesson_id=seeded.lessons[0], question=secret)
    assert r.status_code == 422 and "secret-" not in r.text


async def test_dead_open_session_is_shown_interrupted_then_cancelled_on_start(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    """F11 : lue `interrupted` sans écriture ; annulée au départ suivant, dans la même
    transaction que l'insertion de la nouvelle."""
    first = await started(client, lesson_id=seeded.lessons[0])
    assert seeded.launcher is not None
    await seeded.launcher.end(seeded.user_id, first["session_id"], "failed")
    assert (await study(client, first["study_session_id"]))["status"] == "interrupted"
    assert (await row(seeded, first["study_session_id"])).status == "open"
    second = await started(client, lesson_id=seeded.lessons[1])
    assert (await row(seeded, first["study_session_id"])).status == "cancelled"
    assert (await row(seeded, second["study_session_id"])).status == "open"


async def test_refused_launch_leaves_session_cancelled(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    assert seeded.launcher is not None
    seeded.launcher.refuse = True
    r = await start(client)
    assert r.status_code == 503
    assert await count(seeded, StudySession, status="cancelled") == 1
    seeded.launcher.refuse = False
    await started(client)


async def test_summary_streak_and_week_minutes_in_local_time(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    """Paris (UTC+1) : une fin à 23 h 30 UTC compte le lendemain ; la semaine va du lundi au
    dimanche locaux ; une session abandonnée ne compte pas."""
    ended = [
        (datetime(2026, 11, 14, 10, 0, tzinfo=UTC), 30, "finished"),  # samedi : trou dimanche
        (datetime(2026, 11, 15, 23, 30, tzinfo=UTC), 20, "finished"),  # lundi 0 h 30 local
        (datetime(2026, 11, 16, 23, 30, tzinfo=UTC), 25, "finished"),  # mardi 0 h 30 local
        (datetime(2026, 11, 17, 8, 0, tzinfo=UTC), 99, "cancelled"),
    ]
    async with seeded.rt.session_factory() as db:
        for at, minutes, status in ended:
            db.add(
                StudySession(
                    user_id=seeded.user_id,
                    lesson_id=seeded.lessons[0],
                    module_id=seeded.modules[0],
                    program_id=seeded.program_id,
                    mode="socratic",
                    status=status,
                    minutes=minutes,
                    ended_at=at,
                )
            )
        await db.commit()
    summary = (await client.get(f"{API}/summary")).json()
    assert summary["streak_days"] == 2 and summary["week_minutes"] == 45
    assert (summary["work_minutes"], summary["break_minutes"]) == (50, 10)
    assert summary["open_session_id"] is None


async def test_study_routes_isolate_users(client: httpx.AsyncClient, seeded: Seeded) -> None:
    body = await started(client)
    sid = body["study_session_id"]
    act_as(seeded.app, "un-autre-utilisateur")
    assert (await client.get(f"{API}/{sid}")).status_code == 404
    r = await client.patch(f"{API}/{sid}", json={"action": "cancel"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "study_session_not_found"
    summary = (await client.get(f"{API}/summary")).json()
    assert summary["open_session_id"] is None and summary["block"] is None
    r = await start(client, lesson_id=seeded.lessons[0])
    assert r.status_code == 404
    async with seeded.rt.session_factory() as db:
        lesson = await db.get(Lesson, seeded.lessons[0])
        assert lesson is not None and lesson.user_id == seeded.user_id
