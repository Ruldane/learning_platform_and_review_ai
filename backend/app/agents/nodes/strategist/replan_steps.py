"""Le parcours `replan` sans effet de bord (D105) : constantes des questions, instantané du
contexte, droits de chaque option, références inconnues, réponses de January et textes.

Droits (D105 (2)) : « réduire » → retraits seuls ; « approfondir » → ajouts seuls ; « repousser »,
« avancer » et sans option → aucun, le rangement du code suffit et le Stratège n'écrit qu'un
résumé. Le modèle ne reçoit que le schéma de ses droits (`schema_for`), et `to_draft` vide tout
le reste."""

import json
from dataclasses import asdict
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.agents.tools.program_port import BudgetView
from app.agents.tools.replan_port import (
    ModuleRef,
    PreviewSaved,
    ReplanAdds,
    ReplanContext,
    ReplanDraft,
    ReplanDrops,
    ReplanSummary,
    ReviewView,
    TaskRef,
)
from app.agents.tools.study_schema import ReplanOption

AGENT = "strategist"
REPLAN_REQUEST = "Propose la replanification."
REPLAN_OPTION = "replan_option"
ACCEPT_REPLAN = "accept_replan"
OPTION_LABELS: dict[str, str] = {
    "reduce_scope": "Réduire le périmètre",
    "push_deadline": "Repousser l'échéance",
    "advance": "Avancer la suite",
    "deepen": "Approfondir",
}
OPTION_QUESTIONS = {
    "late_twice": "Deux semaines de suite en retard : comment veux-tu ajuster le plan ?",
    "ahead": "Tu as pris de l'avance : comment veux-tu ajuster le plan ?",
}
ACCEPT_INTERRUPT: dict[str, Any] = {
    "kind": ACCEPT_REPLAN,
    "question": "Voici le plan proposé, avant et après. L'accepter ?",
    "options": [
        {"value": "accept", "label": "Accepter le nouveau plan"},
        {"value": "refuse", "label": "Garder le plan actuel"},
    ],
    "fields": [{"id": "note", "label": "Ce qu'il faut revoir (pour une autre proposition)"}],
}
STALE_NOTE = "Le programme a changé entre-temps : nouvelle proposition sur le plan à jour."
EMPTY_NOTE_HINT = "Écris ce que tu veux changer."
EMPTY_TEXT = "Rien à changer : ton plan tient tel quel dans ton budget."
IMPOSSIBLE_TEXT = "Le plafond de cette semaine ne tient pas une pratique et le quiz."
REFUSED_TEXT = "Plan actuel gardé : la proposition est refusée."
MAX_NOTE_CHARS = 2000
MAX_REASON_CHARS = 300


# --- Instantané du contexte (état du graphe) ----------------------------------------------------


def as_json(value: ReplanContext | PreviewSaved) -> dict[str, Any]:
    """Une donnée du port en JSON (dates ISO), pour l'état du graphe. `ReplanContext` : c'est
    l'instantané des références, relu par `context_from_state`."""
    return dict(json.loads(json.dumps(asdict(value), default=str)))


def context_from_state(data: dict[str, Any]) -> ReplanContext:
    review = data["review"]
    deadline = data["deadline"]
    return ReplanContext(
        program_id=data["program_id"],
        title=data["title"],
        goal=data["goal"],
        deadline=date.fromisoformat(deadline) if deadline else None,
        budget=BudgetView(**data["budget"]),
        review=None
        if review is None
        else ReviewView(**{**review, "week_start": date.fromisoformat(review["week_start"])}),
        options=tuple(data["options"]),
        modules=[ModuleRef(**m) for m in data["modules"]],
        tasks=[
            TaskRef(**{**t, "planned_date": date.fromisoformat(t["planned_date"])})
            for t in data["tasks"]
        ],
        week_cap_override=data["week_cap_override"],
        message=data["message"],
    )


# --- Droits de l'option et références -----------------------------------------------------------


def schema_for(option: ReplanOption | None) -> type[ReplanSummary]:
    if option == "reduce_scope":
        return ReplanDrops
    if option == "deepen":
        return ReplanAdds
    return ReplanSummary


def to_draft(found: ReplanSummary, option: ReplanOption | None) -> ReplanDraft:
    """Le brouillon complet, vidé de ce que l'option n'autorise pas (doublons retirés)."""
    drop = list(dict.fromkeys(getattr(found, "drop", []))) if option == "reduce_scope" else []
    add = list(getattr(found, "add", [])) if option == "deepen" else []
    return ReplanDraft(summary=found.summary, drop=drop, add=add)


def unknown_refs(draft: ReplanDraft, ctx: ReplanContext) -> list[str]:
    """Références absentes de l'instantané, dans l'ordre (sans doublon)."""
    tasks = {t.ref for t in ctx.tasks}
    modules = {m.ref for m in ctx.modules}
    found = [ref for ref in draft.drop if ref not in tasks]
    found += [task.module for task in draft.add if task.module not in modules]
    return list(dict.fromkeys(found))


