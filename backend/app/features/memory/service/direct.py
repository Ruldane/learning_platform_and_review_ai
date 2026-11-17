"""Éléments de mémoire écrits en direct par une feature qui n'a pas d'agent derrière elle (phase 10,
10.W) : la leçon ou l'offre que Claude (par le MCP) ou January écrit elle-même. Même écriture que
celle des agents (règles, dédoublonnage, journal, indexation), sans passerelle d'agent ni session.

Un appel du MCP de niveau 2 se retire en retrouvant chaque ligne dans l'état où l'appel l'a
laissée (`app.mcp.undo`) : l'indexation (`indexed_at`, posée par une requête en masse après le
premier enregistrement de la ligne) la ferait refuser. `settle` relit donc la ligne indexée et la
réécrit une fois, pour que l'état « après » de l'historique soit l'état final. Les vecteurs de
Qdrant d'un élément retiré par l'annulation restent, mais la recherche écarte tout vecteur sans
fragment ni élément en base."""

import logging
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models.memory import USER_AUTHOR, MemoryItem, MemoryKind
from app.features.memory.repository import MemoryItemRepository
from app.features.memory.schemas import MemoryItemPatch
from app.features.memory.service.items import MemoryService, _content
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.text import content_hash

logger = logging.getLogger(__name__)

__all__ = ["author_of", "write_direct"]

MCP_AUTHOR = "claude"


def author_of(is_mcp: bool) -> str:
    """`claude` quand l'appel vient du MCP, `user` sinon (l'interface)."""
    return MCP_AUTHOR if is_mcp else USER_AUTHOR


async def _settle(db: AsyncSession, item: MemoryItem) -> None:
    """Voir le module : réécrit la ligne indexée pour que l'historique la garde dans son état
    final."""
    await db.refresh(item)
    flag_modified(item, "indexed_at")
    await db.flush()
    await db.commit()


async def _replace(
    service: MemoryService,
    db: AsyncSession,
    user_id: str,
    kind: MemoryKind,
    old: tuple[str, str],
    new: tuple[str, str],
    tags: Sequence[str],
) -> MemoryItem | None:
    """L'élément qui portait `old` (titre, texte), mis à jour avec `new` ; `None` s'il n'y en a
    pas (ou si rien ne change)."""
    previous = await MemoryItemRepository(db, user_id).find_by_hash(
        content_hash(kind, *_content(*old))
    )
    if previous is None:
        return None
    patch = MemoryItemPatch.model_construct(title=new[0], text=new[1], tags=list(tags))
    await service.update(previous.id, patch)
    return previous


async def write_direct(
    runtime: MemoryRuntime,
    user_id: str,
    *,
    kind: MemoryKind,
    title: str,
    text: str,
    tags: Sequence[str],
    author: str,
    reason: str,
    replaces: tuple[str, str] | None = None,
) -> str | None:
    """Écrit (et indexe) l'élément, ou met à jour celui qui portait `replaces` (titre, texte).
    Rend son identifiant ; une panne de la mémoire est journalisée par son type et rend `None` :
    l'écriture de la feature, elle, a déjà eu lieu."""
    try:
        async with runtime.session_factory() as db:
            service = MemoryService(db, user_id, runtime)
            item = None
            if replaces is not None:
                item = await _replace(service, db, user_id, kind, replaces, (title, text), tags)
            if item is None:
                draft = WriteDraft(
                    kind=kind,
                    title=title,
                    text=text,
                    author=author,
                    reason=reason,
                    tags=tuple(tags),
                )
                item = (await service.write(draft)).item
            item_id = item.id
            await _settle(db, item)
            return item_id
    except Exception as exc:
        logger.warning("Élément de mémoire non écrit (%s)", type(exc).__name__)
        return None
