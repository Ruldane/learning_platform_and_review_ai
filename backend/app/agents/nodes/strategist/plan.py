"""Le Stratège écrit le programme semaine par semaine (SPEC 3.4 ; point d'arrêt n° 3, D86).

`draft` demande un `PlanDraft` au modèle et le fait vérifier par les règles de la feature (port,
`check_draft`) : les problèmes repartent au modèle, deux fois au plus (`MAX_PLAN_ASKS` = une
demande et deux re-demandes) ; ensuite le brouillon est gardé tel quel et c'est le rangement du
code (`save_draft` : acquis, 85 %, pratique et quiz) qui le met aux règles (D83 §4).

`save` enregistre la version (idempotent par `(session, revision)`) ; `ask_validation` ne fait
qu'`interrupt()` puis analyse la réponse (pur) ; une révision repart de `draft` avec le plan
courant relu en base (modifications de January comprises) et sa note ; `finalize` valide
(idempotent)."""

import logging
from dataclasses import asdict
from datetime import date
from typing import Any, Literal, Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field, ValidationError

from app.agents.nodes.strategist.plan_context import context_vars, hours
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.program_builder import ProgramState
from app.agents.tools.plan_schema import PlanDraft
from app.agents.tools.program_port import DraftSaved

AGENT = "strategist"
MAX_PLAN_ASKS = 3  # une demande + deux re-demandes avec les problèmes de `check_draft`
MAX_PROBLEMS_SHOWN = 30
MAX_NOTE_CHARS = 2000
PLAN_TIMEOUT_S = 600  # trois demandes d'un programme complet au modèle fort
PLAN_REQUEST = "Écris le programme semaine par semaine."
VALIDATION_INTERRUPT: dict[str, Any] = {
    "kind": "validate_program",
    "question": (
        "Déplace, supprime ou ajoute des tâches dans le calendrier, puis valide le programme ou "
        "demande une révision."
    ),
    "options": [{"value": "validate", "label": "Valider le programme"}],
    "fields": [{"id": "note", "label": "Ce qu'il faut revoir (pour une révision)"}],
}

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: ProgramState) -> ProgramState: ...


class ValidationAnswer(BaseModel):
    action: Literal["validate", "revise"]
    note: str = Field(default="", max_length=MAX_NOTE_CHARS)


def make_context(deps: GraphDeps) -> Node:
    @node_timeout()
    async def context(state: ProgramState) -> ProgramState:
        """Objectif, propositions choisies, budget, acquis, langue et compte rendu (port)."""
        found = await deps.ports.program.context(
            deps.user_id, state["goal_id"], state["proposal_ids"], None
        )
        return {"plan_vars": context_vars(found), "revision": 0, "note": ""}

    return context


def _problems_text(problems: list[str]) -> str:
    shown = [f"- {problem}" for problem in problems[:MAX_PROBLEMS_SHOWN]]
    if len(problems) > MAX_PROBLEMS_SHOWN:
        shown.append(f"- … et {len(problems) - MAX_PROBLEMS_SHOWN} autres problèmes.")
    return (
        "Ton programme ne respecte pas les règles :\n"
        + "\n".join(shown)
        + "\nCorrige-le et rends de nouveau le programme complet, toutes les semaines."
    )


