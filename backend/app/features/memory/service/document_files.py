"""The file of an imported document, read back for another feature (contract 2): the master
profile rereads the CV PDF from its file, not from the indexed chunks (preflight G6, D124).
Nothing about the file or its name is logged."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.memory.repository import DocumentRepository
from app.features.memory.service.runtime import MemoryRuntime


@dataclass(frozen=True)
class StoredFile:
    document_id: str
    source_kind: str  # `DocumentSourceKind`
    tags: tuple[str, ...]
    data: bytes


async def document_file(
    runtime: MemoryRuntime, user_id: str, document_id: str
) -> StoredFile | None:
    """The file of the user's document; `None` if missing, someone else's or without
    a file (link)."""
    async with runtime.session_factory() as db:
        doc = await DocumentRepository(db, user_id).get(document_id)
        if doc is None or doc.storage_key is None:
            return None
        kind, tags, key = doc.source_kind, tuple(map(str, doc.tags)), doc.storage_key
    data = await runtime.providers.storage.read(user_id, key)
    return StoredFile(document_id, kind, tags, data)


async def document_tags(db: AsyncSession, user_id: str, document_id: str) -> tuple[str, ...] | None:
    """The tags of the user's document; `None` if missing or someone else's."""
    doc = await DocumentRepository(db, user_id).get(document_id)
    return None if doc is None else tuple(map(str, doc.tags))


async def add_document_tag(db: AsyncSession, user_id: str, document_id: str, tag: str) -> None:
    repo = DocumentRepository(db, user_id)
    doc = await repo.get(document_id)
    if doc is not None and tag not in doc.tags:
        doc.tags = [*doc.tags, tag]
