"""Le Stratège replanifie la suite du programme (SPEC F13, D105) : parcours `replan`.

`context` lit le bilan, les options et le plan à faire par références (port) ; `ask_option` et
`ask_accept` ne font qu'`interrupt()` puis analysent la réponse (pur, rien avant l'arrêt,
SPEC 9.4). `propose` demande au modèle ce que ses droits permettent (schéma de l'option) ; une
référence inconnue est renvoyée une fois au modèle, puis retirée. `preview` fait ranger et
enregistrer la proposition par le port (idempotent par `(session, revision)`), séparé de
`propose` : rejoué, il ne rappelle pas le modèle. `apply` et `refuse` sont idempotents ; une
acceptation périmée (lignes changées) repart de `propose` sur le plan relu."""

import logging
from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from app.agents.nodes.strategist.replan_prompt import replan_vars
from app.agents.nodes.strategist.replan_steps import (
    AGENT,
    EMPTY_NOTE_HINT,
    REPLAN_REQUEST,
    STALE_NOTE,
    accept_payload,
    as_json,
    context_from_state,
    empty_note,
    end_text,
    option_payload,
    parse_accept,
    parse_option,
    preview_text,
    reason_text,
    schema_for,
    to_draft,
    unknown_refs,
    unknown_text,
    without_unknown,
)
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.replan import ReplanState
from app.agents.tools.replan_port import ReplanContext, ReplanDraft
from app.agents.tools.study_schema import ReplanOption

MAX_ASKS = 2  # une demande + une re-demande si une référence est inconnue
PROPOSE_TIMEOUT_S = 300

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: ReplanState) -> ReplanState: ...


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


async def _read(deps: GraphDeps, state: ReplanState) -> ReplanContext:
    return await deps.ports.replan.context(
        deps.user_id,
        state["program_id"],
        trigger=state["trigger"],  # type: ignore[arg-type]  # validé par `ReplanInput`
        review_entry_id=state.get("review_entry_id"),
        available_minutes=state.get("available_minutes"),
        message=state.get("message"),
    )


def make_context(deps: GraphDeps) -> Node:
    @node_timeout()
    async def context(state: ReplanState) -> ReplanState:
        """L'instantané du plan, puis le bilan annoncé s'il y en a un."""
        found = await _read(deps, state)
        if found.review is not None:
            _say("replan-bilan", found.review.text)
        return {"context": as_json(found), "revision": 0, "note": "", "option": None}

    return context


def route_start(state: ReplanState) -> str:
    return "ask_option" if state["context"]["options"] else "propose"


def ask_option(state: ReplanState) -> ReplanState:
    """Point d'arrêt : l'option (réduire ou repousser, avancer ou approfondir)."""
    ctx = context_from_state(state["context"])
    value = interrupt(option_payload(ctx))
    return {"option": parse_option(value, list(ctx.options))}


def route_option(state: ReplanState) -> str:
    return "propose" if state.get("option") else "ask_option"


async def _write(
    deps: GraphDeps, ctx: ReplanContext, option: ReplanOption | None, prompt: str, revision: int
) -> ReplanDraft:
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(REPLAN_REQUEST)]
    draft = ReplanDraft(summary="-")
    for ask in range(1, MAX_ASKS + 1):
        found = await structured_call(
            model,
            schema_for(option),
            messages,
            agent=AGENT,
            step=f"replanification-{revision}-{ask}",
            intent="je replanifie" if ask == 1 else "je corrige les références",
        )
        draft = to_draft(found, option)
        unknown = unknown_refs(draft, ctx)
        if not unknown:
            return draft
        messages += [AIMessage(found.model_dump_json()), HumanMessage(unknown_text(unknown))]
    logger.info(
        "Replanification : %d référence(s) inconnue(s) retirée(s) (session %s, proposition %d)",
        len(unknown_refs(draft, ctx)),
        deps.session_id,
        revision,
    )
    return without_unknown(draft, ctx)


def make_propose(deps: GraphDeps) -> Node:
    @node_timeout(PROPOSE_TIMEOUT_S)
    async def propose(state: ReplanState) -> ReplanState:
        """Le brouillon du Stratège ; après une révision ou une proposition périmée, sur le plan
        relu en base (modifications de January comprises)."""
        revision = state.get("revision", 0)
        ctx = context_from_state(state["context"])
        if revision > 0:
            ctx = await _read(deps, state)
        option: ReplanOption | None = state.get("option")  # type: ignore[assignment]
        variables = replan_vars(
            ctx,
            option,
            revision=revision,
            note=state.get("note", ""),
            stale=state.get("stale", False),
        )
        prompt = render_prompt(AGENT, mode="replan", **variables)
        draft = await _write(deps, ctx, option, prompt, revision)
        return {"context": as_json(ctx), "draft": draft.model_dump(mode="json")}

    return propose


