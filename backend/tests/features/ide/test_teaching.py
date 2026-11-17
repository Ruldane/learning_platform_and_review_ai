"""La barrière de coût du professeur (10.A3) : ce qui réveille le modèle et ce qui ne le réveille
jamais, l'anti-répétition, les plafonds de jetons, la gradation des indices. Application réelle,
faux modèles scriptés : le nombre d'appels de `models` est ce que l'utilisatrice paierait."""

import asyncio
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import update

from app.db.base import utcnow
from app.db.models.ide import IdeNote, IdeSession
from tests.features.ide.support import API, FILES, new_session
from tests.features.ide.teach_support import (
    MAIN,
    SIGNATURE,
    ScriptedModels,
    add_failed_run,
    add_professor_note,
    add_teacher_tokens,
    note_json,
    set_preferences,
    teach,
    wait_done,
)

pytestmark = pytest.mark.usefixtures("me")


@pytest.fixture
async def session(client: httpx.AsyncClient) -> dict[str, Any]:
    return await new_session(client, {"main.py": MAIN, "test_main.py": FILES["test_main.py"]})


async def notes_of(client: httpx.AsyncClient, session_id: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = (await client.get(f"{API}/sessions/{session_id}/notes")).json()
    return found


async def test_unknown_trigger_is_422_and_no_call(
    client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    response = await teach(client, session["id"], "keystroke")
    assert response.status_code == 422
    assert models.calls == []


async def test_empty_question_is_422(
    client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    for question in (None, "", "   \n"):
        body = {"question": question} if question is not None else {}
        assert (await teach(client, session["id"], "question", **body)).status_code == 422
    assert models.calls == []


async def test_no_call_on_save_or_keystroke_routes(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    for _ in range(3):  # des frappes : des sauvegardes répétées des fichiers
        saved = await client.put(f"{API}/sessions/{sid}/files", json={"files": {"main.py": "x=1"}})
        assert saved.status_code == 200
    posted = await client.post(
        f"{API}/sessions/{sid}/notes", json={"kind": "hint", "content": "Une note à moi."}
    )
    assert posted.status_code == 201
    await client.get(f"{API}/sessions/{sid}/notes")
    await client.get(f"{API}/usage", params={"session_id": sid})
    assert models.calls == []
    assert not app.state.runtime.runner.is_active(sid)


async def test_run_ok_calls_nothing_until_passed_then_one_compliment(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    first = (await teach(client, sid, "run_ok")).json()
    assert first == {"session_id": None, "reference_note_id": None, "skipped": "on_demand"}
    async with app.state.session_factory() as db:
        row = await db.get(IdeSession, sid)
        assert row is not None
        row.passed_at = utcnow()
        await db.commit()
    once = (await teach(client, sid, "run_ok")).json()
    again = (await teach(client, sid, "run_ok")).json()
    assert once["reference_note_id"] and once == again
    [note] = await notes_of(client, sid)
    assert note["author"] == "professor" and note["id"] == once["reference_note_id"]
    assert models.calls == []  # un compliment ne coûte aucun appel


async def test_same_error_same_place_references_previous(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await add_failed_run(app, sid)
    previous = await add_professor_note(app, sid, SIGNATURE, kind="explanation")
    for _ in range(10):  # la même erreur dix fois
        sent = (await teach(client, sid, "run_error")).json()
        assert sent["reference_note_id"] == previous and sent["session_id"] is None
    assert models.calls == []
    notes = await notes_of(client, sid)
    references = [n for n in notes if n["kind"] == "reference"]
    assert len(references) == 1  # un seul renvoi écrit, pas dix
    assert references[0]["reference_note_id"] == previous and references[0]["author"] == "professor"


async def test_run_error_calls_once_then_references_its_own_note(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await add_failed_run(app, sid)
    models.replies += [note_json("hint", "Que vaut n à la ligne 3 ?", level=1)]
    started = (await teach(client, sid, "run_error")).json()
    await wait_done(client, started["session_id"])
    [first] = await notes_of(client, sid)
    assert first["kind"] == "hint" and first["level"] == 1 and first["author"] == "professor"
    again = (await teach(client, sid, "run_error")).json()
    assert again["reference_note_id"] == first["id"] and len(models.calls) == 1


async def test_hint_level_rises_with_hints_for_the_same_error(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await add_failed_run(app, sid)
    levels = []
    for _ in range(4):
        models.replies.append(note_json("hint", "Un indice."))
        started = (await teach(client, sid, "hint")).json()
        await wait_done(client, started["session_id"])
        levels.append([n["level"] for n in await notes_of(client, sid)][-1])
    assert levels == [1, 2, 3, 3]  # plafonné à 3


async def test_hint_uses_light_tier_explanation_uses_strong(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    models.replies += [note_json("hint"), note_json("explanation", "Une vraie explication.")]
    hint = (await teach(client, sid, "hint")).json()
    await wait_done(client, hint["session_id"])
    asked = (await teach(client, sid, "question", question="Pourquoi cette erreur ?")).json()
    await wait_done(client, asked["session_id"])
    assert [(c.tier, c.agent) for c in models.calls] == [
        ("rapide", "professor"),
        ("fort", "professor"),
    ]


async def test_session_cap_stops_automatic_triggers(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await set_preferences(app, session_cap=1_000, day_cap=10_000_000)
    await add_teacher_tokens(app, sid, 1_000)
    await add_failed_run(app, sid)
    assert (await teach(client, sid, "run_error")).json()["skipped"] == "cap_reached"
    assert models.calls == []
    usage = (await client.get(f"{API}/usage", params={"session_id": sid})).json()
    assert usage["mode_on_demand"] is True and usage["session_tokens"] == 1_000


async def test_day_cap_stops_automatic_triggers(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    other = await new_session(client)
    await set_preferences(app, session_cap=2_000_000, day_cap=1_000)
    await add_teacher_tokens(app, other["id"], 1_000)  # une autre séance, même jour
    await add_failed_run(app, sid)
    assert (await teach(client, sid, "run_error")).json()["skipped"] == "cap_reached"
    assert models.calls == []
    usage = (await client.get(f"{API}/usage", params={"session_id": sid})).json()
    assert usage["session_tokens"] == 0 and usage["day_tokens"] == 1_000
    assert usage["mode_on_demand"] is True


async def test_explicit_question_still_answered_after_cap(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await set_preferences(app, session_cap=1_000, day_cap=1_000)
    await add_teacher_tokens(app, sid, 5_000)
    models.replies += [note_json("explanation", "Voici."), note_json("hint")]
    asked = (await teach(client, sid, "question", question="Aide-moi ?")).json()
    assert asked["session_id"] and asked["skipped"] is None
    await wait_done(client, asked["session_id"])
    wanted = (await teach(client, sid, "hint")).json()  # un indice demandé est explicite aussi
    assert wanted["session_id"]
    await wait_done(client, wanted["session_id"])
    assert len(models.calls) == 2


async def test_on_demand_mode_stops_automatic_triggers_only(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await set_preferences(app, teacher_mode="on_demand")
    await add_failed_run(app, sid)
    assert (await teach(client, sid, "run_error")).json()["skipped"] == "on_demand"
    models.replies.append(note_json("hint"))
    assert (await teach(client, sid, "hint")).json()["session_id"]


async def test_one_teacher_call_at_a_time(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    models.hold = asyncio.Event()  # le premier appel reste en cours
    models.replies += [note_json("explanation", "Réponse."), note_json("explanation", "Autre.")]
    first = (await teach(client, sid, "question", question="Une question ?")).json()
    assert first["session_id"]
    second = (await teach(client, sid, "question", question="Une autre ?")).json()
    third = (await teach(client, sid, "hint")).json()
    assert second["skipped"] == "busy" and third["skipped"] == "busy"
    models.hold.set()
    await wait_done(client, first["session_id"])
    assert len(models.calls) == 1
    again = (await teach(client, sid, "question", question="Et maintenant ?")).json()
    assert again["session_id"]  # libre de nouveau
    await wait_done(client, again["session_id"])


async def test_idle_needs_option_and_30s(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    place = {"file_path": "main.py", "line": 5}
    assert (await teach(client, sid, "idle", **place)).json()["skipped"] == "on_demand"
    await set_preferences(app, idle_trigger=True)
    await add_professor_note(app, sid, "autre", kind="hint", age_s=5)  # il y a 5 s
    assert (await teach(client, sid, "idle", **place)).json()["skipped"] == "busy"
    assert models.calls == []
    async with app.state.session_factory() as db:  # la note date de plus de 30 s
        await db.execute(update(IdeNote).values(created_at=utcnow().replace(year=2020)))
        await db.commit()
    models.replies.append(note_json("hint"))
    started = (await teach(client, sid, "idle", **place)).json()
    assert started["session_id"]
    await wait_done(client, started["session_id"])
    repeated = (await teach(client, sid, "idle", **place)).json()  # même ligne : renvoi
    assert repeated["reference_note_id"] and len(models.calls) == 1
