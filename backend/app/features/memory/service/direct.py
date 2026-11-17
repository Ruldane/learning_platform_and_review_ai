"""Éléments de mémoire écrits en direct par une feature qui n'a pas d'agent derrière elle (phase
10, 10.W) : la leçon ou l'offre que Claude (par le MCP) ou January écrit elle-même. Même écriture
que celle des agents (règles, dédoublonnage, journal), sans passerelle d'agent ni session.

**L'appel n'indexe pas.** L'élément est écrit (ou mis à jour) dans la transaction de la feature,
avec `indexed_at` vide, et l'indexation (fragments, embeddings, Qdrant) suit hors de l'appel :
`schedule_indexing` la lance après la réponse, l'annulation du MCP la relance, et la tâche
d'entretien la rattrape après un redémarrage (`index_pending_all`). Raison : l'historique du MCP ne
retire que ce qu'il a vu ; une indexation dans l'appel pose `indexed_at` et remplace les fragments
par des requêtes en masse, que l'annulation ne saurait défaire. Une retouche ne touche donc pas aux
fragments : elle remet `indexed_at` à vide, et l'annulation fait de même (`app.mcp.undo`).

Un vecteur d'un élément retiré par l'annulation reste dans Qdrant jusqu'à la prochaine
réindexation ; la recherche écarte tout vecteur sans fragment ni élément en base. Aucun appel au
modèle : seulement les embeddings."""

import asyncio
import contextvars
import logging
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory import USER_AUTHOR, MemoryItem, MemoryKind
from app.features.memory.repository import (
    MemoryItemRepository,
    WriteRepository,
    users_with_unindexed,
)
from app.features.memory.schemas import MemoryItemPatch
from app.features.memory.service.items import MemoryService, _content
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.text import content_hash

logger = logging.getLogger(__name__)

__all__ = [
    "author_of",
    "drain_indexing",
    "index_pending",
    "index_pending_all",
    "schedule_indexing",
    "write_direct",
]

MCP_AUTHOR = "claude"
BATCH = 16  # éléments indexés par passage et par utilisatrice
USERS = 20  # utilisatrices vues par passage de la tâche d'entretien
_TASKS: set["asyncio.Task[None]"] = set()
_paused = False  # crochet des tests : `schedule_indexing` ne lance rien (état « avant indexation »)


def author_of(is_mcp: bool) -> str:
    """`claude` quand l'appel vient du MCP, `user` sinon (l'interface)."""
    return MCP_AUTHOR if is_mcp else USER_AUTHOR


async def _retouch(
    service: MemoryService,
    db: AsyncSession,
    user_id: str,
    kind: MemoryKind,
    old: tuple[str, str],
    new: tuple[str, str],
    tags: Sequence[str],
    author: str,
    reason: str,
) -> MemoryItem | None:
    """L'élément qui portait `old` (titre, texte), mis à jour avec `new` et à réindexer ; `None`
    s'il n'y en a pas. Ses fragments ne sont pas touchés (voir le module)."""
    previous = await MemoryItemRepository(db, user_id).find_by_hash(
        content_hash(kind, *_content(*old))
    )
    if previous is None:
        return None
    patch = MemoryItemPatch.model_construct(title=new[0], text=new[1], tags=list(tags))
    if await service._edit(previous, patch):  # noqa: SLF001 - même paquet : la règle de la retouche
        previous.indexed_at = None
        await WriteRepository(db, user_id).log(
            item=previous, action="update", author=author, session_id=None, reason=reason
        )
    return previous


async def write_direct(
    db: AsyncSession,
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
) -> str:
    """Écrit l'élément, ou met à jour celui qui portait `replaces` (titre, texte), dans la
    transaction de l'appelant (aucun commit : tout ou rien avec la ligne de la feature). Rend son
    identifiant. Une erreur de la mémoire remonte (`AppError` : code, jamais le contenu) et défait
    l'écriture entière. L'appelant lance `schedule_indexing` après son commit."""
    service = MemoryService(db, user_id, runtime)
    item = None
    if replaces is not None:
        item = await _retouch(
            service, db, user_id, kind, replaces, (title, text), tags, author, reason
        )
    if item is None:
        draft = WriteDraft(
            kind=kind, title=title, text=text, author=author, reason=reason, tags=tuple(tags)
        )
        item = (await service.write(draft, index=False)).item
    return item.id


async def index_pending(runtime: MemoryRuntime, user_id: str, limit: int = BATCH) -> int:
    """Indexe les éléments actifs de l'utilisatrice restés à `indexed_at` vide (`limit` au plus) ;
    rend le nombre indexé. S'arrête au premier échec (Ollama ou Qdrant arrêté, réindexation en
    cours) : la passe suivante reprend. Un élément à la fois, chacun dans sa session."""
    async with runtime.session_factory() as db:
        ids = [item.id for item in await MemoryItemRepository(db, user_id).unindexed_batch(limit)]
    done = 0
    for item_id in ids:
        async with runtime.session_factory() as db:
            item = await MemoryItemRepository(db, user_id).get(item_id)
            if item is None or item.indexed_at is not None:
                continue
            if not await runtime.indexer.index_item(db, item):
                break
        done += 1
    return done


async def index_pending_all(runtime: MemoryRuntime) -> int:
    """Un passage de la tâche d'entretien : `index_pending` pour chaque compte qui a des éléments
    à indexer (`USERS` au plus). Une panne est journalisée (son type) et passe au compte suivant."""
    async with runtime.session_factory() as db:
        users = await users_with_unindexed(db, USERS)
    total = 0
    for user_id in users:
        try:
            total += await index_pending(runtime, user_id)
        except Exception as exc:
            logger.warning("Indexation en attente non faite (%s)", type(exc).__name__)
    return total


async def _safely(runtime: MemoryRuntime, user_id: str) -> None:
    try:
        await index_pending(runtime, user_id)
    except Exception as exc:  # la tâche d'entretien reprendra
        logger.warning("Indexation en attente non faite (%s)", type(exc).__name__)


def schedule_indexing(runtime: MemoryRuntime, user_id: str) -> None:
    """Lance `index_pending` en tâche de fond, après la réponse. Elle part d'un contexte vide : ni
    l'historique du MCP ni l'identité de l'appel ne la voient (elle n'écrit que de l'indexation)."""
    if _paused:
        return
    task = asyncio.get_running_loop().create_task(
        _safely(runtime, user_id), context=contextvars.Context()
    )
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)


async def drain_indexing() -> None:
    """Attend les indexations lancées (tests, arrêt propre)."""
    while _TASKS:
        await asyncio.gather(*list(_TASKS), return_exceptions=True)
