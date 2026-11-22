from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.reading_stack import ReadingItem, ReadingKind
from app.features.reading_stack.repository import ReadingRepository
from app.features.reading_stack.schemas import ReadingDetail, ReadingItemOut, ReadingPage
from app.features.reading_stack.service.glossary import annotations

PAGE_SIZE = 50


def reading_not_found() -> AppError:
    return AppError("reading_not_found", "Élément de lecture introuvable.", 404)


async def read_entry(db: AsyncSession, user_id: str, item_id: str) -> ReadingItem:
    row = await ReadingRepository(db, user_id).get(item_id)
    if row is None:
        raise reading_not_found()
    return row


async def read_detail(db: AsyncSession, user_id: str, item_id: str) -> ReadingDetail:
    row = await read_entry(db, user_id, item_id)
    detail = ReadingDetail.model_validate(row)
    detail.annotations = await annotations(db, user_id, detail.text)
    return detail


async def list_entries(
    db: AsyncSession,
    user_id: str,
    unread: bool | None,
    kind: ReadingKind | None,
    offset: int,
) -> ReadingPage:
    repo = ReadingRepository(db, user_id)
    rows = await repo.items(unread=unread, kind=kind, offset=offset)
    return ReadingPage(
        items=[ReadingItemOut.model_validate(row) for row in rows],
        unread_count=await repo.unread_count(),
        next_offset=offset + PAGE_SIZE if len(rows) == PAGE_SIZE else None,
    )


async def set_read(db: AsyncSession, user_id: str, item_id: str, read: bool) -> ReadingDetail:
    row = await ReadingRepository(db, user_id).mark_read(item_id, read, utcnow())
    if row is None:
        raise reading_not_found()
    return ReadingDetail.model_validate(row)


async def unread_count(db: AsyncSession, user_id: str) -> int:
    return await ReadingRepository(db, user_id).unread_count()
