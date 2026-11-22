"""Contrat entre le graphe d'évaluation et les tentatives Boss."""

from collections.abc import Awaitable
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.core.errors import AppError

BOSS_GRAPH = "boss_review"
BOSS_SUBJECT = "boss_program"
BOSS_AGENT = "boss_reviewer"


class BossCheck(BaseModel):
    label: str
    passed: bool


class BossDiagnostic(BaseModel):
    outcome: Literal["completed", "failed", "timeout"]
    checks: list[BossCheck]

    @property
    def passed(self) -> bool:
        return (
            self.outcome == "completed"
            and bool(self.checks)
            and all(check.passed for check in self.checks)
        )


class BossCriterion(BaseModel):
    score: int = Field(ge=0, le=5)
    feedback: str = Field(min_length=1, max_length=1_200)


class BossRubric(BaseModel):
    readability: BossCriterion
    maintenance: BossCriterion


class BossGrade(BaseModel):
    functionality: int = Field(ge=0, le=10)
    total: int = Field(ge=0, le=20)
    rubric: BossRubric
    diagnostic: BossDiagnostic


class BossSubmission(BaseModel):
    brief: str
    change: str
    code_sample: dict[str, str]
    diagnostic: BossDiagnostic
    previous: BossGrade | None


class BossReviewPort(Protocol):
    def diagnose(
        self, user_id: str, program_id: str, session_id: str
    ) -> Awaitable[BossSubmission]: ...

    def grade(
        self, user_id: str, program_id: str, session_id: str, rubric: BossRubric
    ) -> Awaitable[BossGrade]: ...


class _Unavailable:
    async def diagnose(self, user_id: str, program_id: str, session_id: str) -> BossSubmission:
        raise AppError("boss_unavailable", "L’évaluation du Boss est indisponible.", 503)

    async def grade(
        self, user_id: str, program_id: str, session_id: str, rubric: BossRubric
    ) -> BossGrade:
        raise AppError("boss_unavailable", "L’évaluation du Boss est indisponible.", 503)


NO_BOSS: BossReviewPort = _Unavailable()
