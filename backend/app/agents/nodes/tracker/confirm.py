"""La confirmation de la fiche (SPEC 6.3, 9.4, D141) : « Je crée cette fiche ? ».

`ask_confirm` ne fait qu'`interrupt()` puis relit la réponse (pur) : aucune écriture, aucun appel
payant ni lecture de port avant l'arrêt, le nœud est rejoué depuis son début à la reprise. La
question ne dépend que de l'état (le brouillon et les alertes lus avant) : rejouée, elle est la
même.

Question (`kind = "application_confirm"`) : `question` « Je crée cette fiche ? » suivie du message
de l'alerte la plus forte s'il y en a une ; `fields` pré remplis (`value`) : `company`, `title`,
`status`, `applied_on` (AAAA-MM-JJ), `channel`, `contact_name`, `contact_role`, `notes` ;
`options` : sans alerte `create` et `cancel` ; avec une alerte `distinct` (« C'est un autre
poste »), `open` (« Ouvrir la fiche existante », la plus forte) et `cancel` (comme la route, une
fiche qui ressemble ne se crée jamais sans « autre poste »).

Réponse : `{"choice": <option>, "fields": {id: texte}}` (`fields` facultatif : le brouillon sert) ou
l'option seule (`"cancel"`). Une réponse invalide (option absente de la question, champ rejeté,
date dans le futur) repose la même question sans rien écrire."""

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
QUESTION = "Je crée cette fiche ?"
CREATE, DISTINCT, OPEN, CANCEL = "create", "distinct", "open", "cancel"
LABELS = {
    CREATE: "Créer la fiche",
    DISTINCT: "C'est un autre poste",
    OPEN: "Ouvrir la fiche existante",
    CANCEL: "Annuler",
}
# (identifiant, libellé, obligatoire, longueur maximale) : l'ordre du formulaire.
FIELDS: list[tuple[str, str, bool, int]] = [
    ("company", "Entreprise", True, COMPANY_MAX),
    ("title", "Poste", True, TITLE_MAX),
    ("status", "Statut", True, 16),
    ("applied_on", "Date de candidature (AAAA-MM-JJ)", False, 10),
    ("channel", "Canal", False, 16),
    ("contact_name", "Contact", False, CONTACT_MAX),
    ("contact_role", "Rôle du contact", False, CONTACT_MAX),
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
