"""Prepares and removes the local documents entrusted to the memory's ingestion chain."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id
from app.db.models.memory import USER_AUTHOR, Document
from app.features.memory.repository import DocumentRepository, MemoryItemRepository, WriteRepository
from app.features.memory.service.documents import STORAGE_CATEGORY
from app.features.memory.service.obsidian import note_metadata
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.text import display_name, source_hash
from app.features.memory.service.upload import (
    SUFFIX_OF,
    UploadKind,
    detect_upload,
    unsupported_file_type,
)

logger = logging.getLogger(__name__)
_CORE_EXTENSIONS = frozenset({".pdf", ".docx", ".md", ".markdown", ".txt"})
_CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".mts",
        ".cts",
        ".ipynb",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
        ".sh",
        ".ps1",
        ".html",
        ".css",
        ".java",
        ".kt",
        ".rb",
        ".go",
        ".rs",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cs",
        ".r",
        ".lua",
        ".php",
        ".swift",
        ".scala",
        ".vue",
        ".svelte",
        ".xml",
        ".rst",
        ".adoc",
    }
)


@dataclass(frozen=True)
class SyncDraft:
    name: str
    data: bytes
    kind: UploadKind
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RemovedDocument:
    key: str | None
    item_id: str | None


def prepare_sync_document(path: str, data: bytes) -> SyncDraft:
    """Detects the case from the validated path, and replays the existing import checks."""
    relative = PurePosixPath(path)
    suffix = relative.suffix.lower()
    filename = relative.name
    if suffix in _CODE_EXTENSIONS:
        filename = "code.txt"
    elif suffix not in _CORE_EXTENSIONS:
        raise unsupported_file_type()
    kind = detect_upload(filename, data)
    metadata = note_metadata(data.decode("utf-8-sig")) if kind == "markdown" else {}
    return SyncDraft(display_name(relative.name), data, kind, metadata)


async def store_sync_document(
    db: AsyncSession, runtime: MemoryRuntime, user_id: str, draft: SyncDraft
) -> Document:
    """Writes the new document in the calling transaction, before queueing."""
    storage = runtime.providers.storage
    key = await storage.save(user_id, STORAGE_CATEGORY, draft.data, SUFFIX_OF[draft.kind])
    try:
        return await DocumentRepository(db, user_id).add(
            name=draft.name,
            status="queued",
            source_kind=draft.kind,
            source_hash=source_hash(f"brain:{new_id()}".encode()),
            storage_key=key,
            size_bytes=len(draft.data),
            tags=draft.metadata.get("tags", []),
            sync_metadata=draft.metadata,
        )
    except BaseException:
        await delete_sync_file(runtime, user_id, key)
        raise


async def retire_sync_document(
    db: AsyncSession, user_id: str, document_id: str
) -> RemovedDocument | None:
    docs = DocumentRepository(db, user_id)
    doc = await docs.get(document_id)
    if doc is None or doc.sync_metadata is None:
        return None
    items = MemoryItemRepository(db, user_id)
    item = await items.find_document_of(document_id)
    if item is not None:
        await WriteRepository(db, user_id).log(
            item=item,
            action="delete",
            author=USER_AUTHOR,
            session_id=None,
            reason="Removal of the synced document.",
        )
        await items.delete(item.id)
    await docs.delete(doc.id)
    return RemovedDocument(doc.storage_key, item.id if item is not None else None)


async def delete_sync_file(runtime: MemoryRuntime, user_id: str, key: str) -> None:
    try:
        await runtime.providers.storage.delete(user_id, key)
    except Exception as exc:
        logger.warning("Cleaning up synced files %s (%s)", user_id, type(exc).__name__)


async def clean_removed_documents(
    runtime: MemoryRuntime, user_id: str, removed: Sequence[RemovedDocument]
) -> None:
    items = [entry.item_id for entry in removed if entry.item_id is not None]
    if items:
        await runtime.indexer.unindex(user_id, items)
    for entry in removed:
        if entry.key is not None:
            await delete_sync_file(runtime, user_id, entry.key)
