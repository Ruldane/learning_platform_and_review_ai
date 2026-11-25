"""The Strategist writes the program week by week (SPEC 3.4; stop point no. 3, D86).

`draft` asks the model for a `PlanDraft` and has it checked by the feature's rules (port,
`check_draft`): the problems go back to the model, twice at most (`MAX_PLAN_ASKS` = one request
and two re-requests); after that the draft is kept as is and it is the code's filing (`save_draft`:
acquired skills, 85%, practice and quiz) that brings it to the rules (D83 section 4).

`save` records the version (idempotent per `(session, revision)`); `ask_validation` only does
`interrupt()` then parses the answer (pure); a revision restarts from `draft` with the current
plan reread from the database (January's changes included) and her note; `finalize` validates
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
from app.agents.runtime.played_model import refresh_updated_brief
from app.agents.runtime.structured import structured_call
from app.agents.state.program_builder import ProgramState
from app.agents.tools.plan_schema import PlanDraft
from app.agents.tools.program_port import DraftSaved

AGENT = "strategist"
MAX_PLAN_ASKS = 3  # one request + two re-requests with the problems from `check_draft`
MAX_PROBLEMS_SHOWN = 30
MAX_NOTE_CHARS = 2000
PLAN_TIMEOUT_S = 600  # three requests of a complete program to the strong model
PLAN_REQUEST = "Write the program week by week."
VALIDATION_INTERRUPT: dict[str, Any] = {
    "kind": "validate_program",
    "question": (
        "Arrange the tasks in the calendar, then validate the program or request a revision."
    ),
    "options": [{"value": "validate", "label": "Validate the program"}],
    "fields": [{"id": "note", "label": "What should change in a revision?"}],
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
        """Goal, chosen proposals, budget, acquired skills, language and minutes (port)."""
        found = await deps.ports.program.context(
            deps.user_id, state["goal_id"], state["proposal_ids"], None
        )
        return {"plan_vars": context_vars(found), "revision": 0, "note": ""}

    return context


def _problems_text(problems: list[str]) -> str:
    shown = [f"- {problem}" for problem in problems[:MAX_PROBLEMS_SHOWN]]
    if len(problems) > MAX_PROBLEMS_SHOWN:
        shown.append(f"- ... and {len(problems) - MAX_PROBLEMS_SHOWN} more problems.")
    return (
        "Your program does not follow the rules:\n"
        + "\n".join(shown)
        + "\nFix it and return the complete program again, all the weeks."
    )


async def _write(deps: GraphDeps, goal_id: str, prompt: str, revision: int) -> PlanDraft:
    """One request, then two re-requests at most with the problems; the last one is kept."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(PLAN_REQUEST)]
    check = deps.ports.program.check_draft
    found: PlanDraft | None = None
    problems: list[str] = []
    for ask in range(1, MAX_PLAN_ASKS + 1):
        if found is not None:
            messages += [AIMessage(found.model_dump_json()), HumanMessage(_problems_text(problems))]
        found = await structured_call(
            refresh_updated_brief(model),
            PlanDraft,
            messages,
            agent=AGENT,
            step=f"programme-{revision}-{ask}",
            intent="writing the program" if ask == 1 else "revising the program",
        )
        problems = await check(deps.user_id, goal_id, found)
        if not problems:
            return found
    logger.info(
        "Program: draft kept with %d problem(s), filed by the rules (session %s, revision %d)",
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
        if revision > 0:  # the plan is in the database: reread, January's changes included
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
            note=untrusted(note, "January's revision note") if note else "",
        )
        written = await _write(deps, state["goal_id"], prompt, revision)
        return {"draft": written.model_dump(mode="json"), "plan_vars": plan_vars}

    return draft


def _reason(revision: int, note: str) -> str:
    if revision == 0:
        return "First version by the Strategist"
    return (f"Revision {revision}: {note}" if note else f"Revision {revision}")[:300]


def _saved_text(title: str, saved: DraftSaved) -> str:
    parts = [
        f'Program "{title}": {saved.weeks} week(s), {hours(saved.total_minutes)} '
        "planned, never more than 85% of your weekly budget."
    ]
    if saved.skipped_modules:
        parts.append(f"Already acquired, skipped: {', '.join(saved.skipped_modules)}.")
    if saved.moved_tasks:
        parts.append(f"{saved.moved_tasks} task(s) moved to the following week to fit the budget.")
    return " ".join(parts)


def make_save(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save(state: ProgramState) -> ProgramState:
        """Version recorded (idempotent per `(session, revision)`), then announced."""
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
            "Program stored: session %s, program %s, version %d",
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
            "url": f"/learn/programs/{saved.program_id}",
        }
        emit("artifact.ready", artifact, agent=AGENT)
        return {"saved": asdict(saved)}

    return save


def parse_validation(value: Any) -> ValidationAnswer | None:
    """`"validate"`, `{"action": "validate"}`, `{"action": "revise", "note": ...}` or
    `{"answers": {"note": ...}}` (revision). Note cut at 2,000 characters rather than refused
    (January's input is never lost). Any other shape: `None`."""
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
    """Stop point no. 3. Nothing before `interrupt()`; an invalid answer asks the question again."""
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
        """Program validated (idempotent: a replayed node revalidates with no further effect)."""
        program_id = state["saved"]["program_id"]
        await deps.ports.program.validate(deps.user_id, deps.session_id, program_id)
        logger.info("Program validated: session %s, program %s", deps.session_id, program_id)
        summary = f"Validated the program “{state['draft']['title']}”."
        emit("agent.message", {"message_id": f"{AGENT}-validation", "text": summary}, agent=AGENT)
        return {"summary": summary}

    return finalize
