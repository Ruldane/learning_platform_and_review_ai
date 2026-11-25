"""The Council Moderator (SPEC 3.1, 9.1): reads the goal and the memory, prepares 5 framing
questions at most, stops to ask them (stop point no. 1), then records the answers and prepares
the Scout's request. During the debate, it opens and closes each round
(`moderator_rounds`, D85).

The stop lives alone in `ask_framing`: no side effect before `interrupt()` (SPEC 9.4).
The answers are written in the next node, idempotent (the port overwrites).

Goal, target role and answers come from January: not wrapped in the prompts (D53 section 5),
never logged (17.2)."""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from app.agents.nodes.council_rules import Node, deadline_text
from app.agents.nodes.memory_context import load_memory_context
from app.agents.nodes.moderator_rounds import (
    AGENT,
    RoundPlan,
    RoundReview,
    make_round_end,
    make_round_start,
)
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.prose import Prose
from app.agents.runtime.structured import structured_call
from app.agents.state.learning_council import CouncilState
from app.agents.tools.council_port import FramingQuestion, GoalBrief

MAX_FRAMING_QUESTIONS = 5
MAX_ANSWER_CHARS = 2000
MAX_QUERY_CHARS = 300
FRAMING_PROMPT = "Answer any of these questions, then start the research."
GO = {"value": "go", "label": "Start research"}


class FramingQuestionModel(BaseModel):
    question: Prose = Field(min_length=5, max_length=300)


class FramingPlan(BaseModel):
    questions: list[FramingQuestionModel] = Field(max_length=MAX_FRAMING_QUESTIONS)


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _goal_state(goal: GoalBrief) -> dict[str, Any]:
    return {
        "goal_id": goal.goal_id,
        "text": goal.text,
        "target_role": goal.target_role,
        "deadline": goal.deadline.isoformat() if goal.deadline else None,
        "weekly_minutes": goal.weekly_minutes,
        "framing": dict(goal.framing),
    }


def make_context(deps: GraphDeps) -> Node:
    @node_timeout()
    async def context(state: CouncilState) -> CouncilState:
        """The goal (Council port), then the memory context close to its text."""
        goal = await deps.ports.council.goal(deps.user_id, state["goal_id"])
        memory = await load_memory_context(deps, objective=goal.text, agent=AGENT)
        return {"goal": _goal_state(goal), "context": memory.as_prompt()}

    return context


def make_frame(deps: GraphDeps) -> Node:
    @node_timeout()
    async def frame(state: CouncilState) -> CouncilState:
        goal = state["goal"]
        prompt = render_prompt(
            AGENT,
            mode="frame",
            goal=goal["text"],
            target_role=goal.get("target_role") or "not specified",
            deadline=deadline_text(goal),
            weekly_minutes=goal.get("weekly_minutes"),
            context=state.get("context", ""),
            max_questions=MAX_FRAMING_QUESTIONS,
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        plan = await structured_call(
            model,
            FramingPlan,
            [SystemMessage(prompt), HumanMessage("Prepare the framing questions.")],
            agent=AGENT,
            step="cadrage",
            intent="preparing the framing questions",
        )
        questions = [
            {"id": f"q{index}", "question": _one_line(item.question)}
            for index, item in enumerate(plan.questions[:MAX_FRAMING_QUESTIONS], start=1)
        ]
        return {"framing_questions": questions}

    return frame


def framing_answers(value: Any, ids: list[str]) -> dict[str, str]:
    """Answers read from the resume: `{"answers": {id: text}}`; unknown ids and empty answers
    ignored, each answer cut at 2,000 characters. `"go"` or any other shape: none."""
    raw = value.get("answers") if isinstance(value, dict) else None
    if not isinstance(raw, dict):
        return {}
    answers: dict[str, str] = {}
    for qid in ids:
        text = raw.get(qid)
        if isinstance(text, str) and text.strip():
            answers[qid] = text.strip()[:MAX_ANSWER_CHARS]
    return answers


def ask_framing(state: CouncilState) -> CouncilState:
    """Stop point no. 1 (end of the framing), mandatory even without a question. Nothing before
    `interrupt()`: the node restarts from its beginning on resume."""
    questions = state.get("framing_questions", [])
    value = interrupt(
        {
            "kind": "framing",
            "question": FRAMING_PROMPT,
            "options": [GO],
            "fields": [{"id": q["id"], "label": q["question"]} for q in questions],
        }
    )
    return {"framing_answers": framing_answers(value, [q["id"] for q in questions])}


def research_query(
    goal: dict[str, Any], questions: list[dict[str, str]], answers: dict[str, str]
) -> str:
    """The Scout's request: goal, target role, then answers in the order of the questions,
    on one line, 300 characters at most."""
    parts = [goal["text"], goal.get("target_role") or ""]
    parts += [answers.get(q["id"], "") for q in questions]
    line = " ; ".join(clean for part in parts if (clean := _one_line(part)))
    return line[:MAX_QUERY_CHARS].rstrip(" ;")


def make_apply_framing(deps: GraphDeps) -> Node:
    @node_timeout()
    async def apply_framing(state: CouncilState) -> CouncilState:
        """Records questions and answers (the port overwrites: replayed, it rewrites the same
        thing), then prepares the research."""
        questions = state.get("framing_questions", [])
        answers = state.get("framing_answers", {})
        await deps.ports.council.save_framing(
            deps.user_id,
            state["goal_id"],
            [FramingQuestion(q["id"], q["question"]) for q in questions],
            answers,
        )
        return {"query": research_query(state["goal"], questions, answers), "urls": []}

    return apply_framing


__all__ = [
    "AGENT",
    "RoundPlan",
    "RoundReview",
    "ask_framing",
    "framing_answers",
    "make_apply_framing",
    "make_context",
    "make_frame",
    "make_round_end",
    "make_round_start",
    "research_query",
]
