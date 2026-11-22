"""Échanges du Vérificateur avec un exercice de lecture critique."""

from dataclasses import dataclass
from typing import Protocol, Self

from pydantic import BaseModel, Field, model_validator

HUNT_GRAPH = "lesson_hunt"


class ErrorEdit(BaseModel):
    source: str = Field(min_length=8, max_length=1200)
    replacement: str = Field(min_length=8, max_length=1200)
    explanation: str = Field(min_length=8, max_length=900)

    @model_validator(mode="after")
    def is_a_change(self) -> Self:
        if self.source.strip() == self.replacement.strip() or not self.replacement.strip():
            raise ValueError("Le passage modifié doit contenir une erreur distincte.")
        return self


class ErrorPair(BaseModel):
    edits: list[ErrorEdit] = Field(min_length=2, max_length=2)


class AnswerFeedback(BaseModel):
    spotted: bool
    explained: bool
    feedback: str = Field(min_length=1, max_length=850)


class HuntAssessment(BaseModel):
    answers: list[AnswerFeedback] = Field(min_length=2, max_length=2)


@dataclass(frozen=True)
class HuntContext:
    title: str
    source: str
    errors: ErrorPair | None
    responses: list[str] | None
    stage: str


class LessonHuntStore(Protocol):
    async def context(self, user_id: str, hunt_id: str, session_id: str) -> HuntContext: ...

    async def publish(
        self, user_id: str, hunt_id: str, session_id: str, changes: ErrorPair
    ) -> None: ...

    async def assess(
        self, user_id: str, hunt_id: str, session_id: str, feedback: HuntAssessment
    ) -> None: ...


class _MissingLessonHunt:
    async def context(self, user_id: str, hunt_id: str, session_id: str) -> HuntContext:
        raise RuntimeError("La lecture critique n’est pas branchée.")

    async def publish(
        self, user_id: str, hunt_id: str, session_id: str, changes: ErrorPair
    ) -> None:
        raise RuntimeError("La lecture critique n’est pas branchée.")

    async def assess(
        self, user_id: str, hunt_id: str, session_id: str, feedback: HuntAssessment
    ) -> None:
        raise RuntimeError("La lecture critique n’est pas branchée.")


NO_HUNT: LessonHuntStore = _MissingLessonHunt()
