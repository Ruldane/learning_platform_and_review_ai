"""Les outils de graphe (10.B2) : lancer un parcours de l'application par `POST /sessions`, l'entrée
validée par le `input_model` du graphe, puis suivre la session ; jamais un graphe non déclaré."""

import asyncio
import json
from collections.abc import Iterator
from uuid import uuid4

import pytest

from app.mcp.registry import Registry
from tests.agents.graphs_for_tests import Probe
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.sessions_support import use_test_runtime


@pytest.fixture(autouse=True)
def probe(monkeypatch: pytest.MonkeyPatch) -> Iterator[Probe]:
    """Avant l'app (autouse) : son lifespan construit le moteur avec les parcours de test."""
    probe = use_test_runtime(monkeypatch)
    yield probe
    probe.release_b.set()


async def settled(amcp: Mcp, token: str, session_id: str) -> dict[str, object]:
    for _ in range(100):
        envelope, _ = await call(amcp, token, "sessions_get", {"session_id": session_id})
        if envelope["data"]["status"] != "running":
            data: dict[str, object] = envelope["data"]
            return data
        await asyncio.sleep(0.05)
    raise AssertionError("la session ne se termine pas")


async def test_graph_tool_validates_input_model_and_returns_session_id(
    amcp: Mcp, writer: str, adapter: Registry
) -> None:
    tool = adapter.get("graph_with_topic")
    assert tool is not None and tool.level == 2 and tool.graph == "with_topic"
    assert tool.input_schema["required"] == ["topic"] and "topic" in tool.input_schema["properties"]

    launched, is_error = await call(amcp, writer, "graph_with_topic", {"topic": "Le test"})

    assert not is_error, launched
    session_id = launched["data"]["session_id"]
    done = await settled(amcp, writer, session_id)
    assert done["graph"] == "with_topic" and done["status"] == "completed"

    # L'entrée invalide est refusée par le graphe lui-même, sans citer la valeur reçue.
    wrong_type, is_error = await call(amcp, writer, "graph_with_topic", {"topic": 12345678})
    assert is_error and wrong_type["data"]["error"]["code"] == "validation_error"
    assert "12345678" not in json.dumps(wrong_type)
    missing, is_error = await call(amcp, writer, "graph_with_topic", {})
    assert is_error and missing["data"]["error"]["code"] == "invalid_arguments"
    extra, is_error = await call(amcp, writer, "graph_with_topic", {"topic": "x", "graph": "autre"})
    assert is_error and extra["data"]["error"]["code"] == "invalid_arguments"


async def test_graph_launch_has_no_undoable_changes_but_is_in_the_journal(
    amcp: Mcp, writer: str
) -> None:
    launched, _ = await call(amcp, writer, "graph_with_topic", {"topic": "Le test"})
    await settled(amcp, writer, launched["data"]["session_id"])

    assert (await amcp.http.get(f"{API}/mcp/changes")).json() == []  # annuler = annuler la session
    calls = (await amcp.http.get(f"{API}/mcp/calls")).json()
    launch = next(item for item in calls if item["action"] == "graph_with_topic")
    assert launch["ids"] == {"session_id": launched["data"]["session_id"]}


async def test_session_journal_omits_user_supplied_subject_id(amcp: Mcp, writer: str) -> None:
    subject_id = str(uuid4())
    started = await amcp.http.post(
        f"{API}/sessions",
        json={"graph": "with_topic", "input": {"topic": "Test"}, "subject_id": subject_id},
    )
    assert started.status_code == 202, started.text
    session_id = started.json()["session_id"]

    done = await settled(amcp, writer, session_id)

    assert done["subject_id"] == subject_id
    entries = (await amcp.http.get(f"{API}/mcp/calls")).json()
    assert entries and all(entry["ids"] == {"id": session_id} for entry in entries)


async def test_graph_outside_allowlist_refused(amcp: Mcp, writer: str, adapter: Registry) -> None:
    for name in ("graph_two_steps", "graph_blocking", "sessions_start", "graph_demo_debate"):
        response = await amcp.call(writer, name, {"topic": "x"})
        assert response.json()["error"]["code"] == -32602, name  # outil inconnu
    # Aucun outil n'envoie un `POST /sessions` brut : seul le graphe déclaré passe.
    raw = [tool for tool in adapter.all() if tool.route == ("POST", "/sessions")]
    assert raw == []
    assert {tool.graph for tool in adapter.all() if tool.graph} == {"with_topic"}
    created, _ = await call(amcp, writer, "graph_with_topic", {"topic": "ok"})
    sessions = (await amcp.http.get(f"{API}/sessions")).json()
    assert [item["id"] for item in sessions] == [created["data"]["session_id"]]
