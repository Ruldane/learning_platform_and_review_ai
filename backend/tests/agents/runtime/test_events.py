from typing import get_args

import pytest
from fastapi import FastAPI

from app.agents.runtime.events import (
    PAYLOAD_MODELS,
    SESSION_EVENT_ADAPTER,
    AgentMessagePayload,
    AgentTokenEvent,
    BoardUpdatePayload,
    Citation,
    EventType,
    InterruptField,
    InterruptRequestedEvent,
    InterruptRequestedPayload,
    SessionEvent,
    SourceFoundPayload,
    UserMessagePayload,
    validate_payload,
)

_ENVELOPE = {"id": "e1", "session_id": "s1", "seq": 1, "ts": "2026-11-11T08:00:00Z"}
_SAMPLE_PAYLOADS: dict[str, dict[str, object]] = {
    "agent.started": {"step": "debate", "intent": "Je compare les arguments."},
    "agent.token": {"message_id": "m1", "text": "Bon"},
    "agent.message": {
        "message_id": "m1",
        "text": "Bonjour",
        "citations": [{"index": 1, "title": "T"}],
    },
    "tool.called": {"call_id": "c1", "tool": "web_search", "args": {"q": "x"}},
    "tool.result": {"call_id": "c1", "tool": "web_search", "ok": True, "summary": "3 résultats"},
    "source.found": {
        "title": "T",
        "url": "https://x.test",
        "author": None,
        "date": None,
        "lang": "fr",
        "score": 3,
    },
    "board.update": {"mermaid": "graph TD; A-->B", "step": 2},
    "memory.written": {"item_id": "i1", "kind": "note", "title": "T", "reason": "utile"},
    "interrupt.requested": {
        "interrupt_id": "x1",
        "kind": "choice",
        "question": "Quel angle ?",
        "options": [{"value": "a", "label": "A"}],
    },
    "proposal.ready": {"proposal_id": "p1", "title": "T"},
    "artifact.ready": {"artifact_id": "a1", "kind": "pdf", "title": "T"},
    "cost.updated": {"tokens_in": 1, "tokens_out": 2, "cost_usd": 0.01, "cap_tokens": 300000},
    "run.completed": {},
    "run.failed": {"code": "llm_key_missing", "message": "Clé absente."},
    "user.message": {"text": "Salut"},
}


def test_every_event_type_has_a_payload_model():
    assert set(PAYLOAD_MODELS) == set(get_args(EventType))
    assert len(PAYLOAD_MODELS) == 15


def test_adapter_discriminates_on_type():
    ev = SESSION_EVENT_ADAPTER.validate_python(
        {
            **_ENVELOPE,
            "type": "agent.token",
            "agent": "demo_critic",
            "payload": {"message_id": "m1", "text": "Bon"},
        }
    )
    assert isinstance(ev, AgentTokenEvent) and ev.payload.text == "Bon"


@pytest.mark.parametrize("event_type", get_args(EventType))
def test_every_type_round_trips_through_the_adapter(event_type: str):
    raw = {**_ENVELOPE, "type": event_type, "agent": None, "payload": _SAMPLE_PAYLOADS[event_type]}
    event = SESSION_EVENT_ADAPTER.validate_python(raw)
    assert event.type == event_type
    assert isinstance(event.payload, PAYLOAD_MODELS[event.type])
    dumped = SESSION_EVENT_ADAPTER.dump_python(event, mode="json")
    assert SESSION_EVENT_ADAPTER.validate_python(dumped) == event


def test_adapter_rejects_unknown_type_and_mismatched_payload():
    with pytest.raises(ValueError):
        SESSION_EVENT_ADAPTER.validate_python({**_ENVELOPE, "type": "nope", "payload": {}})
    with pytest.raises(ValueError):
        SESSION_EVENT_ADAPTER.validate_python(
            {**_ENVELOPE, "type": "agent.token", "payload": {"question": "?"}}
        )


def test_interrupt_event_exposes_kind_and_default_options():
    ev = SESSION_EVENT_ADAPTER.validate_python(
        {
            **_ENVELOPE,
            "type": "interrupt.requested",
            "payload": {"interrupt_id": "i", "kind": "text", "question": "?"},
        }
    )
    assert isinstance(ev, InterruptRequestedEvent)
    assert ev.payload.options == [] and ev.agent is None


