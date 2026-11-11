"""Schémas de l'API de la mémoire (14.2) : éléments, journal, recherche, documents."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.db.models.memory import (
    DocumentSourceKind,
    DocumentStatus,
    ItemStatus,
    MasteryLevel,
    MemoryKind,
    WriteAction,
)

# Les types littéraux sont réexportés : un router n'importe pas `app.db` (contrat 1b).
__all__ = [
    "AgentLevel",
    "ChunkOut",
    "DocumentCreated",
    "DocumentError",
    "DocumentOut",
    "DocumentSourceKind",
    "DocumentStatus",
    "ItemStatus",
    "MapPoint",
    "MapResponse",
    "MemoryExport",
    "MemoryItemCreate",
    "MemoryItemDetail",
    "MemoryItemList",
    "MemoryItemOut",
    "MemoryItemPatch",
    "MemoryKind",
    "MemoryWriteOut",
    "MergeRequest",
    "PasteCreate",
    "NeighborOut",
    "ReindexState",
    "ReindexStatus",
    "SearchHitOut",
    "SearchRequest",
    "SearchResponse",
    "StatsOut",
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


class DocumentError(BaseModel):
    """Erreur d'import lisible ; `item_id` : l'élément déjà en mémoire d'un doublon."""

    code: str
    message: str
    item_id: str | None = None


class DocumentOut(BaseModel):
    id: str
    name: str
    source_kind: DocumentSourceKind
    status: DocumentStatus
    error: DocumentError | None
    url: str | None
    size_bytes: int | None
    item_id: str | None
    learned: bool
    created_at: datetime
    updated_at: datetime


class DocumentCreated(BaseModel):
    document: DocumentOut
    duplicate: bool


class PasteCreate(BaseModel):
    """Texte collé (`POST /documents/text`, corps JSON). La longueur du texte (500 000
    caractères au plus) est contrôlée par le service, qui répond `paste_too_long` ; le corps est
    borné à 21 Mo par le middleware."""

    text: str
    title: str | None = Field(default=None, max_length=200)


# --- explorateur : fusion, carte, statistiques, réindexation, export (D67) -------------------


class MergeRequest(BaseModel):
    """Éléments à fondre dans l'élément de l'URL (même type, 20 au plus)."""

    other_ids: list[str] = Field(min_length=1, max_length=20)


class MapPoint(BaseModel):
    item_id: str
    title: str
    kind: MemoryKind
    x: float
    y: float


class MapResponse(BaseModel):
    """Un point par élément actif indexé (moyenne de ses fragments), coordonnées sur [-1, 1] ;
    `truncated` : seuls les plus récents sont montrés."""

    points: list[MapPoint]
    method: Literal["pca"]
    truncated: bool


ReindexStatus = Literal["idle", "queued", "running", "done", "failed"]


class ReindexState(BaseModel):
    """État de la réindexation de l'utilisateur, tenu en mémoire (perdu au redémarrage)."""

    status: ReindexStatus
    done: int
    total: int
    error: str | None


class StatsOut(BaseModel):
    by_kind: dict[MemoryKind, int]
    total_items: int
    total_chunks: int
    pending_decisions: int
    unindexed_items: int
    last_write: MemoryWriteOut | None
    dimension: int
    vectorize_limit: int
    vectorize_share: float
    reindex: ReindexState
    dashboard_url: str


class MemoryExport(BaseModel):
    """Toute la mémoire de l'utilisateur en JSON, sans aucun vecteur."""

    version: Literal[1]
    exported_at: datetime
    items: list[MemoryItemOut]
    documents: list[DocumentOut]
    writes: list[MemoryWriteOut]
