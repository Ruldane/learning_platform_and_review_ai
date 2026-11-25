"""Port of the learning council (D84). `app.agents` imports no feature (contract 6): it
describes here what the `learning_council` graph needs (the goal, the framing, the boards,
the proposals, the choice); the composition plugs in the `learning` feature implementation,
as for memory (D68) and web search (D77).

Each write is idempotent: a node replayed after a stop (SPEC 9.4) rewrites the same
thing, never one more line.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field

from app.agents.runtime.payloads import BoardKind
from app.agents.runtime.prose import Prose, ShortenToMax
from app.core.errors import AppError

_Item = Annotated[str, Field(min_length=1, max_length=120)]
_Tradeoff = Annotated[str, Field(min_length=1, max_length=300), ShortenToMax()]


@dataclass(frozen=True)
class GoalBrief:
    """The goal as January entered it (free text, target role, deadline, budget)."""

    goal_id: str
    text: str
    target_role: str | None
    deadline: date | None
    weekly_minutes: int | None
    framing: Mapping[str, str]  # framing answers already stored, by question id


@dataclass(frozen=True)
class FramingQuestion:
    id: str  # `q1` to `q5`, set by the code
    question: str


class ProposalDraft(BaseModel):
    """A proposed path (SPEC 3.1, step 5): the Strategist's structured output (task 4.4)."""

    name: str = Field(min_length=3, max_length=80)
    promise: Prose = Field(min_length=10, max_length=300)
    duration_weeks: int = Field(ge=1, le=52)
    weekly_hours: int = Field(ge=1, le=40)
    skills: list[_Item] = Field(min_length=1, max_length=15)
    final_project: Prose = Field(min_length=10, max_length=400)
    tradeoffs: list[_Tradeoff] = Field(min_length=1, max_length=5)


@dataclass(frozen=True)
class ProposalRef:
    proposal_id: str
    rank: int
    name: str


@dataclass(frozen=True)
class SavedProposal:
    """A proposal from an already stored batch, with its details as written (D85)."""

    ref: ProposalRef
    draft: ProposalDraft


@dataclass(frozen=True)
class Choice:
    """January's choice: a path (`choose`, an id) or a mix of two (`mix`)."""

    action: Literal["choose", "mix"]
    proposal_ids: tuple[str, ...]
    start_date: date | None = None


class CouncilStore(Protocol):
    async def goal(self, user_id: str, goal_id: str) -> GoalBrief:
        """The user's goal; `goal_not_found` (404) if it is not theirs."""
        ...

    async def save_framing(
        self,
        user_id: str,
        goal_id: str,
        questions: Sequence[FramingQuestion],
        answers: Mapping[str, str],
    ) -> None:
        """Framing questions and answers: overwrites the previous ones (idempotent)."""
        ...

    async def save_board(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        step: int,
        kind: BoardKind,
        title: str,
        mermaid: str,
    ) -> str:
        """A state of the Scribe's board; idempotent per `(session, step)`. Returns its id."""
        ...

    async def save_minutes(self, user_id: str, goal_id: str, text: str) -> None:
        """Scribe's minutes (overwrites the previous ones)."""
        ...

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        batch: int,
        proposals: Sequence[ProposalDraft],
    ) -> list[ProposalRef]:
        """A batch of proposals; idempotent per `(session, batch)`: replayed, returns the batch
        already written."""
        ...

    async def saved_proposals(
        self, user_id: str, session_id: str, *, batch: int
    ) -> list[SavedProposal]:
        """The `batch` of the session as stored, by rank; empty if it does not exist. A
        replayed `propose` rereads it instead of calling the model again (D85)."""
        ...

    async def attach_board(self, user_id: str, proposal_id: str, board_id: str) -> None: ...

    async def record_choice(
        self, user_id: str, session_id: str, goal_id: str, choice: Choice
    ) -> None:
        """Marks the choice (one proposal chosen per batch at most); idempotent."""
        ...

    async def start_program(self, user_id: str, goal_id: str, choice: Choice) -> str:
        """Starts the `program_builder` session (only one per goal); returns its id."""
        ...


def council_unavailable() -> AppError:
    return AppError("council_unavailable", "The Council is unavailable in this runtime.", 503)


class _NoCouncil:
    """Engine default value (existing tests, starts without the Council)."""

    async def goal(self, user_id: str, goal_id: str) -> GoalBrief:
        raise council_unavailable()

    async def save_framing(
        self,
        user_id: str,
        goal_id: str,
        questions: Sequence[FramingQuestion],
        answers: Mapping[str, str],
    ) -> None:
        raise council_unavailable()

    async def save_board(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        step: int,
        kind: BoardKind,
        title: str,
        mermaid: str,
    ) -> str:
        raise council_unavailable()

    async def save_minutes(self, user_id: str, goal_id: str, text: str) -> None:
        raise council_unavailable()

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        batch: int,
        proposals: Sequence[ProposalDraft],
    ) -> list[ProposalRef]:
        raise council_unavailable()

    async def saved_proposals(
        self, user_id: str, session_id: str, *, batch: int
    ) -> list[SavedProposal]:
        raise council_unavailable()

    async def attach_board(self, user_id: str, proposal_id: str, board_id: str) -> None:
        raise council_unavailable()

    async def record_choice(
        self, user_id: str, session_id: str, goal_id: str, choice: Choice
    ) -> None:
        raise council_unavailable()

    async def start_program(self, user_id: str, goal_id: str, choice: Choice) -> str:
        raise council_unavailable()


NO_COUNCIL: CouncilStore = _NoCouncil()
