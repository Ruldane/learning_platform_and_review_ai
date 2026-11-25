"""Common study types (phase 5): the agent ports and the features share them here, because the
engine imports no feature (contract 6)."""

import hashlib
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose

ReplanTrigger = Literal["weekly_review", "message", "gap", "reading"]
ReplanOption = Literal["reduce_scope", "push_deadline", "advance", "deepen"]
ReviewState = Literal["late_twice", "late", "ahead", "on_track"]


class ReplanReading(BaseModel):
    """Snapshot of the selected reading, provided by its route."""

    title: str = Field(min_length=1, max_length=240)
    url: str = Field(min_length=1, max_length=2000)


class CardDraft(BaseModel):
    """A card proposed by an agent. The back is read by January: too long, it is
    shortened (`Prose`); the front serves as key (`card_hash`), it stays refused if it exceeds."""

    front: str = Field(min_length=5, max_length=300)
    back: Prose = Field(min_length=1, max_length=600)
    skill: str | None = Field(default=None, max_length=120)


def card_hash(front: str) -> str:
    """The fingerprint (sha256) of the front without case or extra spaces: two cards with the
    same front make only one per user."""
    return hashlib.sha256(" ".join(front.casefold().split()).encode()).hexdigest()
