"""The Strategist replans the rest of the program (SPEC F13, D105): flow `replan`.

`context` reads the review, the options and the plan to do by references (port); `ask_option`
and `ask_accept` only do `interrupt()` then parse the answer (pure, nothing before the stop,
SPEC 9.4). `propose` asks the model for what its rights allow (option schema, or additions only
with the `gap` trigger, `replan_gap`); an unknown reference, or a `gap` addition that names no
skill, is sent back once to the model, then removed. `preview` has the port file and record the
proposal (idempotent per `(session, revision)`), separate from `propose`: replayed, it does not
call the model again. `apply` and `refuse` are idempotent; a stale acceptance (lines changed)
restarts from `propose` on the reread plan."""

import logging
from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from app.agents.nodes.strategist.replan_gap import cleaned, draft_of, problem_text, schema_of
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

MAX_ASKS = 2  # one request + one re-request if a reference is unknown
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
        trigger=state["trigger"],  # type: ignore[arg-type]  # validated by `ReplanInput`
        review_entry_id=state.get("review_entry_id"),
        available_minutes=state.get("available_minutes"),
        message=state.get("message"),
        skills=state.get("skills") or [],
    )


def make_context(deps: GraphDeps) -> Node:
    @node_timeout()
    async def context(state: ReplanState) -> ReplanState:
        """The plan snapshot, then the review announced if there is one."""
        found = await _read(deps, state)
        if found.review is not None:
            _say("replan-bilan", found.review.text)
        return {"context": as_json(found), "revision": 0, "note": "", "option": None}

    return context


def route_start(state: ReplanState) -> str:
    """The `gap` trigger has no option (additions only, D123): `ask_option` is skipped."""
    if state.get("trigger") == "gap" or not state["context"]["options"]:
        return "propose"
    return "ask_option"


def ask_option(state: ReplanState) -> ReplanState:
    """Stop point: the option (reduce or push back, bring forward or deepen)."""
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
            schema_of(option, ctx),
            messages,
            agent=AGENT,
            step=f"replanification-{revision}-{ask}",
            intent="Updating the plan" if ask == 1 else "Revising the proposal",
        )
        draft = draft_of(found, option, ctx)
        problem = problem_text(draft, ctx)
        if problem is None:
            return draft
        messages += [AIMessage(found.model_dump_json()), HumanMessage(problem)]
    draft, removed = cleaned(draft, ctx)
    logger.info(
        "Replanning: %d invalid removal(s) or addition(s) dropped (session %s, proposal %d)",
        removed,
        deps.session_id,
        revision,
    )
    return draft


def make_propose(deps: GraphDeps) -> Node:
    @node_timeout(PROPOSE_TIMEOUT_S)
    async def propose(state: ReplanState) -> ReplanState:
        """The Strategist's draft; after a revision or a stale proposal, on the plan reread from
        the database (January's changes included)."""
        revision = state.get("revision", 0)
        ctx = context_from_state(state["context"])
        if revision > 0:
            ctx = await _read(deps, state)
        if state["trigger"] == "reading":
            draft = ReplanDraft(summary="Added the chosen reading to the program.")
            return {"context": as_json(ctx), "draft": draft.model_dump(mode="json")}
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
        """The proposal filed and recorded by the port, then announced."""
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
            "Replanning proposed: session %s, program %s, version %d, %d removed, "
            "%d added, %d moved, %d removal(s) ignored, impossible %s",
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
            outcome = "finished" if saved.finished else "impossible"
            return {"preview": as_json(saved), "outcome": outcome}
        if saved.empty and option is None:
            # Only "Nothing to change" is said: the Strategist's summary could contradict it
            # (reread 5.8 m5, final review of phase 5).
            return {"preview": as_json(saved), "outcome": "empty"}
        _say(f"replan-{revision}", preview_text(draft.summary, saved))
        artifact = {
            "artifact_id": ctx.program_id,
            "kind": "plan_version",
            "title": f"Replanification : {ctx.title}",
            "url": f"/learn/programs/{ctx.program_id}/replan",
        }
        emit("artifact.ready", artifact, agent=AGENT)
        return {"preview": as_json(saved), "outcome": ""}

    return preview


def route_preview(state: ReplanState) -> str:
    return (
        "finalize" if state.get("outcome") in ("impossible", "finished", "empty") else "ask_accept"
    )


def ask_accept(state: ReplanState) -> ReplanState:
    """Stop point: accept, keep the current plan, or a note for another proposal.
    Nothing before `interrupt()` (the question only depends on the state); an invalid answer asks
    the question again, an empty note with a hint ("Describe what you'd like to change.")."""
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
        """Version applied (idempotent); stale: nothing is written, new proposal."""
        program_id, version = state["program_id"], state["preview"]["version"]
        applied = await deps.ports.replan.apply(deps.user_id, deps.session_id, program_id, version)
        logger.info(
            "Replanning: session %s, program %s, version %d, stale %s",
            deps.session_id,
            program_id,
            version,
            applied.stale,
        )
        if applied.stale:
            revision = state.get("revision", 0)
            _say(f"replan-perimee-{revision}", STALE_NOTE)
            # January's note stays for the next proposal (D106, reread m4).
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
            "Replanning refused: session %s, program %s, version %d",
            deps.session_id,
            program_id,
            version,
        )
        return {"outcome": "refused"}

    return refuse


def finalize(state: ReplanState) -> ReplanState:
    """The announced end: applied, refused, nothing to change or filing impossible."""
    text = end_text(state.get("outcome", ""), state["preview"]["version"], state["trigger"])
    _say("replan-fin", text)
    return {"summary": text}
