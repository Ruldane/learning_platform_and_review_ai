"""Memory as seen by the quick capture (SPEC F18, D108): the state of a document imported by
January, and the writing of her summarised capture as a `document` item (author the Archivist,
reason `CAPTURE_REASON`), indexed after the caller's commit (D66). Reads and writes for the
other features (contract 2). Logs: identifiers only.

`CAPTURE_REASON` and `CAPTURE_REFLECT_PREFIX` are stored in the write log and matched there
(`recent.py`): they keep their French values until a coordinated migration."""

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
CAPTURE_REFLECT_PREFIX = "Capture « "  # start of the reason for skills reflected by a capture


def reflect_reason(title: str) -> str:
    """The reason for the skills that an "I learned" capture reflects in memory."""
    return f"{CAPTURE_REFLECT_PREFIX}{title} » : January dit l'avoir appris."


@dataclass(frozen=True)
class DocumentState:
    status: str  # `queued`, `processing`, `indexed` or `error`
    name: str
    url: str | None


async def document_state(db: AsyncSession, user_id: str, document_id: str) -> DocumentState | None:
    """The state of a user's document, `None` if it does not exist or is not theirs."""
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
    """The capture's `document` item (without `source_id`: deleting it touches no imported
    document). Same content already there: the existing one. Not indexed here, and not
    committed: the transaction is the caller's, which indexes afterwards (`index_capture`)."""
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
    """Indexes the item if not indexed yet (replay included); true if it is indexed. An
    Ollama or Qdrant outage leaves it unindexed, without an exception: reindexing will catch
    it up."""
    async with runtime.session_factory() as db:
        item = await MemoryItemRepository(db, user_id).get(item_id)
        if item is None:
            return False
        if item.indexed_at is not None:
            return True
        return await runtime.indexer.index_item(db, item)
