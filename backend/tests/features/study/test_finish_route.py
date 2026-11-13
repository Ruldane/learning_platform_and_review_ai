"""« Terminer » et « Abandonner » (`PATCH`, D103) sur le vrai moteur : parcours `study_session` de
test (`stub.py`) qui lit et range par le vrai port `AgentStudyStore`, branché au démarrage."""

import asyncio
from datetime import timedelta
from typing import Any

import httpx
import pytest

from app.core.errors import AppError
from app.db.models.program import Task
from app.db.models.study import Flashcard, JournalEntry, StudySession
from app.features.study.service.store import AgentStudyStore
from tests.features.study.conftest import Seeded
from tests.features.study.stub import StubControl
from tests.features.study.support import count, patch, row, started, study
from tests.sessions_support import wait_status


async def _waiting(client: httpx.AsyncClient, s: Seeded, **body: Any) -> dict[str, Any]:
    """Session ouverte sur la leçon du premier module, Tuteur en attente d'une réponse ; horloge
    de l'étude réglée à 7 min 10 s après le départ."""
    out = await started(client, lesson_id=s.lessons[0], **body)
    await wait_status(client, out["session_id"], "waiting_user")
    began = (await row(s, out["study_session_id"])).created_at
    s.at(began + timedelta(minutes=7, seconds=10))
    return out


async def _finished(client: httpx.AsyncClient, out: dict[str, Any]) -> dict[str, Any]:
    await wait_status(client, out["session_id"], "completed")
    return await study(client, out["study_session_id"])


async def test_study_port_is_wired_at_startup(
    client: httpx.AsyncClient, tutored: Seeded, stub_tutor: StubControl
) -> None:
    """Plus de `NO_STUDY` au démarrage réel : le parcours lit la séance par le vrai port."""
    out = await _waiting(client, tutored, question="Et le masque ?")
    [context] = stub_tutor.contexts
    assert context.study_session_id == out["study_session_id"]
    assert context.question == "Et le masque ?" and len(context.sections) == 5
    runner_ports = tutored.app.state.runtime.runner._ctx.ports
    assert isinstance(runner_ports.study, AgentStudyStore)


async def test_finish_records_minutes_clamped_to_wall_time(
    client: httpx.AsyncClient, tutored: Seeded, stub_tutor: StubControl
) -> None:
    out = await _waiting(client, tutored)
    r = await patch(client, out["study_session_id"], action="finish", worked_minutes=600)
    assert r.status_code == 202
    done = await _finished(client, out)
    assert done["status"] == "finished" and done["minutes"] == 8  # 7 min 10 s, minute entamée
    assert done["summary"] == "Bonne séance : la softmax est acquise."
    assert done["tasks_done"] == ["Lire le chapitre 1", "Pratiquer les bases", "Lire le chapitre 2"]
    assert done["flashcards_created"] == 3
    assert sorted((g["name"], g["level"]) for g in done["skills"]) == [
        ("Index", "en_cours"),
        ("Séries", "en_cours"),
        ("pandas", "en_cours"),
    ]
    assert stub_tutor.finished[0]["minutes"] == 8


async def test_finish_without_worked_minutes_counts_zero(
    client: httpx.AsyncClient, tutored: Seeded
) -> None:
    out = await _waiting(client, tutored)
    assert (await patch(client, out["study_session_id"], action="finish")).status_code == 202
    assert (await _finished(client, out))["minutes"] == 0


async def test_finish_while_tutor_writes_is_409(
    client: httpx.AsyncClient, tutored: Seeded, stub_tutor: StubControl
) -> None:
    stub_tutor.hold = asyncio.Event()
    out = await started(client, lesson_id=tutored.lessons[0])
    await wait_status(client, out["session_id"], "running")
    r = await patch(client, out["study_session_id"], action="finish", worked_minutes=5)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "study_not_waiting"
    assert (await row(tutored, out["study_session_id"])).worked_minutes is None
    stub_tutor.hold.set()
    await wait_status(client, out["session_id"], "waiting_user")
    assert (await patch(client, out["study_session_id"], action="finish")).status_code == 202
    assert (await _finished(client, out))["status"] == "finished"


async def test_finish_twice_is_idempotent(
    client: httpx.AsyncClient, tutored: Seeded, stub_tutor: StubControl
) -> None:
    out = await _waiting(client, tutored)
    sid = out["study_session_id"]
    first, second = await asyncio.gather(
        patch(client, sid, action="finish", worked_minutes=5),
        patch(client, sid, action="finish", worked_minutes=7),
    )
    assert (first.status_code, second.status_code) == (202, 202)
    done = await _finished(client, out)
    assert done["minutes"] in (5, 7) and len(stub_tutor.finished) == 1  # le premier servi
    again = await patch(client, sid, action="finish", worked_minutes=9)
    assert again.status_code == 202 and again.json() == done
    assert await count(tutored, JournalEntry) == 1
    assert await count(tutored, Flashcard) == 3


