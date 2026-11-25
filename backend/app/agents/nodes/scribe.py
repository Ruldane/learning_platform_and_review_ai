"""The Scribe (SPEC 3.3, 9.1, D85): draws on the board in Mermaid `flowchart` (never any
coordinates) and keeps the minutes. It takes no position.

The Mermaid is parsed by a strict grammar then re-emitted (`mermaid_rules`): refused, a new
request; still refused (or invalid output), no board, the Council continues (log:
identifiers). Only the re-emitted version is recorded and published. Each board has its step
number, taken from `board_step` of the input state: a replayed node rewrites the same steps,
which the port records only once (idempotent per session and step)."""

import json
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.nodes.council_rules import (
    MINUTES_WORDS,
    Node,
    citation_entries,
    goal_vars,
    notes_prompt,
    transcript_prompt,
)
from app.agents.nodes.mermaid_rules import (
    MAX_LABEL_CHARS,
    MAX_MERMAID_LINES,
    MAX_NODES,
    mermaid_problems,
    normalize_mermaid,
)
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.events import BoardKind
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.speech import speak
from app.agents.runtime.structured import structured_call
from app.agents.state.learning_council import CouncilState
from app.core.errors import AppError

AGENT = "scribe"
INVALID_OUTPUT_CODE = "structured_output_invalid"
BOARDS_TIMEOUT_S = 300  # a timeline per proposal and one comparison, two tries each
_FENCE = re.compile(r"^```[a-z]*\s*\n|\n?```\s*$")

logger = logging.getLogger(__name__)


MIN_TITLE_CHARS = 3


class BoardDraft(BaseModel):
    title: str = Field(min_length=MIN_TITLE_CHARS, max_length=120)
    mermaid: str = Field(min_length=10, max_length=6000)


def _title_problems(title: str) -> list[str]:
    if len(title) < MIN_TITLE_CHARS:
        return [f"Use a title with at least {MIN_TITLE_CHARS} characters."]
    return []


def _clean(code: str) -> str:
    """Removes a possible code fence around the diagram."""
    return _FENCE.sub("", code.strip()).strip()


def _board_prompt(state: CouncilState, kind: BoardKind, brief: str) -> str:
    return render_prompt(
        AGENT,
        mode="board",
        kind=kind,
        **goal_vars(state),
        brief=brief,
        max_lines=MAX_MERMAID_LINES,
        max_nodes=MAX_NODES,
        max_label=MAX_LABEL_CHARS,
    )


