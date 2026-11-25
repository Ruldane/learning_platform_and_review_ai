"""Merging of memory items (4.6, D67): `POST /memory/items/{id}/merge`.

The other items are merged into the target: text (target then the non-identical texts of the
others, separated by a blank line), tags and evidence combined in order of first appearance,
highest level for a skill. The others are deleted (`delete` log), the target is logged `merge`
then reindexed. Same pattern as writing (D66): everything is committed to the database before
calling Qdrant, and `index_item` is the last step."""

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError
from app.db.models.memory import MASTERY_ORDER, USER_AUTHOR, MasteryLevel, MemoryItem, MemoryKind
from app.features.memory.repository import MemoryItemRepository, WriteRepository
from app.features.memory.schemas import MemoryItemOut
from app.features.memory.service.items import MemoryService, duplicate, to_out
from app.features.memory.service.rules import clean_tags
from app.features.memory.service.text import content_hash

SEPARATOR = "\n\n"


def _check(target: MemoryItem, others: Sequence[MemoryItem]) -> None:
    everyone = [target, *others]
    if any(item.kind == "document" for item in everyone):
        raise AppError(
            "merge_document_forbidden", "A document cannot be merged: delete the duplicate.", 409
        )
    if any(item.kind != target.kind for item in others):
        raise AppError("merge_kind_mismatch", "Only items of the same kind can be merged.", 422)
    if any(item.status != "active" for item in everyone):
        raise AppError(
            "merge_pending_forbidden",
            "Confirm or reject the pending decision before merging it.",
            409,
        )


def _merged(
    target: MemoryItem, others: Sequence[MemoryItem]
) -> tuple[str, list[str], dict[str, Any]]:
    """Text, tags and `meta` of the target after merging."""
    everyone = [target, *others]
    texts: dict[str, str] = {}  # normalised text (case, spaces) -> original text
    for item in everyone:
        texts.setdefault(" ".join(item.text.casefold().split()), item.text)
    tags = clean_tags([str(tag) for item in everyone for tag in item.tags])
    evidence = list(
        dict.fromkeys(str(e) for item in everyone for e in (item.meta or {}).get("evidence", []))
    )
    meta = dict(target.meta or {})
    if evidence:
        meta["evidence"] = evidence
    if target.kind == "skill":
        levels = [
            cast(MasteryLevel, (item.meta or {}).get("level") or "declared") for item in everyone
        ]
        meta["level"] = max(levels, key=MASTERY_ORDER.__getitem__)
    return SEPARATOR.join(texts.values()), tags, meta


async def merge(service: MemoryService, target_id: str, other_ids: Sequence[str]) -> MemoryItemOut:
    """Merges `other_ids` into `target_id` (same user: 404 otherwise). Readable refusals: nothing
    to merge (422), document (409), different kinds (422), pending decision (409), merged
    content identical to another item (409)."""
    ids = list(dict.fromkeys(i for i in other_ids if i != target_id))
    if not ids:
        raise AppError("merge_nothing", "Choose at least one other item to merge.", 422)
    target = await service.get(target_id)
    others = [await service.get(item_id) for item_id in ids]
    _check(target, others)
    text, tags, meta = _merged(target, others)
    db, user_id = service.db, service.user_id
    items, writes = MemoryItemRepository(db, user_id), WriteRepository(db, user_id)
    await items.begin_write()  # before the SAVEPOINT (D65 c)
    for other in others:
        reason = f'Merged into "{target.title}".'
        await writes.log(
            item=other, action="delete", author=USER_AUTHOR, session_id=None, reason=reason
        )
        await items.delete(other.id)
    digest = content_hash(cast(MemoryKind, target.kind), target.title, text)
    clash = await items.find_by_hash(digest)
    if clash is not None and clash.id != target.id:
        raise duplicate()
    try:
        async with db.begin_nested():
            target.text, target.tags, target.content_hash, target.meta = text, tags, digest, meta
            await db.flush()
    except IntegrityError:
        raise duplicate() from None
    reason = f"Merge of {len(others)} item(s)."
    await writes.log(
        item=target, action="merge", author=USER_AUTHOR, session_id=None, reason=reason
    )
    # Unindexed in the same transaction as the merged text: a stop before `index_item`
    # finishes never leaves it marked indexed with its old chunks.
    await items.set_indexed_at(target, None)
    await db.commit()  # nothing is held during the following Qdrant calls
    await service.runtime.indexer.unindex(user_id, ids)
    await service.runtime.indexer.index_item(db, target)  # last step (D66)
    return to_out(target)
