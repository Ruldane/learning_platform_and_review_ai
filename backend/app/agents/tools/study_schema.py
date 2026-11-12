"""Types communs de l'étude (phase 5) : ports de l'agent et features les partagent ici, car le
moteur n'importe aucune feature (contrat 6)."""

import hashlib
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose

ReplanTrigger = Literal["weekly_review", "message"]
ReplanOption = Literal["reduce_scope", "push_deadline", "advance", "deepen"]
ReviewState = Literal["late_twice", "late", "ahead", "on_track"]


class CardDraft(BaseModel):
    """Une fiche proposée par un agent. Le verso est lu par January : trop long, il est
    raccourci (`Prose`) ; le recto sert de clé (`card_hash`), il reste refusé s'il dépasse."""

    front: str = Field(min_length=5, max_length=300)
    back: Prose = Field(min_length=1, max_length=600)
    skill: str | None = Field(default=None, max_length=120)


def card_hash(front: str) -> str:
    """L'empreinte (sha256) du recto sans la casse ni les espaces en trop : deux fiches au
    même recto ne font qu'une par utilisateur."""
    return hashlib.sha256(" ".join(front.casefold().split()).encode()).hexdigest()
