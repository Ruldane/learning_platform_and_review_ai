from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel

from app.agents.tools.feynman_port import FeynmanAssessment, FeynmanContext, FeynmanExchange
from app.core.errors import AppError

CONVERSATION_GRAPH = "conversation"
LESSON_PROFESSOR = "lesson_professor"
TRAINING_TUTOR = "training_tutor"
BRAIN_LIBRARIAN = "brain_librarian"
CLASSROOM_SCOPE = "classroom"
TURN_TOKEN_LIMIT = 12_000

FocusOutcome = Literal["correct", "retry"]

ClassmateRole = Literal["beginner", "peer", "advanced"]
CLASSMATE_ROLES: tuple[ClassmateRole, ...] = ("beginner", "peer", "advanced")


class ClassmateReply(BaseModel):
    role: ClassmateRole
    answer: str


class ConversationSource(BaseModel):
    kind: Literal["lesson", "memory"]
    id: UUID
    title: str
    excerpt: str | None


class ConversationPractice(BaseModel):
    lesson_id: UUID
    front: str
    back: str


@dataclass(frozen=True)
class ConversationReference:
    source: ConversationSource
    material: str
    primary: bool = False


@dataclass(frozen=True)
class ConversationExchange:
    question: str
    answer: str


@dataclass(frozen=True)
class ConversationContext:
    agent: str
    question: str
    strong: bool
    history: Sequence[ConversationExchange]
    references: Sequence[ConversationReference]
    used_tokens: int
    selection: str | None = None
    mode: str | None = None
    context_notes: dict[str, str] | None = None


class ConversationStore(Protocol):
    async def feynman_context(
        self, user_id: str, session_id: str, thread_id: str, turn_id: str
    ) -> FeynmanContext | None: ...

    async def save_feynman(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        turn_id: str,
        *,
        assessment: FeynmanAssessment,
        exchange: FeynmanExchange,
    ) -> None: ...

    async def context(
        self, user_id: str, session_id: str, thread_id: str, turn_id: str
    ) -> ConversationContext | None: ...

    async def save_reply(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        turn_id: str,
        *,
        answer: str,
        sources: Sequence[ConversationSource],
        practice: Sequence[ConversationPractice] = (),
        context_notes: dict[str, str] | None = None,
        classmates: Sequence[ClassmateReply] = (),
        focus_outcome: FocusOutcome | None = None,
    ) -> None: ...


def _unavailable() -> AppError:
    return AppError("conversation_unavailable", "La conversation est indisponible.", 503)


class _NoConversation:
    async def feynman_context(
        self, user_id: str, session_id: str, thread_id: str, turn_id: str
    ) -> FeynmanContext | None:
        raise _unavailable()

    async def save_feynman(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        turn_id: str,
        *,
        assessment: FeynmanAssessment,
        exchange: FeynmanExchange,
    ) -> None:
        raise _unavailable()

    async def context(
        self, user_id: str, session_id: str, thread_id: str, turn_id: str
    ) -> ConversationContext | None:
        raise _unavailable()

    async def save_reply(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        turn_id: str,
        *,
        answer: str,
        sources: Sequence[ConversationSource],
        practice: Sequence[ConversationPractice] = (),
        context_notes: dict[str, str] | None = None,
        classmates: Sequence[ClassmateReply] = (),
        focus_outcome: FocusOutcome | None = None,
    ) -> None:
        raise _unavailable()


NO_CONVERSATION: ConversationStore = _NoConversation()
