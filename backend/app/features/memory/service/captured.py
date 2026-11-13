"""La mémoire vue par la capture rapide (SPEC F18, D108) : l'état d'un document importé de
January, et l'écriture de sa capture résumée en élément `document` (auteur l'Archiviste, raison
« Capture rapide de January. »), indexée après le commit de l'appelant (D66). Lectures et
écritures pour les autres features (contrat 2). Journaux : identifiants seulement."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory import MemoryItem
from app.features.memory.repository import DocumentRepository, MemoryItemRepository
from app.features.memory.service.items import MemoryService
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime

CAPTURE_AUTHOR = "archivist"
CAPTURE_REASON = "Capture rapide de January."


@dataclass(frozen=True)
class DocumentState:
    status: str  # `queued`, `processing`, `indexed` ou `error`
    name: str
    url: str | None


async def document_state(db: AsyncSession, user_id: str, document_id: str) -> DocumentState | None:
    """L'état d'un document de l'utilisateur, `None` s'il n'existe pas ou n'est pas à lui."""
    doc = await DocumentRepository(db, user_id).get(document_id)
    return None if doc is None else DocumentState(doc.status, doc.name, doc.url)


async def write_capture(
    db: AsyncSession,
    runtime: MemoryRuntime,
    user_id: str,
    *,
    title: str,
    text: str,
    tags: Sequence[str],
    session_id: str,
) -> MemoryItem:
    """L'élément `document` de la capture (sans `source_id` : le supprimer ne touche à aucun
    document importé). Même contenu déjà là : l'existant. Non indexé ici, et non commité : la
    transaction est celle de l'appelant, qui indexe ensuite (`index_capture`)."""
    draft = WriteDraft(
        kind="document",
        title=title,
        text=text,
        author=CAPTURE_AUTHOR,
        reason=CAPTURE_REASON,
        tags=tuple(tags),
        session_id=session_id,
        captured=True,
    )
    return (await MemoryService(db, user_id, runtime).write(draft, index=False)).item


async def index_capture(runtime: MemoryRuntime, user_id: str, item_id: str) -> bool:
    """Indexe l'élément s'il ne l'est pas encore (rejeu compris) ; vrai s'il est indexé. Une
    panne d'Ollama ou de Qdrant le laisse non indexé, sans exception : la réindexation le
    rattrapera."""
    async with runtime.session_factory() as db:
        item = await MemoryItemRepository(db, user_id).get(item_id)
        if item is None:
            return False
        if item.indexed_at is not None:
            return True
        return await runtime.indexer.index_item(db, item)
