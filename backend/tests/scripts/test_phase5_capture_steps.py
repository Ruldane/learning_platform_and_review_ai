"""Étape « capture » du contrôle de fin de phase 5 contre une fausse API : un lien lisible qui
demande le texte, un lien illisible signalé trop tard, une entrée de journal sans élément de
mémoire, et ce que le texte collé envoie (sans jamais l'imprimer)."""

from typing import Any

import httpx
import pytest

from scripts import phase5_capture
from scripts.phase4_rules import CheckFailed
from scripts.phase5_capture import PASTED_TEXT, capture_link, capture_unreadable
from scripts.phase5_steps import Etude
from tests.scripts.phase5_fakes import FakeApi

TEXT_QUESTION = {
    "interrupt_id": "i1",
    "kind": "capture_text",
    "options": [{"value": "cancel", "label": "Abandonner"}],
}


def capture_api(*, question: dict[str, Any] | None, item: str | None = "mi") -> FakeApi:
    """Une capture `c1` : la question (ou rien), puis `completed` une fois la reprise reçue."""
    state = {"resumed": question is None}

    def session(request: httpx.Request) -> dict[str, Any]:
        if state["resumed"]:
            return {"status": "completed", "pending_interrupt": None}
        return {"status": "waiting_user", "pending_interrupt": question}

    def resume(request: httpx.Request) -> dict[str, Any]:
        state["resumed"] = True
        return {}

    entry = {"id": "j1", "links": {"session_id": "c1", "memory_item_id": item}}
    return FakeApi(
        {
            ("POST", "/capture"): {"session_id": "c1"},
            ("GET", "/sessions/c1"): session,
            ("POST", "/sessions/c1/resume"): resume,
            ("GET", "/journal"): {"entries": [entry], "next_before": None},
            ("GET", "/memory/items/mi"): {"id": "mi"},
        }
    )


async def test_a_readable_link_is_stored_and_its_entry_has_a_memory_item() -> None:
    api = capture_api(question=None)
    client, run = api.run()
    async with client:
        state = Etude()
        await capture_link(run, state)

    assert state.captures == ["c1"]
    assert api.sent("POST", "/capture") == [{"url": phase5_capture.READABLE_URL}]


async def test_a_readable_link_that_asks_for_its_text_is_a_failure() -> None:
    api = capture_api(question=TEXT_QUESTION)
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="Question « capture_text » inattendue"):
            await capture_link(run, Etude())


async def test_an_unreadable_link_asks_for_the_text_at_once_and_stores_the_pasted_one() -> None:
    api = capture_api(question=TEXT_QUESTION)
    client, run = api.run()
    async with client:
        state = Etude()
        await capture_unreadable(run, state)

    resumed = api.sent("POST", "/sessions/c1/resume")
    assert resumed == [{"interrupt_id": "i1", "value": {"answers": {"text": PASTED_TEXT}}}]
    assert state.captures == ["c1"]


async def test_an_unreadable_link_signalled_too_late_is_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(phase5_capture, "UNREADABLE_S", -1.0)
    api = capture_api(question=TEXT_QUESTION)
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="signalé après .* s : -1 au plus"):
            await capture_unreadable(run, Etude())


async def test_an_unreadable_link_without_a_question_is_a_failure() -> None:
    api = capture_api(question=None)
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="sans question « capture_text »"):
            await capture_unreadable(run, Etude())


async def test_an_entry_without_a_memory_item_is_a_failure() -> None:
    api = capture_api(question=None, item=None)
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="Entrée j1 sans élément de mémoire"):
            await capture_link(run, Etude())