async def test_cancel_writes_nothing(
    client: httpx.AsyncClient, tutored: Seeded, stub_tutor: StubControl
) -> None:
    out = await _waiting(client, tutored)
    sid = out["study_session_id"]
    r = await patch(client, sid, action="cancel", worked_minutes=30)
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "cancelled" and body["minutes"] == 0 and body["tasks_done"] == []
    await wait_status(client, out["session_id"], "cancelled")
    assert await count(tutored, Task, status="done") == 0
    assert await count(tutored, JournalEntry) == 0 and await count(tutored, Flashcard) == 0
    after = await patch(client, sid, action="finish", worked_minutes=30)
    assert after.status_code == 202 and after.json()["status"] == "cancelled"
    assert stub_tutor.finished == []


async def test_finish_after_tutor_failed_still_records_time(
    client: httpx.AsyncClient, tutored: Seeded, stub_tutor: StubControl
) -> None:
    """Session d'agents échouée en route : lue `interrupted`, « Terminer » range le temps
    (sans résultat de questions : ni lecture cochée, ni fiche)."""
    stub_tutor.fail = True
    out = await started(client, lesson_id=tutored.lessons[0])
    await wait_status(client, out["session_id"], "failed")
    sid = out["study_session_id"]
    assert (await study(client, sid))["status"] == "interrupted"
    began = (await row(tutored, sid)).created_at
    tutored.at(began + timedelta(minutes=12))
    r = await patch(client, sid, action="finish", worked_minutes=10)
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "finished" and body["minutes"] == 10 and body["tasks_done"] == []
    assert body["flashcards_created"] == 0
    assert await count(tutored, JournalEntry, kind="study_session") == 1


async def test_finish_resumes_when_minutes_were_kept_but_not_sent(
    client: httpx.AsyncClient, tutored: Seeded
) -> None:
    """Temps gardé puis arrêt du back avant la reprise : la question attend encore, le
    « Terminer » suivant reprend (jamais une session bloquée « en fin »)."""
    out = await _waiting(client, tutored)
    async with tutored.rt.session_factory() as db:
        found = await db.get(StudySession, out["study_session_id"])
        assert found is not None
        found.worked_minutes = 3
        await db.commit()
    r = await patch(client, out["study_session_id"], action="finish", worked_minutes=4)
    assert r.status_code == 202
    assert (await _finished(client, out))["minutes"] == 4


async def test_second_finish_without_minutes_keeps_the_kept_time(
    client: httpx.AsyncClient, tutored: Seeded, stub_tutor: StubControl
) -> None:
    """m3 : temps gardé (45 min), le Tuteur échoue après la reprise ; le « Terminer » suivant,
    sans minuteur, ne l'écrase pas par 0 (absent n'efface jamais une valeur gardée)."""
    stub_tutor.fail = True
    out = await started(client, lesson_id=tutored.lessons[0])
    await wait_status(client, out["session_id"], "failed")
    sid = out["study_session_id"]
    async with tutored.rt.session_factory() as db:
        found = await db.get(StudySession, sid)
        assert found is not None
        found.worked_minutes = 45
        await db.commit()
    tutored.at((await row(tutored, sid)).created_at + timedelta(hours=2))
    r = await patch(client, sid, action="finish")
    assert r.status_code == 202 and r.json()["status"] == "finished"
    assert r.json()["minutes"] == 45


async def test_dead_session_with_kept_time_is_finished_on_next_start(
    client: httpx.AsyncClient, tutored: Seeded, stub_tutor: StubControl
) -> None:
    """Revue finale 5 (S-I1) : « Terminer » a gardé 45 min, puis le Tuteur a échoué avant de
    conclure. Le départ suivant range cette fin (temps, journal ; sans lecture cochée, aucun
    résultat de question n'étant connu) au lieu de l'annuler."""
    stub_tutor.fail = True
    out = await started(client, lesson_id=tutored.lessons[0])
    await wait_status(client, out["session_id"], "failed")
    sid = out["study_session_id"]
    async with tutored.rt.session_factory() as db:
        found = await db.get(StudySession, sid)
        assert found is not None
        found.worked_minutes = 45
        await db.commit()
    stub_tutor.fail = False
    second = await started(client, lesson_id=tutored.lessons[1])
    old = await study(client, sid)
    assert old["status"] == "finished" and old["minutes"] == 45 and old["tasks_done"] == []
    assert (await row(tutored, sid)).ended_at is not None
    assert await count(tutored, JournalEntry, kind="study_session") == 1
    assert (await row(tutored, second["study_session_id"])).status == "open"


async def test_failed_resume_keeps_previously_kept_time(
    client: httpx.AsyncClient, tutored: Seeded, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Revue finale 5 (S-m5) : 30 min gardées par un premier « Terminer » (arrêt du back avant
    la reprise) ; la reprise du second échoue : les 30 min restent, jamais remises à rien."""
    out = await _waiting(client, tutored)
    sid = out["study_session_id"]
    async with tutored.rt.session_factory() as db:
        found = await db.get(StudySession, sid)
        assert found is not None
        found.worked_minutes = 30
        await db.commit()

    async def stale(*args: Any, **kwargs: Any) -> None:
        raise AppError("stale_interrupt", "Question déjà répondue.", 409)

    monkeypatch.setattr("app.features.study.service.control._resume", stale)
    r = await patch(client, sid, action="finish", worked_minutes=5)
    assert (r.status_code, r.json()["error"]["code"]) == (409, "study_not_waiting")
    assert (await row(tutored, sid)).worked_minutes == 30