async def _write(deps: GraphDeps, goal_id: str, prompt: str, revision: int) -> PlanDraft:
    """Une demande, puis deux re-demandes au plus avec les problèmes ; la dernière est gardée."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(PLAN_REQUEST)]
    check = deps.ports.program.check_draft
    found: PlanDraft | None = None
    problems: list[str] = []
    for ask in range(1, MAX_PLAN_ASKS + 1):
        if found is not None:
            messages += [AIMessage(found.model_dump_json()), HumanMessage(_problems_text(problems))]
        found = await structured_call(
            model,
            PlanDraft,
            messages,
            agent=AGENT,
            step=f"programme-{revision}-{ask}",
            intent="j'écris le programme" if ask == 1 else "je corrige le programme",
        )
        problems = await check(deps.user_id, goal_id, found)
        if not problems:
            return found
    logger.info(
        "Programme : brouillon gardé avec %d problème(s), rangé par les règles "
        "(session %s, révision %d)",
        len(problems),
        deps.session_id,
        revision,
    )
    assert found is not None
    return found


def make_draft(deps: GraphDeps) -> Node:
    @node_timeout(PLAN_TIMEOUT_S)
    async def draft(state: ProgramState) -> ProgramState:
        revision = state.get("revision", 0)
        plan_vars = state.get("plan_vars", {})
        if revision > 0:  # le plan est en base : relu, modifications de January comprises
            program_id = state["saved"]["program_id"]
            found = await deps.ports.program.context(
                deps.user_id, state["goal_id"], state["proposal_ids"], program_id
            )
            plan_vars = context_vars(found)
        note = state.get("note", "")
        prompt = render_prompt(
            AGENT,
            mode="plan",
            **plan_vars,
            revision=revision,
            note=untrusted(note, "note de révision de January") if note else "",
        )
        written = await _write(deps, state["goal_id"], prompt, revision)
        return {"draft": written.model_dump(mode="json"), "plan_vars": plan_vars}

    return draft


def _reason(revision: int, note: str) -> str:
    if revision == 0:
        return "Première version du Stratège"
    return (f"Révision {revision} : {note}" if note else f"Révision {revision}")[:300]


def _saved_text(title: str, saved: DraftSaved) -> str:
    parts = [
        f"Programme « {title} » : {saved.weeks} semaine(s), {hours(saved.total_minutes)} "
        "planifiées, jamais plus de 85 % de ton budget par semaine."
    ]
    if saved.skipped_modules:
        parts.append(f"Déjà acquis, sautés : {', '.join(saved.skipped_modules)}.")
    if saved.moved_tasks:
        parts.append(
            f"{saved.moved_tasks} tâche(s) reportée(s) à la semaine suivante pour tenir le budget."
        )
    return " ".join(parts)


def make_save(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save(state: ProgramState) -> ProgramState:
        """Version enregistrée (idempotent par `(session, revision)`), puis annoncée."""
        draft = PlanDraft.model_validate(state["draft"])
        revision = state.get("revision", 0)
        raw_start = state.get("start_date")
        saved = await deps.ports.program.save_draft(
            deps.user_id,
            deps.session_id,
            state["goal_id"],
            draft,
            revision=revision,
            start_date=date.fromisoformat(raw_start) if raw_start else None,
            reason=_reason(revision, state.get("note", "")),
        )
        logger.info(
            "Programme enregistré : session %s, programme %s, version %d",
            deps.session_id,
            saved.program_id,
            saved.version,
        )
        message = {"message_id": f"{AGENT}-programme-{revision}"}
        emit("agent.message", {**message, "text": _saved_text(draft.title, saved)}, agent=AGENT)
        artifact = {
            "artifact_id": saved.program_id,
            "kind": "program",
            "title": draft.title,
            "url": f"/apprendre/programme/{saved.program_id}",
        }
        emit("artifact.ready", artifact, agent=AGENT)
        return {"saved": asdict(saved)}

    return save


def parse_validation(value: Any) -> ValidationAnswer | None:
    """`"validate"`, `{"action": "validate"}`, `{"action": "revise", "note": …}` ou
    `{"answers": {"note": …}}` (révision). Note coupée à 2 000 caractères plutôt que refusée (la
    saisie de January n'est jamais perdue). Toute autre forme : `None`."""
    if value == "validate":
        return ValidationAnswer(action="validate")
    if not isinstance(value, dict):
        return None
    if "action" not in value and "answers" in value:
        answers = value["answers"]
        if not isinstance(answers, dict) or not isinstance(answers.get("note"), str):
            return None
        value = {"action": "revise", "note": answers["note"]}
    if isinstance(value.get("note"), str):
        value = {**value, "note": value["note"].strip()[:MAX_NOTE_CHARS]}
    try:
        answer = ValidationAnswer.model_validate(value)
    except ValidationError:
        return None
    return ValidationAnswer(action="validate") if answer.action == "validate" else answer


def ask_validation(state: ProgramState) -> ProgramState:
    """Point d'arrêt n° 3. Rien avant `interrupt()` ; une réponse invalide repose la question."""
    answer = parse_validation(interrupt(VALIDATION_INTERRUPT))
    if answer is None:
        return {"validation": None}
    if answer.action == "revise":
        revision = state.get("revision", 0) + 1
        return {"validation": answer.model_dump(), "revision": revision, "note": answer.note}
    return {"validation": answer.model_dump()}


def route_validation(state: ProgramState) -> str:
    answer = state.get("validation")
    if answer is None:
        return "ask_validation"
    return "finalize" if answer["action"] == "validate" else "draft"


def make_finalize(deps: GraphDeps) -> Node:
    @node_timeout()
    async def finalize(state: ProgramState) -> ProgramState:
        """Programme validé (idempotent : un nœud rejoué revalide sans effet de plus)."""
        program_id = state["saved"]["program_id"]
        await deps.ports.program.validate(deps.user_id, deps.session_id, program_id)
        logger.info("Programme validé : session %s, programme %s", deps.session_id, program_id)
        summary = f"Programme validé : « {state['draft']['title']} »."
        emit("agent.message", {"message_id": f"{AGENT}-validation", "text": summary}, agent=AGENT)
        return {"summary": summary}

    return finalize
