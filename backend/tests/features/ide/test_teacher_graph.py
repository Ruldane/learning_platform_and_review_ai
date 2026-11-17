"""Le parcours `ide_teacher` de bout en bout (10.A3) : application réelle, port de l'IDE réel, faux
modèles. Le début de prompt fixe, le contexte borné, les règles du mode guide et du binôme, le
niveau de modèle et le journal d'un appel (séance, modèle, jetons, rien d'autre)."""

import asyncio
import logging
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.features.ide.service import file_hash
from app.providers.llm.base import CACHE_PREFIX_KEY
from tests.features.ide.support import API, FILES, new_session
from tests.features.ide.teach_support import (
    MAIN,
    ScriptedModels,
    add_failed_run,
    note_json,
    set_preferences,
    teach,
    wait_done,
)

pytestmark = pytest.mark.usefixtures("me")

LONG_CODE = "```python\n" + "\n".join(f"x{n} = {n}" for n in range(8)) + "\n```"
QUESTION = "Pourquoi mon programme plante-t-il ?"


@pytest.fixture
async def session(client: httpx.AsyncClient) -> dict[str, Any]:
    return await new_session(client, {"main.py": MAIN, "test_main.py": FILES["test_main.py"]})


async def ask(client: httpx.AsyncClient, sid: str, **body: Any) -> dict[str, Any]:
    sent = (await teach(client, sid, "question", question=QUESTION, **body)).json()
    await wait_done(client, sent["session_id"])
    notes: list[dict[str, Any]] = (await client.get(f"{API}/sessions/{sid}/notes")).json()
    return notes[-1]


