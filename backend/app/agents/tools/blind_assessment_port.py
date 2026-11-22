"""L’évaluateur reçoit les textes A et B, sans métadonnées de provenance."""

from dataclasses import dataclass
from typing import Annotated, Protocol

from pydantic import BaseModel, Field, StringConstraints

BLIND_GRAPH = "blind_assessment"
Score = Annotated[int, Field(strict=True, ge=0, le=4)]


class BlindCriterion(BaseModel):
    label: str
    instructions: str


class BlindGrade(BaseModel):
    scores_a: list[Score] = Field(min_length=3, max_length=3)
    scores_b: list[Score] = Field(min_length=3, max_length=3)
    feedback: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=4, max_length=1800)
    ]


@dataclass(frozen=True)
class BlindContext:
    text_a: str
    text_b: str
    criteria: list[BlindCriterion]
    complete: bool


class BlindAssessmentStore(Protocol):
    async def context(self, user_id: str, assessment_id: str, session_id: str) -> BlindContext: ...

    async def finish(
        self, user_id: str, assessment_id: str, session_id: str, grade: BlindGrade
    ) -> None: ...


class _MissingBlind:
    async def context(self, user_id: str, assessment_id: str, session_id: str) -> BlindContext:
        raise RuntimeError("Le port de l’épreuve en aveugle n’est pas branché.")

    async def finish(
        self, user_id: str, assessment_id: str, session_id: str, grade: BlindGrade
    ) -> None:
        raise RuntimeError("Le port de l’épreuve en aveugle n’est pas branché.")


NO_BLIND: BlindAssessmentStore = _MissingBlind()