def make_preview(deps: GraphDeps) -> Node:
    @node_timeout()
    async def preview(state: ReplanState) -> ReplanState:
        """La proposition rangée et enregistrée par le port, puis annoncée."""
        ctx = context_from_state(state["context"])
        draft = ReplanDraft.model_validate(state["draft"])
        revision = state.get("revision", 0)
        option: ReplanOption | None = state.get("option")  # type: ignore[assignment]
        saved = await deps.ports.replan.preview(
            deps.user_id,
            deps.session_id,
            ctx.program_id,
            draft,
            refs=ctx.refs(),
            option=option,
            revision=revision,
            reason=reason_text(state["trigger"], option, revision, state.get("note", "")),
            week_cap_override=ctx.week_cap_override,
        )
        logger.info(
            "Replanification proposée : session %s, programme %s, version %d, %d retirée(s), "
            "%d ajoutée(s), %d déplacée(s), %d retrait(s) ignoré(s), impossible %s",
            deps.session_id,
            ctx.program_id,
            saved.version,
            saved.removed,
            saved.added,
            saved.moved,
            saved.kept,
            saved.impossible,
        )
        if saved.impossible:
            return {"preview": as_json(saved), "outcome": "impossible"}
        if saved.empty and option is None:
            _say(f"replan-{revision}", draft.summary)
            return {"preview": as_json(saved), "outcome": "empty"}
        _say(f"replan-{revision}", preview_text(draft.summary, saved))
        artifact = {
            "artifact_id": ctx.program_id,
            "kind": "plan_version",
            "title": f"Replanification : {ctx.title}",
            "url": f"/apprendre/programme/{ctx.program_id}/replanification",
        }
        emit("artifact.ready", artifact, agent=AGENT)
        return {"preview": as_json(saved), "outcome": ""}

    return preview


def route_preview(state: ReplanState) -> str:
    return "finalize" if state.get("outcome") in ("impossible", "empty") else "ask_accept"


def ask_accept(state: ReplanState) -> ReplanState:
    """Point d'arrêt : accepter, garder le plan actuel, ou une note pour une autre proposition.
    Rien avant `interrupt()` (la question ne dépend que de l'état) ; une réponse invalide repose
    la question, une note vide avec une aide (« Écris ce que tu veux changer. »)."""
    value = interrupt(accept_payload(state.get("hint", "")))
    answer = parse_accept(value)
    if answer is None:
        return {"answer": None, "hint": EMPTY_NOTE_HINT if empty_note(value) else ""}
    if answer.action == "revise":
        revision = state.get("revision", 0) + 1
        note = answer.note
        return {
            "answer": answer.model_dump(),
            "revision": revision,
            "note": note,
            "stale": False,
            "hint": "",
        }
    return {"answer": answer.model_dump(), "hint": ""}


def route_accept(state: ReplanState) -> str:
    answer = state.get("answer")
    if answer is None:
        return "ask_accept"
    return {"accept": "apply", "refuse": "refuse", "revise": "propose"}[answer["action"]]


def make_apply(deps: GraphDeps) -> Node:
    @node_timeout()
    async def apply(state: ReplanState) -> ReplanState:
        """Version appliquée (idempotent) ; périmée : rien n'est écrit, nouvelle proposition."""
        program_id, version = state["program_id"], state["preview"]["version"]
        applied = await deps.ports.replan.apply(deps.user_id, deps.session_id, program_id, version)
        logger.info(
            "Replanification : session %s, programme %s, version %d, périmée %s",
            deps.session_id,
            program_id,
            version,
            applied.stale,
        )
        if applied.stale:
            revision = state.get("revision", 0)
            _say(f"replan-perimee-{revision}", STALE_NOTE)
            # La note de January reste pour la proposition suivante (D106, relecture m4).
            return {"stale": True, "revision": revision + 1}
        return {"stale": False, "outcome": "accepted"}

    return apply


def route_apply(state: ReplanState) -> str:
    return "propose" if state.get("stale") else "finalize"


def make_refuse(deps: GraphDeps) -> Node:
    @node_timeout()
    async def refuse(state: ReplanState) -> ReplanState:
        program_id, version = state["program_id"], state["preview"]["version"]
        await deps.ports.replan.refuse(deps.user_id, deps.session_id, program_id, version)
        logger.info(
            "Replanification refusée : session %s, programme %s, version %d",
            deps.session_id,
            program_id,
            version,
        )
        return {"outcome": "refused"}

    return refuse


def finalize(state: ReplanState) -> ReplanState:
    """La fin annoncée : appliquée, refusée, rien à changer ou rangement impossible."""
    text = end_text(state.get("outcome", ""), state["preview"]["version"])
    _say("replan-fin", text)
    return {"summary": text}