def without_unknown(draft: ReplanDraft, ctx: ReplanContext) -> ReplanDraft:
    unknown = set(unknown_refs(draft, ctx))
    return ReplanDraft(
        summary=draft.summary,
        drop=[ref for ref in draft.drop if ref not in unknown],
        add=[task for task in draft.add if task.module not in unknown],
    )


def unknown_text(unknown: list[str]) -> str:
    return (
        f"Ces références n'existent pas dans le plan : {', '.join(unknown)}. N'utilise que les "
        "références de la liste (`t…` pour une tâche, `m…` pour un module) et réponds de nouveau."
    )


# --- Réponses de January ------------------------------------------------------------------------


def option_payload(ctx: ReplanContext) -> dict[str, Any]:
    state = ctx.review.state if ctx.review else ""
    return {
        "kind": REPLAN_OPTION,
        "question": OPTION_QUESTIONS.get(state, "Comment veux-tu ajuster le plan ?"),
        "options": [{"value": o, "label": OPTION_LABELS[o]} for o in ctx.options],
    }


def parse_option(value: Any, options: list[str]) -> str | None:
    """La valeur d'une option offerte (`"reduce_scope"` ou `{"option": …}`) ; sinon `None`."""
    if isinstance(value, dict):
        value = value.get("option")
    return value if isinstance(value, str) and value in options else None


class AcceptAnswer(BaseModel):
    action: Literal["accept", "refuse", "revise"]
    note: str = Field(default="", max_length=MAX_NOTE_CHARS)


def parse_accept(value: Any) -> AcceptAnswer | None:
    """`"accept"`, `"refuse"`, `{"action": …, "note": …}` ou `{"answers": {"note": …}}`
    (révision). Une révision demande une note non vide (coupée à 2 000 caractères, jamais
    perdue). Toute autre forme : `None` (la question est reposée)."""
    if value in ("accept", "refuse"):
        return AcceptAnswer(action=value)
    if not isinstance(value, dict):
        return None
    if "action" not in value and isinstance(value.get("answers"), dict):
        value = {"action": "revise", "note": value["answers"].get("note")}
    note = value.get("note")
    note = note.strip()[:MAX_NOTE_CHARS] if isinstance(note, str) else ""
    try:
        answer = AcceptAnswer.model_validate({"action": value.get("action"), "note": note})
    except ValidationError:
        return None
    if answer.action == "revise":
        return answer if answer.note else None
    return AcceptAnswer(action=answer.action)


def empty_note(value: Any) -> bool:
    """Une demande d'autre proposition sans rien d'écrit (D106) : la question revient avec
    `EMPTY_NOTE_HINT`, jamais en silence."""
    if not isinstance(value, dict):
        return False
    if "action" not in value and isinstance(value.get("answers"), dict):
        value = {"action": "revise", "note": value["answers"].get("note")}
    note = value.get("note")
    return value.get("action") == "revise" and not (isinstance(note, str) and note.strip())


def accept_payload(hint: str) -> dict[str, Any]:
    """La question d'acceptation, précédée de l'aide quand elle est reposée."""
    if not hint:
        return ACCEPT_INTERRUPT
    return {**ACCEPT_INTERRUPT, "question": f"{hint} {ACCEPT_INTERRUPT['question']}"}


# --- Textes -------------------------------------------------------------------------------------


def reason_text(state_trigger: str, option: str | None, revision: int, note: str) -> str:
    parts = ["Bilan hebdomadaire" if state_trigger == "weekly_review" else "Message de January"]
    if option:
        parts.append(OPTION_LABELS[option])
    if revision:
        parts.append(f"proposition {revision + 1}")
    text = " ; ".join(parts)
    return (f"{text} : {note}" if note else text)[:MAX_REASON_CHARS]


def preview_text(summary: str, saved: PreviewSaved) -> str:
    """Le résumé du Stratège, puis les chiffres de la proposition rangée par le code."""
    facts = (
        f"Proposition : {saved.removed} tâche(s) retirée(s), {saved.added} ajoutée(s), "
        f"{saved.moved} déplacée(s) ; {saved.weeks_before} semaine(s) avant, "
        f"{saved.weeks_after} après, jamais plus de 85 % de ton budget par semaine."
    )
    if saved.kept:
        facts += (
            f" {saved.kept} retrait(s) ignoré(s) : chaque semaine garde sa pratique et son quiz."
        )
    return f"{summary}\n\n{facts}"


def end_text(outcome: str, version: int) -> str:
    if outcome == "accepted":
        return f"Nouveau plan appliqué (version {version})."
    if outcome == "refused":
        return REFUSED_TEXT
    if outcome == "impossible":
        return IMPOSSIBLE_TEXT
    return EMPTY_TEXT
