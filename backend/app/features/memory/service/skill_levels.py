"""Skill levels reflected in the memory's learned items (D6, D88): for each skill, the learned
item of the same name (normalized name) is created or raised, never lowered, and the write is
logged (`memory_writes`: author, session, reason). Idempotent: reflecting the same level twice
writes nothing more (this is what allows catching up a missed reflection).

Reverse read: `acquis_levels` returns the level of each learned item in memory (those the
Archivist wrote have no `user_skills` row)."""

from collections.abc import Sequence
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import normalize_skill_name
from app.db.models.memory import MASTERY_ORDER, MasteryLevel, MemoryItem
from app.features.memory.repository import MemoryItemRepository, WriteRepository
from app.features.memory.service.items import MemoryService
from app.features.memory.service.rules import WRITABLE_LEVELS, WriteDraft
from app.features.memory.service.runtime import MemoryRuntime


def _level(item: MemoryItem) -> MasteryLevel:
    raw = (item.meta or {}).get("level", "declared")
    return cast(MasteryLevel, raw) if raw in MASTERY_ORDER else "declared"


async def _acquis(db: AsyncSession, user_id: str) -> list[MemoryItem]:
    """All active learned items, oldest to most recent: read once per call."""
    return await MemoryItemRepository(db, user_id).of_kind("skill")


async def acquis_levels(db: AsyncSession, user_id: str) -> dict[str, MasteryLevel]:
    """`normalized name → level` of the active learned items (the highest if duplicated)."""
    levels: dict[str, MasteryLevel] = {}
    for item in await _acquis(db, user_id):
        norm, level = normalize_skill_name(item.title), _level(item)
        if norm and (norm not in levels or MASTERY_ORDER[level] > MASTERY_ORDER[levels[norm]]):
            levels[norm] = level
    return levels


async def _raise(
    db: AsyncSession,
    user_id: str,
    item: MemoryItem,
    level: MasteryLevel,
    *,
    author: str,
    session_id: str | None,
    reason: str,
    allow_lower: bool = False,
) -> None:
    """Raises the learned item's level if it is lower (or sets it, lower included, with
    `allow_lower`), logs `update`; otherwise nothing."""
    current = MASTERY_ORDER[_level(item)]
    if current == MASTERY_ORDER[level] or (current > MASTERY_ORDER[level] and not allow_lower):
        return
    item.meta = {**(item.meta or {}), "level": level}
    await db.flush()
    await WriteRepository(db, user_id).log(
        item=item, action="update", author=author, session_id=session_id, reason=reason
    )


async def _create(
    db: AsyncSession,
    runtime: MemoryRuntime,
    user_id: str,
    title: str,
    level: MasteryLevel,
    *,
    author: str,
    session_id: str | None,
    reason: str,
) -> MemoryItem:
    """A learned item is created at most "in progress" (write rules, D65); `_raise` then sets a
    higher level. Text determined by the title: two simultaneous creations of the same name
    land on the same hash (a single row)."""
    draft = WriteDraft(
        kind="skill",
        title=title,
        text=f"Skill worked on in a learning program: {title}.",
        author=author,
        reason=reason,
        level=level if level in WRITABLE_LEVELS else "in_progress",
        session_id=session_id,
    )
    return (await MemoryService(db, user_id, runtime).write(draft)).item


async def reflect_skill_levels(
    runtime: MemoryRuntime,
    user_id: str,
    levels: Sequence[tuple[str, MasteryLevel]],
    *,
    author: str,
    session_id: str | None,
    reason: str,
    allow_lower: bool = False,
) -> list[str]:
    """Reflects each `(title, level)` in the learned item of the same normalized name (created,
    or raised, never lower); returns the learned items' ids. The items are read once. Own
    database session, committed (vectorizing a created item commits its transaction first).
    `allow_lower`: the only decrease allowed (D6, D101), two card failures in a row (SPEC F9)."""
    ids: list[str] = []
    async with runtime.session_factory() as db:
        index: dict[str, MemoryItem] = {}
        for row in await _acquis(db, user_id):
            index.setdefault(normalize_skill_name(row.title), row)
        for title, level in levels:
            norm = normalize_skill_name(title)
            if not norm:
                continue
            item = index.get(norm)
            if item is None:
                item = await _create(
                    db,
                    runtime,
                    user_id,
                    title,
                    level,
                    author=author,
                    session_id=session_id,
                    reason=reason,
                )
                index[norm] = item
            await _raise(
                db,
                user_id,
                item,
                level,
                author=author,
                session_id=session_id,
                reason=reason,
                allow_lower=allow_lower,
            )
            ids.append(item.id)
        await db.commit()
    return ids


async def reflect_skill_level(
    runtime: MemoryRuntime,
    user_id: str,
    *,
    title: str,
    level: MasteryLevel,
    author: str,
    session_id: str | None,
    reason: str,
    allow_lower: bool = False,
) -> str:
    """Creates the learned item `title` at level `level` (or raises it; lower only with
    `allow_lower`); returns its id."""
    [item_id] = await reflect_skill_levels(
        runtime,
        user_id,
        [(title, level)],
        author=author,
        session_id=session_id,
        reason=reason,
        allow_lower=allow_lower,
    )
    return item_id
