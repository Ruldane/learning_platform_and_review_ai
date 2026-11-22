"""Contrat entre le parcours du podcast et son stockage."""

from dataclasses import dataclass
from typing import Annotated, Protocol, Self

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.providers.speech.base import Speaker

TurnText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1800)]
ChoiceText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)]


class PodcastLine(BaseModel):
    speaker: Speaker
    text: TurnText


class PodcastQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    choices: list[ChoiceText] = Field(min_length=3, max_length=3)
    answer: int = Field(ge=0, le=2)
    explanation: str = Field(min_length=1, max_length=650)


class PodcastScript(BaseModel):
    lines: list[PodcastLine] = Field(min_length=2, max_length=16)
    questions: list[PodcastQuestion] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def alternating(self) -> Self:
        if self.lines[0].speaker != "host" or any(
            one.speaker == two.speaker for one, two in zip(self.lines, self.lines[1:], strict=False)
        ):
            raise ValueError("Les deux voix alternent. L’hôte commence.")
        return self


@dataclass(frozen=True)
class PodcastContext:
    lesson_title: str
    lesson_text: str
    reviews: tuple[str, ...]
    notes: tuple[str, ...]
    already_written: bool


class PodcastStore(Protocol):
    async def context(self, user_id: str, episode_id: str) -> PodcastContext: ...

    async def save_script(self, user_id: str, episode_id: str, script: PodcastScript) -> None: ...

    async def render_audio(self, user_id: str, episode_id: str) -> None: ...


class _MissingPodcastStore:
    async def context(self, user_id: str, episode_id: str) -> PodcastContext:
        raise RuntimeError("Le stockage du podcast n’est pas branché.")

    async def save_script(self, user_id: str, episode_id: str, script: PodcastScript) -> None:
        raise RuntimeError("Le stockage du podcast n’est pas branché.")

    async def render_audio(self, user_id: str, episode_id: str) -> None:
        raise RuntimeError("Le stockage du podcast n’est pas branché.")


NO_PODCAST: PodcastStore = _MissingPodcastStore()
