from collections.abc import Collection, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, case, func, literal, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brain import BrainFile, BrainFolder
from app.db.models.memory import Document, MemoryChunk, MemoryItem


class NoteReadingRepository:
    """Active Memory rows whose document is still linked to the synchroniser."""

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self._db = session
        self._user_id = user_id

    def _active(self) -> Select[BrainFile, MemoryItem]:
        user = self._user_id
        return (
            select(BrainFile, MemoryItem)
            .join(
                BrainFolder,
                and_(BrainFolder.id == BrainFile.folder_id, BrainFolder.user_id == user),
            )
            .join(Document, and_(Document.id == BrainFile.document_id, Document.user_id == user))
            .join(MemoryItem, and_(MemoryItem.id == Document.item_id, MemoryItem.user_id == user))
            .where(
                BrainFile.user_id == user,
                Document.status == "indexed",
                MemoryItem.kind == "document",
                MemoryItem.status == "active",
            )
        )

    async def link_entries(self) -> list[tuple[str, str, str, str, dict[str, Any] | None]]:
        """Resolution metadata of active notes. Their texts are not read."""
        stmt = self._active().with_only_columns(
            BrainFile.folder_id,
            BrainFile.path,
            MemoryItem.id,
            MemoryItem.title,
            Document.sync_metadata,
        )
        return [
            (folder, path, key, title, metadata)
            for folder, path, key, title, metadata in await self._db.execute(stmt)
        ]

    async def versions(self, ids: Collection[str]) -> dict[str, str]:
        if not ids:
            return {}
        stmt = (
            self._active()
            .where(MemoryItem.id.in_(ids))
            .with_only_columns(MemoryItem.id, BrainFile.sha256, MemoryItem.content_hash)
        )
        return {item_id: f"{file}:{item}" for item_id, file, item in await self._db.execute(stmt)}

    async def explicitly_linked(
        self, references: Collection[str]
    ) -> list[tuple[str, str, str, datetime]]:
        if not references:
            return []
        links = func.json_each(Document.sync_metadata["links"]).table_valued("key", "value")
        stmt = (
            self._active()
            .join(links, true())
            .where(Document.source_kind == "markdown", links.c.value.in_(references))
            .with_only_columns(
                links.c.value, MemoryItem.title, MemoryItem.text, BrainFile.updated_at
            )
            .order_by(MemoryItem.title, MemoryItem.id)
        )
        return [
            (reference, title, text, changed_at)
            for reference, title, text, changed_at in await self._db.execute(stmt)
        ]

    async def matching(self, terms: Sequence[str], limit: int) -> list[tuple[str, str, str, str]]:
        """One chunk per note, the best ranked by its title and text."""
        score: ColumnElement[int] = literal(0)
        for term in terms:
            score = (
                score
                + case((func.lower(MemoryItem.title).contains(term, autoescape=True), 4), else_=0)
                + case((func.lower(MemoryChunk.text).contains(term, autoescape=True), 1), else_=0)
            )
        rank = func.row_number().over(
            partition_by=MemoryItem.id,
            order_by=(score.desc(), MemoryChunk.ordinal),
        )
        ranked = (
            self._active()
            .join(
                MemoryChunk,
                and_(MemoryChunk.item_id == MemoryItem.id, MemoryChunk.user_id == self._user_id),
            )
            .where(score > 0)
            .with_only_columns(
                MemoryItem.id.label("id"),
                MemoryItem.title.label("title"),
                BrainFile.sha256.label("file_version"),
                MemoryItem.content_hash.label("item_version"),
                MemoryChunk.text.label("text"),
                score.label("score"),
                rank.label("rank"),
            )
        ).subquery()
        cols = ranked.c
        stmt = (
            select(cols.id, cols.title, cols.file_version, cols.item_version, cols.text)
            .where(cols.rank == 1)
            .order_by(cols.score.desc(), cols.id)
            .limit(limit)
        )
        return [
            (item_id, title, f"{file_version}:{item_version}", content)
            for item_id, title, file_version, item_version, content in await self._db.execute(stmt)
        ]
