"""Exchanges with the Verifier of a simulated recruitment step."""

from dataclasses import dataclass
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field, StringConstraints

RECRUITMENT_GRAPH = "recruitment_process"
RecruitmentKind = Literal["project", "exercise", "interview"]
RecruitmentMark = Annotated[int, Field(strict=True, ge=0, le=4)]


class RecruitmentCriterion(BaseModel):
    label: str
    instructions: str


class RecruitmentGrade(BaseModel):
    marks: list[RecruitmentMark] = Field(min_length=3, max_length=3)
    feedback: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=4, max_length=1800)
    ]


@dataclass(frozen=True)
class RecruitmentContext:
    offer: str
    requirements: list[str]
    kind: RecruitmentKind
    prompt: str
    answer: str
    criteria: list[RecruitmentCriterion]
    project: dict[str, object] | None
    graded: bool


class RecruitmentStore(Protocol):
    async def context(
        self, user_id: str, process_id: str, session_id: str
    ) -> RecruitmentContext: ...

    async def grade(
        self, user_id: str, process_id: str, session_id: str, grade: RecruitmentGrade
    ) -> None: ...


class _MissingRecruitment:
    async def context(self, user_id: str, process_id: str, session_id: str) -> RecruitmentContext:
        raise RuntimeError("The recruitment graph is not wired.")

    async def grade(
        self, user_id: str, process_id: str, session_id: str, grade: RecruitmentGrade
    ) -> None:
        raise RuntimeError("The recruitment graph is not wired.")


NO_RECRUITMENT: RecruitmentStore = _MissingRecruitment()
