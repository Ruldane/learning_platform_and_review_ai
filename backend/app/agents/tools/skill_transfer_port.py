"""Bounded context for preparing and grading the transfer."""

from dataclasses import dataclass
from typing import Annotated, Protocol

from pydantic import BaseModel, Field, StringConstraints

TRANSFER_GRAPH = "skill_transfer"
Criterion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=4, max_length=600)]


class TransferExercise(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=4, max_length=150)]
    prompt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=30, max_length=2400)]
    criteria: list[Criterion] = Field(min_length=3, max_length=3)


class TransferAssessment(BaseModel):
    met: list[bool] = Field(min_length=3, max_length=3)
    feedback: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=4, max_length=2400)
    ]


@dataclass(frozen=True)
class TransferContext:
    stage: str
    skill: str
    proof_kind: str
    proof_label: str
    previous_prompts: tuple[str, ...]
    exercise: TransferExercise | None
    answer: str | None


class SkillTransferStore(Protocol):
    async def context(self, user_id: str, transfer_id: str, session_id: str) -> TransferContext: ...

    async def publish(
        self, user_id: str, transfer_id: str, session_id: str, exercise: TransferExercise
    ) -> None: ...

    async def assess(
        self, user_id: str, transfer_id: str, session_id: str, assessment: TransferAssessment
    ) -> None: ...


class _MissingTransfer:
    async def context(self, user_id: str, transfer_id: str, session_id: str) -> TransferContext:
        raise RuntimeError("The transfer check is not wired.")

    async def publish(
        self, user_id: str, transfer_id: str, session_id: str, exercise: TransferExercise
    ) -> None:
        raise RuntimeError("The transfer check is not wired.")

    async def assess(
        self, user_id: str, transfer_id: str, session_id: str, assessment: TransferAssessment
    ) -> None:
        raise RuntimeError("The transfer check is not wired.")


NO_TRANSFER: SkillTransferStore = _MissingTransfer()