def test_default_lists_are_not_shared_between_instances():
    a = AgentMessagePayload(message_id="m", text="t")
    b = AgentMessagePayload(message_id="m", text="t")
    a.citations.append(Citation(index=1, title="x"))
    assert b.citations == []


def test_validate_payload_accepts_dict_and_model():
    model = validate_payload("agent.token", {"message_id": "m1", "text": "a"})
    assert validate_payload("agent.token", model) is model


def test_validate_payload_rejects_wrong_shape():
    with pytest.raises(ValueError):
        validate_payload("interrupt.requested", {"question": "?"})


def test_validate_payload_rejects_unknown_type_and_wrong_model():
    with pytest.raises(ValueError):
        validate_payload("nope", {})  # type: ignore[arg-type]
    other = validate_payload("agent.token", {"message_id": "m1", "text": "a"})
    with pytest.raises(ValueError):
        validate_payload("run.failed", other)


def test_validate_payload_error_does_not_echo_the_received_value():
    with pytest.raises(ValueError) as exc:
        validate_payload("cost.updated", {"tokens_in": "sk-secret-value"})
    assert "sk-secret-value" not in str(exc.value)


def test_openapi_exposes_session_event_union(app: FastAPI):
    schemas = app.openapi()["components"]["schemas"]
    assert "SessionEvent" in schemas and "InterruptRequestedEvent" in schemas
    assert len(schemas["SessionEvent"]["oneOf"]) == 15
    assert schemas["SessionEvent"]["discriminator"]["propertyName"] == "type"
    assert "InterruptRequestedPayload" in schemas and "Citation" in schemas
    assert "$defs" not in schemas["SessionEvent"]
    assert app.openapi() is app.openapi()  # mis en cache, fusion faite une seule fois


def test_session_event_alias_is_exported():
    assert SessionEvent is not None


# --- Phase 4 : champs ajoutés avec défaut (D82) ------------------------------------------------


@pytest.mark.parametrize(
    ("event_type", "payload"),
    [
        ("board.update", {"mermaid": "flowchart TD", "step": 1}),
        ("user.message", {"text": "ancien"}),
        ("interrupt.requested", {"interrupt_id": "i", "kind": "text", "question": "?"}),
        ("source.found", _SAMPLE_PAYLOADS["source.found"]),
    ],
)
def test_old_events_still_validate(event_type: EventType, payload: dict[str, object]):
    """Charges stockées avant la phase 4 (sans fields, kind, board_id ni command)."""
    assert validate_payload(event_type, payload)


def test_new_fields_have_defaults():
    board = validate_payload("board.update", {"mermaid": "flowchart TD", "step": 1})
    assert isinstance(board, BoardUpdatePayload)
    assert (board.board_id, board.kind, board.title) == (None, None, None)
    found = validate_payload("source.found", _SAMPLE_PAYLOADS["source.found"])
    assert isinstance(found, SourceFoundPayload) and (found.kind, found.role) == ("page", None)
    said = validate_payload("user.message", {"text": "x"})
    assert isinstance(said, UserMessagePayload) and said.command is None
    asked = validate_payload("interrupt.requested", _SAMPLE_PAYLOADS["interrupt.requested"])
    assert isinstance(asked, InterruptRequestedPayload) and asked.fields == []


def test_user_message_accepts_a_command_without_text():
    said = validate_payload("user.message", {"command": "shorter"})
    assert isinstance(said, UserMessagePayload) and (said.text, said.command) == ("", "shorter")
    with pytest.raises(ValueError):
        validate_payload("user.message", {"text": "", "command": "louder"})


def test_interrupt_fields_are_bounded():
    field = InterruptField(id="goal_1", label="Ton objectif ?", required=True)
    assert field.max_length == 2000
    for bad in (
        {"id": "Goal", "label": "x"},
        {"id": "a" * 33, "label": "x"},
        {"id": "ok", "label": "x", "max_length": 0},
        {"id": "ok", "label": "x", "max_length": 20001},
    ):
        with pytest.raises(ValueError):
            InterruptField.model_validate(bad)
    # Le texte d'une page collée après un lien illisible (capture, F6 / D108).
    assert InterruptField(id="text", label="x", max_length=20000).max_length == 20000


def test_board_kind_is_one_of_four():
    for kind in ("domain_map", "prerequisites", "timeline", "comparison"):
        assert validate_payload("board.update", {"mermaid": "m", "step": 1, "kind": kind})
    with pytest.raises(ValueError):
        validate_payload("board.update", {"mermaid": "m", "step": 1, "kind": "free"})
