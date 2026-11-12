"""Niveaux des compétences reflétés dans les acquis de la mémoire (D6, D88) : pour chaque
compétence, l'acquis du même nom (nom normalisé) est créé ou monté, jamais baissé, et
l'écriture est journalisée (`memory_writes` : auteur, session, raison). Idempotent : refléter
deux fois le même niveau n'écrit rien de plus (c'est ce qui permet de rattraper un reflet manqué).

Lecture inverse : `acquis_levels` rend le niveau de chaque acquis de la mémoire (ceux que
l'Archiviste a écrits n'ont pas de ligne `user_skills`)."""

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
    raw = (item.meta or {}).get("level", "declare")
    return cast(MasteryLevel, raw) if raw in MASTERY_ORDER else "declare"


async def _acquis(db: AsyncSession, user_id: str) -> list[MemoryItem]:
    """Tous les acquis actifs, du plus ancien au plus récent : lus une fois par appel."""
    return await MemoryItemRepository(db, user_id).of_kind("acquis")


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
    """Un acquis se crée au plus « en cours » (règles d'écriture, D65) ; `_raise` pose ensuite
    un niveau plus haut. Texte déterminé par le titre : deux créations simultanées du même nom
    tombent sur le même hash (une seule ligne)."""
    draft = WriteDraft(
        kind="acquis",
        title=title,
        text=f"Compétence travaillée dans un programme d'apprentissage : {title}.",
        author=author,
        reason=reason,
        level=level if level in WRITABLE_LEVELS else "en_cours",
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
) -> list[str]:
    """Reflète chaque `(titre, niveau)` dans l'acquis du même nom normalisé (créé, ou monté,
    jamais plus bas) ; rend les ids des acquis. Les acquis sont lus une seule fois. Session de
    base propre, commitée (la vectorisation d'un acquis créé valide sa transaction avant)."""
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
                db, user_id, item, level, author=author, session_id=session_id, reason=reason
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
) -> str:
    """Crée l'acquis `title` au niveau `level` (ou le monte, jamais plus bas) ; rend son id."""
    [item_id] = await reflect_skill_levels(
        runtime, user_id, [(title, level)], author=author, session_id=session_id, reason=reason
    )
    return item_id