async def _valid_draft(
    deps: GraphDeps, messages: list[BaseMessage], step: int
) -> BoardDraft | None:
    """A diagram that passes the grammar, in two requests at most, returned **normalized**
    (re-emitted by `normalize_mermaid`: the model's raw Mermaid never comes out); else `None`."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    for attempt in range(2):
        try:
            draft = await structured_call(
                model,
                BoardDraft,
                messages,
                agent=AGENT,
                step=f"tableau-{step}",
                intent="drawing on the board",
            )
        except AppError as exc:
            if exc.code != INVALID_OUTPUT_CODE:
                raise
            return None
        # Once cleaned, the draft is not validated again (a `ValidationError` would leave the node
        # and make the Council fail): its defects are refusals, hence a new request.
        title, code = " ".join(draft.title.split()), _clean(draft.mermaid)
        problems = _title_problems(title) + mermaid_problems(code)
        if not problems:
            return BoardDraft.model_construct(title=title, mermaid=normalize_mermaid(code))
        if attempt == 0:
            refused = "\n".join(f"- {problem}" for problem in problems)
            shown = {"title": title, "mermaid": code}
            messages = [
                *messages,
                AIMessage(json.dumps(shown, ensure_ascii=False)),
                HumanMessage(
                    f"Diagram rejected:\n{refused}\nRedraw it using the supported syntax."
                ),
            ]
    return None


async def draw(
    deps: GraphDeps, state: CouncilState, *, kind: BoardKind, step: int, brief: str
) -> str | None:
    """Draws a board, records it (idempotent) then publishes `board.update`; returns its id, or
    `None` if no valid diagram was obtained."""
    messages: list[BaseMessage] = [
        SystemMessage(_board_prompt(state, kind, brief)),
        HumanMessage("Draw the board."),
    ]
    draft = await _valid_draft(deps, messages, step)
    if draft is None:
        logger.warning("Board not drawn (%s): session %s, step %d", kind, deps.session_id, step)
        return None
    board_id = await deps.ports.council.save_board(
        deps.user_id,
        deps.session_id,
        state["goal_id"],
        step=step,
        kind=kind,
        title=draft.title,
        mermaid=draft.mermaid,
    )
    emit(
        "board.update",
        {
            "mermaid": draft.mermaid,
            "step": step,
            "board_id": board_id,
            "kind": kind,
            "title": draft.title,
        },
        agent=AGENT,
    )
    return board_id


def make_domain_map(deps: GraphDeps) -> Node:
    @node_timeout()
    async def domain_map(state: CouncilState) -> CouncilState:
        """Domain map, based on the round 1 positions."""
        step = state.get("board_step", 0) + 1
        positions = [t for t in state.get("turns", []) if t["round"] == 1]
        await draw(deps, state, kind="domain_map", step=step, brief=transcript_prompt(positions))
        return {"board_step": step}

    return domain_map


def make_prerequisites(deps: GraphDeps) -> Node:
    @node_timeout()
    async def prerequisites(state: CouncilState) -> CouncilState:
        """Prerequisites graph, based on the whole debate."""
        step = state.get("board_step", 0) + 1
        brief = transcript_prompt(state.get("turns", []))
        await draw(deps, state, kind="prerequisites", step=step, brief=brief)
        return {"board_step": step}

    return prerequisites


def make_minutes(deps: GraphDeps) -> Node:
    @node_timeout()
    async def minutes(state: CouncilState) -> CouncilState:
        """Minutes (200 words at most, cited), kept on the goal for the Strategist."""
        prompt = render_prompt(
            AGENT,
            mode="minutes",
            **goal_vars(state),
            transcript=transcript_prompt(state.get("turns", [])),
            notes=notes_prompt(state.get("notes", [])),
            max_words=MINUTES_WORDS,
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        spoken = await speak(
            model,
            [SystemMessage(prompt), HumanMessage("Write the minutes.")],
            agent=AGENT,
            step=f"compte-rendu-{state.get('round', 1)}",
            intent="writing the minutes",
            catalog=citation_entries(state),
            max_words=MINUTES_WORDS,
        )
        await deps.ports.council.save_minutes(deps.user_id, state["goal_id"], spoken.text)
        return {"minutes": spoken.text}

    return minutes


def _proposal_lines(proposal: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Name: {proposal['name']}",
            f"Promise: {proposal.get('promise', '')}",
            f"Duration: {proposal.get('duration_weeks', '?')} weeks, "
            f"{proposal.get('weekly_hours', '?')} h per week",
            f"Skills: {', '.join(proposal.get('skills', []))}",
            f"Final project: {proposal.get('final_project', '')}",
            f"Trade-offs: {' ; '.join(proposal.get('tradeoffs', []))}",
        ]
    )


def _proposal_brief(proposal: dict[str, Any]) -> str:
    return untrusted(_proposal_lines(proposal), f"proposal {proposal['rank']}")


def make_proposal_boards(deps: GraphDeps) -> Node:
    @node_timeout(BOARDS_TIMEOUT_S)
    async def proposal_boards(state: CouncilState) -> CouncilState:
        """A timeline per proposal (attached to it), then the comparison of the batch."""
        proposals = state.get("proposals", [])
        step = state.get("board_step", 0)
        for proposal in proposals:
            step += 1
            board_id = await draw(
                deps, state, kind="timeline", step=step, brief=_proposal_brief(proposal)
            )
            if board_id is not None:
                await deps.ports.council.attach_board(
                    deps.user_id, proposal["proposal_id"], board_id
                )
        step += 1
        brief = "\n\n".join(_proposal_brief(p) for p in proposals)
        await draw(deps, state, kind="comparison", step=step, brief=brief)
        return {"board_step": step}

    return proposal_boards
