"""The Verifier prepares a targeted draft."""

from typing import Annotated, Protocol

from pydantic import BaseModel, Field, StrictInt, StringConstraints

from app.core.errors import AppError

GRAPH = "lesson_update"


class BlockRevision(BaseModel):
    block: StrictInt = Field(ge=1)
    code: str = Field(min_length=1, max_length=3500)


class SuggestedRevision(BaseModel):
    explanation: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=1200)
    ]
    replacements: list[BlockRevision] = Field(min_length=1, max_length=8)


class LessonUpdatePort(Protocol):
    async def context(
        self, user_id: str, session_id: str, proposal_id: str
    ) -> dict[str, object] | None: ...

    async def prepare(
        self, user_id: str, session_id: str, proposal_id: str, revision: SuggestedRevision
    ) -> None: ...


class _Unavailable:
    async def context(
        self, user_id: str, session_id: str, proposal_id: str
    ) -> dict[str, object] | None:
        raise AppError("lesson_update_unavailable", "Lesson watch is unavailable.", 503)

    async def prepare(
        self, user_id: str, session_id: str, proposal_id: str, revision: SuggestedRevision
    ) -> None:
        raise AppError("lesson_update_unavailable", "Lesson watch is unavailable.", 503)


NO_LESSON_UPDATE: LessonUpdatePort = _Unavailable()
