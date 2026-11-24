"""Memory write rules (D65): what an agent or the user may write, at which level, with which
reason, and in which status the item is born. Pure functions."""

from dataclasses import dataclass
from typing import Any

from app.core.errors import AppError
from app.db.models.memory import USER_AUTHOR, ItemStatus, MasteryLevel, MemoryKind
from app.features.memory.repository.writes import REASON_MAX

# Levels that can be written: `valide` and `prouve` are earned (SPEC 4.2, phase 4).
WRITABLE_LEVELS: tuple[MasteryLevel, ...] = ("declared", "in_progress")
TAG_MAX_LENGTH = 40
TAGS_MAX = 10


@dataclass(frozen=True)
class WriteDraft:
    """A requested write, before the rules. `author` is `user` or an agent's slug."""

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
    # January's quick capture (D108): the Archivist files her page or note as a `document`.
    captured: bool = False
    sync_metadata: dict[str, Any] | None = None


def clean_tags(tags: list[str] | tuple[str, ...]) -> list[str]:
    """Cleaned tags: spaces stripped, empties and duplicates dropped, bounded."""
    seen: dict[str, None] = {}
    for tag in tags:
        cleaned = tag.strip()[:TAG_MAX_LENGTH]
        if cleaned:
            seen.setdefault(cleaned)
    return list(seen)[:TAGS_MAX]


def _level(draft: WriteDraft, is_agent: bool) -> MasteryLevel | None:
    if draft.kind != "acquis":
        if draft.level is not None:
            raise AppError("memory_level_forbidden", "Only a skill has a level.", 422)
        return None
    level = draft.level or "declared"
    if level not in WRITABLE_LEVELS:
        message = (
            "An agent only writes a skill at the declared or in-progress level."
            if is_agent
            else "A skill can only be created at the declared or in-progress level."
        )
        raise AppError("memory_level_forbidden", message, 422)
    return level


def resolve_write(draft: WriteDraft) -> tuple[ItemStatus, dict[str, Any]]:
    """Status of the new item and its `meta` (`level`, `evidence`, `reason`, keys absent when not
    applicable). An agent can neither write a document nor write without a reason; its decision
    awaits the user's confirmation (`pending`); its skills stay declared or in progress. Sole
    exception for documents: January's quick capture (`captured`, D108), filed by the `capture`
    feature, never by an agent tool."""
    is_agent = draft.author != USER_AUTHOR
    reason = (draft.reason or "").strip()
    if is_agent and draft.kind == "document" and not draft.captured:
        raise AppError("memory_kind_forbidden", "An agent cannot write a document.", 422)
    if is_agent and not reason:
        raise AppError("memory_reason_required", "Every agent write must give its reason.", 422)
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
