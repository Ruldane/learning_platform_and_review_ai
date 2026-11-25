"""What the Interviewer nodes have in common (D145): its name, the type of a node, the context
reread from the state and the question published in the thread."""

from typing import Protocol

from app.agents.runtime.emit import emit
from app.agents.state.interview import InterviewState
from app.agents.tools.interview_schema import InterviewContext

AGENT = "interviewer"
# Slowness, transient failure, empty or unreadable reply: a node falls back. The rest fails,
# including `token_cap_reached` (the token cap stops the session) and `llm_rate_limited`
# (D115 no. 17).
RECOVERABLE_CODES = frozenset(
    {"llm_timeout", "llm_unavailable", "llm_empty_reply", "structured_output_invalid"}
)


class Node(Protocol):
    async def __call__(self, state: InterviewState) -> InterviewState: ...


def context_of(state: InterviewState) -> InterviewContext:
    return InterviewContext.model_validate(state["context"])


def say_question(number: int, text: str, *, follow_up: bool = False) -> None:
    """The question (or the follow-up) in the thread; same identifier if the node is replayed."""
    suffix = "-relance" if follow_up else ""
    emit(
        "agent.message",
        {"message_id": f"{AGENT}-q{number}{suffix}", "text": text},
        agent=AGENT,
    )
