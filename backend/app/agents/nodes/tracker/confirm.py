"""Confirm the drafted application (SPEC 6.3, 9.4, D141).

`ask_confirm` interrupts and validates the reply. Replay reconstructs the same question from the
draft and the strongest duplicate alert in state. The node performs no writes or provider calls.

The form includes the draft's fields and offers `create` and `cancel` when there are no alerts.
With an alert, the choices are `distinct`, `open`, and `cancel`.

The reply can be a choice or an object with `choice` and optional `fields`. An invalid choice,
field, or future application date causes the graph to ask the same question again.
"""

from typing import Any

from langgraph.types import interrupt
from pydantic import ValidationError

from app.agents.state.application_intake import ApplicationIntakeState
from app.agents.tools.applications_port import (
    COMPANY_MAX,
    CONTACT_MAX,
    NOTES_MAX,
    TITLE_MAX,
    IntakeDraft,
)

KIND = "application_confirm"
QUESTION = "Create this application?"
CREATE, DISTINCT, OPEN, CANCEL = "create", "distinct", "open", "cancel"
LABELS = {
    CREATE: "Create application",
    DISTINCT: "It's a different role",
    OPEN: "Open the existing application",
    CANCEL: "Cancel",
}
# Field ID, display label, required flag, and maximum length in form order.
FIELDS: list[tuple[str, str, bool, int]] = [
    ("company", "Company", True, COMPANY_MAX),
    ("title", "Role", True, TITLE_MAX),
    ("status", "Status", True, 16),
    ("applied_on", "Application date (YYYY-MM-DD)", False, 10),
    ("channel", "Channel", False, 16),
    ("contact_name", "Contact", False, CONTACT_MAX),
    ("contact_role", "Contact role", False, CONTACT_MAX),
    ("notes", "Notes", False, NOTES_MAX),
]
FIELD_IDS = [name for name, *_ in FIELDS]


def _values(draft: dict[str, Any]) -> dict[str, str]:
    return {name: str(draft.get(name) or "") for name in FIELD_IDS}


def options_for(alerts: list[dict[str, Any]]) -> list[str]:
    return [DISTINCT, OPEN, CANCEL] if alerts else [CREATE, CANCEL]


def question(state: ApplicationIntakeState) -> dict[str, Any]:
    """La question de la confirmation (voir le module) : ne dépend que de l'état."""
    alerts = state.get("alerts", [])
    text = f"{QUESTION} {alerts[0]['message']}" if alerts else QUESTION
    values = _values(state["draft"])
    return {
        "kind": KIND,
        "question": text,
        "options": [{"value": o, "label": LABELS[o]} for o in options_for(alerts)],
        "fields": [
            {"id": name, "label": label, "required": required, "max_length": size,
             "value": values[name]}
            for name, label, required, size in FIELDS
        ],
    }  # fmt: skip


def _choice_and_fields(value: Any) -> tuple[str, dict[str, str]] | None:
    """`(option, champs envoyés)` d'une réponse bien formée, sinon `None`."""
    if isinstance(value, str):
        return value, {}
    if not isinstance(value, dict) or not isinstance(value.get("choice"), str):
        return None
    sent = value.get("fields") or {}
    if not isinstance(sent, dict):
        return None
    fields = {name: raw for name, raw in sent.items() if name in FIELD_IDS}
    if not all(isinstance(raw, str) for raw in fields.values()):
        return None
    return value["choice"], fields


def _confirmed(state: ApplicationIntakeState, fields: dict[str, str]) -> IntakeDraft | None:
    """Le brouillon relu : celui de l'état, les champs envoyés par-dessus, revalidé. Une date
    dans le futur (jour de January) est refusée comme à la lecture de la phrase."""
    try:
        draft = IntakeDraft.model_validate({**state["draft"], **fields})
    except ValidationError:
        return None
    today = state.get("today")
    if draft.applied_on is not None and today is not None and draft.applied_on.isoformat() > today:
        return None
    return draft


def parse_answer(value: Any, state: ApplicationIntakeState) -> dict[str, Any] | None:
    """`{"choice", "draft"}` ou `None` (la question est reposée). Pur : aucun port."""
    parsed = _choice_and_fields(value)
    if parsed is None or parsed[0] not in options_for(state.get("alerts", [])):
        return None
    choice, fields = parsed
    if choice in (CANCEL, OPEN):
        return {"choice": choice, "draft": state["draft"]}
    draft = _confirmed(state, fields)
    return None if draft is None else {"choice": choice, "draft": draft.model_dump(mode="json")}


def ask_confirm(state: ApplicationIntakeState) -> ApplicationIntakeState:
    """`interrupt()` seul : rien avant lui ; la réponse est relue sans aucun port."""
    return {"answer": parse_answer(interrupt(question(state)), state)}


def route_confirm(state: ApplicationIntakeState) -> str:
    answer = state.get("answer")
    if answer is None:
        return "ask"
    return "save" if answer["choice"] in (CREATE, DISTINCT) else "leave"
