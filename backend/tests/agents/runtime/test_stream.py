"""Traduction du flux LangGraph (`astream`, plusieurs modes) en événements du catalogue."""

from langchain_core.messages import AIMessage, AIMessageChunk
from langgraph.types import Interrupt

from app.agents.runtime.emit import EVENT_KEY
from app.agents.runtime.stream import PendingEvent, interrupt_payload, translate_chunk


def test_translate_custom_event():
    out = translate_chunk(
        "custom",
        {
            EVENT_KEY: "board.update",
            "agent": "scribe",
            "payload": {"mermaid": "flowchart TD", "step": 1},
        },
    )
    assert out == [PendingEvent("board.update", "scribe", {"mermaid": "flowchart TD", "step": 1})]


def test_custom_data_without_the_event_key_is_ignored():
    assert translate_chunk("custom", {"autre": 1}) == []
    assert translate_chunk("custom", "texte libre") == []


def test_translate_message_chunk_uses_agent_metadata():
    out = translate_chunk(
        "messages",
        (
            AIMessageChunk(content="Bon", id="m1"),
            {"agent": "demo_critic", "langgraph_node": "critic"},
        ),
    )
    assert out[0].type == "agent.token" and out[0].agent == "demo_critic"
    assert out[0].payload == {"message_id": "m1", "text": "Bon"}


def test_message_chunk_without_agent_falls_back_to_the_node():
    out = translate_chunk(
        "messages", (AIMessageChunk(content="x", id="m1"), {"langgraph_node": "n"})
    )
    assert out[0].agent == "n"


def test_message_chunk_with_text_blocks_is_joined():
    chunk = AIMessageChunk(content=[{"type": "text", "text": "a"}, {"type": "text", "text": "b"}])
    out = translate_chunk("messages", (chunk, {"agent": "x"}))
    assert out[0].payload["text"] == "ab"


def test_empty_or_complete_messages_are_not_tokens():
    """Un fragment vide (raisonnement GLM, appel d'outil) n'est pas un token ; un message complet
    déjà présent dans l'état n'est pas rediffusé (il a son `agent.message`)."""
    assert translate_chunk("messages", (AIMessageChunk(content="", id="m"), {"agent": "a"})) == []
    assert translate_chunk("messages", (AIMessage(content="tout", id="m"), {"agent": "a"})) == []


def test_translate_interrupt_update():
    value = {"kind": "choice", "question": "?", "options": []}
    out = translate_chunk("updates", {"__interrupt__": (Interrupt(value=value, id="i1"),)})
    assert out[0].type == "interrupt.requested" and out[0].payload["interrupt_id"] == "i1"
    assert out[0].payload["kind"] == "choice" and out[0].agent is None


def test_node_updates_and_other_modes_are_ignored():
    assert translate_chunk("updates", {"a": {"n": 1}}) == []
    assert translate_chunk("values", {"n": 1}) == []


def test_interrupt_payload_validates_the_value():
    interrupt = Interrupt(
        value={"kind": "choice", "question": "Lequel ?", "options": [{"value": "a", "label": "A"}]},
        id="i2",
    )
    assert interrupt_payload(interrupt) == {
        "interrupt_id": "i2",
        "kind": "choice",
        "question": "Lequel ?",
        "options": [{"value": "a", "label": "A"}],
        "fields": [],
    }
