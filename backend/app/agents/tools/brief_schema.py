"""Schemas of the daily brief (P11): the Scout's pick (one resource among eight results) and the
two advice sentences (Moderator). Nothing here invents data: the resource comes from a real result
the code read, the advice numbers are checked by code (`numbers_in_advice`) against the day's facts
before being stored."""

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator

from app.agents.runtime.prose import Prose
from app.agents.tools.cv_lexicon import figures_in

RESULTS = 8  # results of the month's search shown to the Scout
READS = 3  # page reads at most for the resource (pick, then next results)
SENTENCES = 2  # advice sentences
SENTENCE_MIN = 10
SENTENCE_MAX = 240


class ResourcePick(BaseModel):
    """The Scout's pick: the rank (1 to 8) of the result, `None` if none fits, and one sentence
    saying why."""

    index: int | None = Field(ge=1, le=RESULTS)
    why: Prose = Field(max_length=200)


class CouncilAdvice(BaseModel):
    """The day's advice: exactly two sentences of 10 to 240 characters."""

    sentences: list[str] = Field(min_length=SENTENCES, max_length=SENTENCES)

    @field_validator("sentences")
    @classmethod
    def _sentence_lengths(cls, sentences: list[str]) -> list[str]:
        cleaned = [" ".join(sentence.split()) for sentence in sentences]
        if any(not SENTENCE_MIN <= len(sentence) <= SENTENCE_MAX for sentence in cleaned):
            raise ValueError(f"each sentence has {SENTENCE_MIN} to {SENTENCE_MAX} characters")
        return cleaned


@dataclass(frozen=True)
class ResourceView:
    """The day's resource, as the port stores it: a real result whose page was read.
    `published`: its date if the web gives it, never guessed."""

    title: str
    url: str
    domain: str
    published: str | None
    why: str


def numbers_in_advice(sentences: Sequence[str]) -> set[str]:
    """The advice numbers, in canonical form (`cv_lexicon`): digits as well as spelled-out ones
    ("three hours" is the number 3, not a way of quoting one without saying it). The code checks
    them against the day's facts."""
    found: set[str] = set()
    for sentence in sentences:
        found |= figures_in(sentence)
    return found