async def test_prompt_prefix_is_byte_stable_between_calls(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    models.replies += [note_json("explanation", "Un."), note_json("explanation", "Deux.")]
    await ask(client, sid, file_path="main.py", line=10)
    await add_failed_run(app, sid)
    await ask(client, sid, file_path="main.py", line=90)
    first, second = (messages[0] for messages in models.received[:2])
    assert first.content == second.content and first.additional_kwargs == second.additional_kwargs
    assert first.additional_kwargs == {CACHE_PREFIX_KEY: True}
    assert models.received[0][1].content != models.received[1][1].content  # le reste change
    assert "line_10 = 10" not in str(first.content)  # le début fixe ne porte aucun code


async def test_context_sent_is_bounded_to_one_file(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    models.replies.append(note_json("explanation", "Réponse."))
    await ask(client, sid, file_path="main.py", line=60)
    system, turn = models.received[0][0], models.received[0][1]
    text = str(turn.content)
    assert "line_30 = 30" in text and "line_90 = 90" in text  # ±30 lignes
    assert "line_29 = 29" not in text and "line_91 = 91" not in text
    assert "test_ok" not in text + str(system.content)  # jamais un second fichier
    assert QUESTION in text


async def test_guide_note_has_no_replacement_or_long_code(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    models.replies.append(
        note_json(
            "proposal",
            f"Essaie ceci :\n{LONG_CODE}\nEt un petit `x = 1` en ligne.",
            path="main.py",
            start_line=2,
            end_line=3,
            replacement="    return 1",
        )
    )
    note = await ask(client, sid, file_path="main.py", line=2)
    assert note["kind"] == "explanation" and note["replacement"] is None
    assert note["base_hash"] is None and "x7 = 7" not in note["content"]
    assert "`x = 1`" in note["content"]  # le code court reste
    assert "démarche" in note["content"]


async def test_hint_level_three_never_contains_code(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await add_failed_run(app, sid)
    for _ in range(3):
        models.replies.append(note_json("hint", "Étape :\n```python\nx = 1\n```\nPuis relance."))
        sent = (await teach(client, sid, "hint")).json()
        await wait_done(client, sent["session_id"])
    notes: list[dict[str, Any]] = (await client.get(f"{API}/sessions/{sid}/notes")).json()
    assert [n["level"] for n in notes] == [1, 2, 3]
    assert "x = 1" in notes[0]["content"] and "x = 1" not in notes[2]["content"]
    assert "Niveau 3" in str(models.received[2][1].content)


async def test_binome_proposal_has_range_and_base_hash(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await set_preferences(app, teacher_style="pair")
    models.replies.append(
        note_json(
            "proposal",
            "J'ai remplacé la ligne 4.",
            path="main.py",
            start_line=4,
            end_line=5,
            replacement="line_4 = 40\nline_5 = 50",
        )
    )
    note = await ask(client, sid, file_path="main.py", line=4)
    assert note["kind"] == "proposal" and note["author"] == "professor"
    assert (note["line_start"], note["line_end"]) == (4, 5)
    assert note["replacement"] == "line_4 = 40\nline_5 = 50" and note["status"] == "open"
    assert note["base_hash"] == file_hash(MAIN)
    assert (await client.post(f"{API}/notes/{note['id']}/accept")).status_code == 200
    saved = (await client.get(f"{API}/sessions/{sid}")).json()["files"]["main.py"]
    assert "line_4 = 40" in saved and "line_5 = 50" in saved


async def test_binome_proposal_outside_the_shown_file_becomes_an_explanation(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await set_preferences(app, teacher_style="pair")
    models.replies.append(
        note_json(
            "proposal",
            "Dans l'autre fichier.",
            path="test_main.py",
            start_line=1,
            replacement="x = 1",
        )
    )
    note = await ask(client, sid, file_path="main.py", line=4)
    assert note["kind"] == "explanation" and note["replacement"] is None


async def test_binome_run_error_is_a_margin_annotation_on_the_light_tier(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await set_preferences(app, teacher_style="pair")
    await add_failed_run(app, sid)
    models.replies.append(note_json("explanation", "Ici ça coince."))  # le code force le type
    sent = (await teach(client, sid, "run_error")).json()
    await wait_done(client, sent["session_id"])
    [note] = (await client.get(f"{API}/sessions/{sid}/notes")).json()
    assert note["kind"] == "annotation" and note["file_path"] == "main.py"
    assert note["line_start"] == 3  # le dernier cadre de la trace (TRACE : ligne 7 puis 3)
    assert models.calls[0].tier == "rapide"
    assert "ZeroDivisionError" in str(models.received[0][1].content)


async def test_stale_proposal_is_dropped_when_the_code_changed_meanwhile(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sid = session["id"]
    await set_preferences(app, teacher_style="pair")
    changed = {"main.py": MAIN + "extra = 1\n", "test_main.py": FILES["test_main.py"]}
    models.hold = hold = asyncio.Event()
    models.replies.append(
        note_json("proposal", "Change.", path="main.py", start_line=1, replacement="a = 1")
    )
    sent = (await teach(client, sid, "question", question=QUESTION, file_path="main.py")).json()
    async with asyncio.timeout(5):
        while not models.calls:  # le professeur a lu le code et attend le modèle
            await asyncio.sleep(0.01)
    await client.put(f"{API}/sessions/{sid}/files", json={"files": changed})
    hold.set()
    done = await wait_done(client, sent["session_id"])
    assert (await client.get(f"{API}/sessions/{sid}/notes")).json() == []  # rien de périmé rangé
    assert done["status"] == "completed"


async def test_each_call_logs_only_session_model_tokens(
    app: FastAPI,
    client: httpx.AsyncClient,
    session: dict[str, Any],
    models: ScriptedModels,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sid = session["id"]
    answer = "Une réponse secrète du professeur."
    models.replies.append(note_json("explanation", answer))
    caplog.set_level(logging.INFO)
    note = await ask(client, sid, file_path="main.py", line=3)
    assert note["content"] == answer
    ours = [r for r in caplog.records if r.name.startswith("app.agents.nodes.professor")]
    [record] = ours
    message = record.getMessage()
    assert sid in message and "modele-fort" in message and "jetons" in message
    secrets = [MAIN[:30], QUESTION, answer, "line_3 = 3", "ZeroDivisionError"]
    for entry in caplog.records:
        if entry.name.startswith("app."):  # (aiosqlite journalise ses paramètres en DEBUG)
            assert not any(secret in entry.getMessage() for secret in secrets), entry.name
