"""Indexed notes still present in the source's sync folder."""

from dataclasses import dataclass

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brain import BrainFile, BrainFolder
from app.db.models.memory import Document, MemoryItem


@dataclass(frozen=True)
class NoteCandidate:
    path: str
    item_id: str
    title: str


async def active_folder_notes(db: AsyncSession, user: str, item_id: str) -> list[NoteCandidate]:
    origin_folder = (
        select(BrainFile.folder_id)
        .join(Document, and_(Document.id == BrainFile.document_id, Document.user_id == user))
        .where(BrainFile.user_id == user, Document.item_id == item_id)
        .scalar_subquery()
    )
    stmt = (
        select(BrainFile.path, MemoryItem.id, MemoryItem.title)
        .join(BrainFolder, and_(BrainFolder.id == BrainFile.folder_id, BrainFolder.user_id == user))
        .join(Document, and_(Document.id == BrainFile.document_id, Document.user_id == user))
        .join(MemoryItem, and_(MemoryItem.id == Document.item_id, MemoryItem.user_id == user))
        .where(
            BrainFile.user_id == user,
            BrainFile.folder_id == origin_folder,
            Document.status == "indexed",
            MemoryItem.kind == "document",
            MemoryItem.status == "active",
        )
    )
    return [NoteCandidate(path, key, title) for path, key, title in await db.execute(stmt)]
