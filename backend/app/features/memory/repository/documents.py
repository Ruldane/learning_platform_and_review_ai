import builtins

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory import Document
from app.db.repository import UserScopedRepository


class DocumentRepository(UserScopedRepository[Document]):
    model = Document

    async def find_by_source_hash(self, source_hash: str) -> Document | None:
        stmt = select(Document).where(
            Document.user_id == self.user_id, Document.source_hash == source_hash
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_recent(self, limit: int | None = 200) -> builtins.list[Document]:
        """The user's documents, most recent first (`None`: all, for the export)."""
        stmt = (
            select(Document)
            .where(Document.user_id == self.user_id)
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def for_item(self, item_id: str) -> builtins.list[Document]:
        """Documents whose learned summary is the item `item_id`."""
        stmt = (
            select(Document)
            .where(Document.user_id == self.user_id, Document.item_id == item_id)
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


async def list_documents_to_resume(db: AsyncSession) -> list[tuple[str, str]]:
    """`(user_id, document_id)` of `queued` or `processing` documents, across all users,
    oldest to newest.

    Second read in the project that does not filter by `user_id`, after
    `list_sessions_to_recover`: it is reserved for server startup, when the worker resumes
    ingestions interrupted by a shutdown. Never call it from a user's request.
    """
    stmt = (
        select(Document.user_id, Document.id)
        .where(Document.status.in_(("queued", "processing")))
        .order_by(Document.created_at, Document.id)
    )
    return [(user_id, doc_id) for user_id, doc_id in (await db.execute(stmt)).all()]
