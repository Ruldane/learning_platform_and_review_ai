"""Ce que les nœuds de l'Intervieweur ont en commun (D145) : son nom, le type d'un nœud, le contexte
relu depuis l'état et la question publiée dans le fil."""

from typing import Protocol

from app.agents.runtime.emit import emit
from app.agents.state.interview import InterviewState
from app.agents.tools.interview_schema import InterviewContext

AGENT = "interviewer"
# Lenteur, panne passagère, réponse vide ou illisible : un nœud se replie. Le reste échoue, dont
# `token_cap_reached` (le plafond de tokens arrête la session) et `llm_rate_limited` (D115 n° 17).
RECOVERABLE_CODES = frozenset(
    {"llm_timeout", "llm_unavailable", "llm_empty_reply", "structured_output_invalid"}
)


class Node(Protocol):
    async def __call__(self, state: InterviewState) -> InterviewState: ...


def context_of(state: InterviewState) -> InterviewContext:
    return InterviewContext.model_validate(state["context"])


def say_question(number: int, text: str, *, follow_up: bool = False) -> None:
    """La question (ou la relance) dans le fil ; même identifiant si le nœud est rejoué."""
    suffix = "-relance" if follow_up else ""
    emit(
        "agent.message",
        {"message_id": f"{AGENT}-q{number}{suffix}", "text": text},
        agent=AGENT,
    )
