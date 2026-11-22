from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field

from app.agents.tools.podcast_port import PodcastLine
from app.db.models.podcast import EpisodeStatus


class PodcastQuestionOut(BaseModel):
    question: str
    choices: list[str]


class PodcastEpisodeOut(BaseModel):
    id: str
    day: date
    lesson_id: str
    title: str
    status: EpisodeStatus
    lines: list[PodcastLine]
    questions: list[PodcastQuestionOut]
    duration_seconds: int | None


class PodcastStarted(BaseModel):
    session_id: str


class PodcastAnswers(BaseModel):
    choices: list[Annotated[int, Field(ge=0, le=2)]] = Field(min_length=3, max_length=3)


class PodcastCorrection(BaseModel):
    answer: int
    correct: bool
    explanation: str


class PodcastQuizOut(BaseModel):
    score: int
    corrections: list[PodcastCorrection]
