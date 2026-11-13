"""Charges typées des événements d'une session (SPEC 9.5) ; l'enveloppe, le catalogue et la
validation vivent dans `events.py`, qui les réexporte.

Tout champ ajouté a une valeur par défaut : les événements déjà stockés restent valides.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentStartedPayload(BaseModel):
    step: str
    intent: str  # phrase d'intention affichée : jamais un raisonnement brut (9.5)


class AgentTokenPayload(BaseModel):
    message_id: str
    text: str


class Citation(BaseModel):
    index: int
    title: str
    url: str | None = None
    memory_item_id: str | None = None


class AgentMessagePayload(BaseModel):
    message_id: str
    text: str
    citations: list[Citation] = Field(default_factory=list)


class ToolCalledPayload(BaseModel):
    call_id: str
    tool: str
    args: dict[str, Any]


class ToolResultPayload(BaseModel):
    call_id: str
    tool: str
    ok: bool
    summary: str


class SourceFoundPayload(BaseModel):
    title: str
    url: str
    author: str | None
    date: str | None
    lang: str | None
    score: int | None
    # Compléments de la recherche web (D77) : valeurs par défaut, donc compatibles avec les
    # événements déjà stockés.
    source_id: str | None = None  # absent : page sans ligne `sources` (domaine exclu)
    status: Literal["ok", "unreadable"] = "ok"
    verdict: Literal["kept", "rejected"] | None = None  # absent : source non notée
    reason: str | None = None  # raison du verdict, ou de l'illisibilité
    # Praticiens repérés par l'Éclaireur (phase 4, D82) : `person`, avec son rôle public.
    kind: Literal["page", "person"] = "page"
    role: str | None = None


BoardKind = Literal["domain_map", "prerequisites", "timeline", "comparison"]


class BoardUpdatePayload(BaseModel):
    """Un état du tableau. `board_id`, `kind`, `title` (D82) : plusieurs tableaux par session
    (carte du domaine, prérequis, frise, comparaison) ; absents des événements d'avant."""

    mermaid: str
    step: int
    board_id: str | None = None
    kind: BoardKind | None = None
    title: str | None = None


class MemoryWrittenPayload(BaseModel):
    item_id: str
    kind: str
    title: str
    reason: str
    status: Literal["active", "pending"] = "active"  # `pending` : décision « À confirmer » (D68)


class InterruptOption(BaseModel):
    value: str
    label: str


class InterruptField(BaseModel):
    """Une question d'un cadrage à plusieurs champs (D82) ; la reprise porte
    `{"answers": {id: texte}}` (ou la valeur d'une option, `"go"`, D84)."""

    id: str = Field(pattern=r"^[a-z0-9_]{1,32}$")
    label: str
    required: bool = False
    max_length: int = Field(default=2000, ge=1, le=20000)  # texte d'une page collée (F6)


class InterruptRequestedPayload(BaseModel):
    """`kind` et non `type` : `type` est déjà le discriminant de l'enveloppe (DECISIONS)."""

    interrupt_id: str
    kind: str
    question: str
    options: list[InterruptOption] = Field(default_factory=list)
    fields: list[InterruptField] = Field(default_factory=list)


class ProposalReadyPayload(BaseModel):
    proposal_id: str
    title: str


class ArtifactReadyPayload(BaseModel):
    artifact_id: str
    kind: str
    title: str
    url: str | None = None


class CostUpdatedPayload(BaseModel):
    tokens_in: int
    tokens_out: int
    cost_usd: float
    cap_tokens: int


class RunCompletedPayload(BaseModel):
    summary: str = ""


class RunFailedPayload(BaseModel):
    code: str
    message: str


# Commandes permanentes du débat (SPEC 3.2) portées par `user.message` (D82).
UserCommand = Literal["another_round", "to_proposals", "more_concrete", "shorter"]


class UserMessagePayload(BaseModel):
    """Message de l'utilisatrice (D4) ; `command` : commande du débat, texte alors facultatif."""

    text: str = ""
    command: UserCommand | None = None
