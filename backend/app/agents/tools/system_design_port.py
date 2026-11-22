from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)]


class SystemDesignSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    board_id: UUID
    defense: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class DesignCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: Annotated[int, Field(strict=True, ge=1, le=5)]
    feedback: Text


class DesignCriteria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    architecture: DesignCriterion
    reliability: DesignCriterion
    scale: DesignCriterion
    tradeoffs: DesignCriterion


class SystemDesignReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criteria: DesignCriteria
    summary: Text

    @property
    def earns_proof(self) -> bool:
        scores = (
            self.criteria.architecture.score,
            self.criteria.reliability.score,
            self.criteria.scale.score,
            self.criteria.tradeoffs.score,
        )
        return min(scores) >= 3 and sum(scores) >= 14


@dataclass(frozen=True)
class SystemDesignContext:
    title: str
    situation: str
    requirements: tuple[str, ...]
    diagram: str
    defense: str
