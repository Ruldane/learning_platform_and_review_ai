"""Schémas de l'API de la mémoire (14.2) : éléments, journal, recherche."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.db.models.memory import ItemStatus, MasteryLevel, MemoryKind, WriteAction

# `ItemStatus` et `MemoryKind` sont réexportés : un router n'importe pas `app.db` (contrat 1b).
__all__ = [
    "AgentLevel",
    "ChunkOut",
    "ItemStatus",
    "MemoryItemCreate",
    "MemoryItemDetail",
    "MemoryItemList",
    "MemoryItemOut",
    "MemoryItemPatch",
    "MemoryKind",
    "MemoryWriteOut",
    "NeighborOut",
    "SearchHitOut",
    "SearchRequest",
    "SearchResponse",
    "UserWritableKind",
]

# Types qu'un utilisateur crée à la main ; les `lecon` et `source` viennent des agents, les
# `document` de l'import (`/documents`).
UserWritableKind = Literal["acquis", "decision", "offre"]
# Niveaux qu'on peut donner à la main ou par un agent : `valide` et `prouve` se gagnent (phase 4).
AgentLevel = Literal["declare", "en_cours"]
Tag = Annotated[str, Field(min_length=1, max_length=40)]


class MemoryItemOut(BaseModel):
    id: str
    kind: MemoryKind
    title: str
    text: str
    tags: list[str]
    created_by: str
    session_id: str | None
    source_id: str | None
    lang: str | None
    status: ItemStatus
    level: MasteryLevel | None
    evidence: list[str]
    reason: str | None
    indexed: bool
    created_at: datetime
    updated_at: datetime


class MemoryItemList(BaseModel):
    items: list[MemoryItemOut]
    total: int


class ChunkOut(BaseModel):
    id: str
    ordinal: int
    text: str
    token_count: int


class NeighborOut(BaseModel):
    item_id: str
    title: str
    kind: MemoryKind
    score: float


class MemoryWriteOut(BaseModel):
    id: str
    item_id: str
    item_title: str
    action: WriteAction
    author: str
    session_id: str | None
    reason: str | None
    created_at: datetime


class MemoryItemDetail(MemoryItemOut):
    chunks: list[ChunkOut]
    neighbors: list[NeighborOut]
    writes: list[MemoryWriteOut]


class MemoryItemCreate(BaseModel):
    kind: UserWritableKind
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=20_000)
    tags: list[Tag] = Field(default_factory=list, max_length=10)
    level: AgentLevel | None = None


class MemoryItemPatch(BaseModel):
    """Tout est facultatif ; un champ absent ou `null` ne change rien. `status` n'accepte que
    `active` : confirmer une décision en attente (la refuser, c'est la supprimer)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    text: str | None = Field(default=None, min_length=1, max_length=20_000)
    tags: list[Tag] | None = Field(default=None, max_length=10)
    level: AgentLevel | None = None
    status: Literal["active"] | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    kinds: list[MemoryKind] | None = None
    k: int = Field(default=8, ge=1, le=50)


class SearchHitOut(BaseModel):
    chunk_id: str
    item_id: str
    kind: MemoryKind
    title: str
    text: str
    score: float
    created_by: str


class SearchResponse(BaseModel):
    hits: list[SearchHitOut]
    agent_text: str
