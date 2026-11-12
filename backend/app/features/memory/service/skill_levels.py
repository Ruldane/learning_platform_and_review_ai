"""Niveaux des compétences reflétés dans les acquis de la mémoire (D6) : quand un niveau change
dans `user_skills`, l'acquis du même nom (nom normalisé) est créé ou monté, jamais baissé, et
l'écriture est journalisée (`memory_writes` : auteur, session, raison).

Lecture inverse : `acquis_levels` rend le niveau de chaque acquis de la mémoire (ceux que
l'Archiviste a écrits n'ont pas de ligne `user_skills`)."""

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import normalize_skill_name
from app.db.models.memory import MASTERY_ORDER, MasteryLevel, MemoryItem
from app.features.memory.repository import ItemFilter, MemoryItemRepository, WriteRepository
from app.features.memory.service.items import MemoryService
from app.features.memory.service.rules import WRITABLE_LEVELS, WriteDraft
from app.features.memory.service.runtime import MemoryRuntime

ACQUIS_READ_MAX = 2000  # acquis relus pour trouver un nom (les plus récents)


def _level(item: MemoryItem) -> MasteryLevel:
    raw = (item.meta or {}).get("level", "declare")
    return cast(MasteryLevel, raw) if raw in MASTERY_ORDER else "declare"


async def _acquis(db: AsyncSession, user_id: str) -> list[MemoryItem]:
    rows, _ = await MemoryItemRepository(db, user_id).filtered(
        ItemFilter(kind="acquis"), limit=ACQUIS_READ_MAX, offset=0
    )
    return rows


async def acquis_levels(db: AsyncSession, user_id: str) -> dict[str, MasteryLevel]:
    """`nom normalisé → niveau` des acquis actifs de la mémoire (le plus haut s'il y a doublon)."""
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
) -> None:
    """Monte le niveau de l'acquis s'il est plus bas, journalise `update` ; sinon rien."""
    if MASTERY_ORDER[_level(item)] >= MASTERY_ORDER[level]:
        return
    item.meta = {**(item.meta or {}), "level": level}
    await db.flush()
    await WriteRepository(db, user_id).log(
        item=item, action="update", author=author, session_id=session_id, reason=reason
    )


async def reflect_skill_level(
    runtime: MemoryRuntime,
    user_id: str,
    *,
    title: str,
    level: MasteryLevel,
    author: str,
    session_id: str | None,
    reason: str,
) -> str:
    """Crée l'acquis `title` au niveau `level` (ou le monte, jamais plus bas) ; rend son id.

    Un acquis se crée au plus « en cours » (règles d'écriture, D65) : un niveau plus haut est
    posé ensuite par une mise à jour journalisée. Session de base propre, commitée."""
    norm = normalize_skill_name(title)
    async with runtime.session_factory() as db:
        acquis = await _acquis(db, user_id)
        found = next((i for i in acquis if normalize_skill_name(i.title) == norm), None)
        if found is None:
            first = level if level in WRITABLE_LEVELS else "en_cours"
            draft = WriteDraft(
                kind="acquis",
                title=title,
                text=f"Compétence travaillée dans un programme d'apprentissage : {title}.",
                author=author,
                reason=reason,
                level=first,
                session_id=session_id,
            )
            found = (await MemoryService(db, user_id, runtime).write(draft)).item
        await _raise(db, user_id, found, level, author=author, session_id=session_id, reason=reason)
        item_id = found.id
        await db.commit()
    return item_id
