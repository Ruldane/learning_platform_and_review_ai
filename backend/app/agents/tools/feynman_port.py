from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

FEYNMAN_LESSON = "feynman_lesson"
FEYNMAN_IDE = "feynman_ide"
FEYNMAN_SCOPES = frozenset({FEYNMAN_LESSON, FEYNMAN_IDE})

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=600)]


class FeynmanCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    front: ShortText
    back: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]


class FeynmanAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    mastered: bool
    follow_up: ShortText | None = None
    cards: list[FeynmanCard] = Field(default_factory=list, max_length=3)


@dataclass(frozen=True)
class FeynmanContext:
    title: str
    material: str
    strong: bool
    used_tokens: int


class FeynmanExchange(BaseModel):
    explanation: str
    follow_up: str | None = None
    clarification: str | None = None
