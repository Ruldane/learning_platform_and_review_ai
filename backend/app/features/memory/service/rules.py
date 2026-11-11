"""Règles d'écriture de la mémoire (D65) : ce qu'un agent ou l'utilisateur peut écrire, à quel
niveau, avec quelle raison, et dans quel statut l'élément naît. Fonctions pures."""

from dataclasses import dataclass
from typing import Any

from app.core.errors import AppError
from app.db.models.memory import USER_AUTHOR, ItemStatus, MasteryLevel, MemoryKind
from app.features.memory.repository.writes import REASON_MAX

# Niveaux qu'on peut écrire : `valide` et `prouve` se gagnent (SPEC 4.2, phase 4).
WRITABLE_LEVELS: tuple[MasteryLevel, ...] = ("declare", "en_cours")
TAG_MAX_LENGTH = 40
TAGS_MAX = 10


@dataclass(frozen=True)
class WriteDraft:
    """Une écriture demandée, avant les règles. `author` est `user` ou le slug d'un agent."""

    kind: MemoryKind
    title: str
    text: str
    author: str
    reason: str | None
    tags: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    level: MasteryLevel | None = None
    session_id: str | None = None
    source_id: str | None = None
    lang: str | None = None


def clean_tags(tags: list[str] | tuple[str, ...]) -> list[str]:
    """Étiquettes nettoyées : espaces retirés, vides et doublons écartés, bornées."""
    seen: dict[str, None] = {}
    for tag in tags:
        cleaned = tag.strip()[:TAG_MAX_LENGTH]
        if cleaned:
            seen.setdefault(cleaned)
    return list(seen)[:TAGS_MAX]


def _level(draft: WriteDraft, is_agent: bool) -> MasteryLevel | None:
    if draft.kind != "acquis":
        if draft.level is not None:
            raise AppError("memory_level_forbidden", "Seul un acquis a un niveau.", 422)
        return None
    level = draft.level or "declare"
    if level not in WRITABLE_LEVELS:
        message = (
            "Un agent n'écrit un acquis qu'au niveau déclaré ou en cours."
            if is_agent
            else "Un acquis ne se crée qu'au niveau déclaré ou en cours."
        )
        raise AppError("memory_level_forbidden", message, 422)
    return level


def resolve_write(draft: WriteDraft) -> tuple[ItemStatus, dict[str, Any]]:
    """Statut du nouvel élément et sa `meta` (`level`, `evidence`, `reason`, clés absentes si sans
    objet). Un agent ne peut ni écrire un document ni écrire sans raison ; sa décision attend la
    confirmation de l'utilisateur (`pending`) ; ses acquis restent déclarés ou en cours."""
    is_agent = draft.author != USER_AUTHOR
    reason = (draft.reason or "").strip()
    if is_agent and draft.kind == "document":
        raise AppError("memory_kind_forbidden", "Un agent ne peut pas écrire de document.", 422)
    if is_agent and not reason:
        raise AppError(
            "memory_reason_required", "Chaque écriture d'agent doit donner sa raison.", 422
        )
    level = _level(draft, is_agent)
    meta: dict[str, Any] = {}
    if level is not None:
        meta["level"] = level
    if draft.evidence:
        meta["evidence"] = list(draft.evidence)
    if reason:
        meta["reason"] = reason[:REASON_MAX]
    status: ItemStatus = "pending" if is_agent and draft.kind == "decision" else "active"
    return status, meta
