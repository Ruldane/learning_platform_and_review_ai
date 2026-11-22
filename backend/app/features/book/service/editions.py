"""Demande d'une édition et téléchargement à partir des pointeurs publiés."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.book import ProgramBook
from app.features.book.repository import BookRepository
from app.features.book.schemas import BookFormat, BookOut, BookStatus
from app.features.book.service.runtime import BookRuntime
from app.features.program.service.programs import load
from app.providers.storage.base import StorageKeyInvalid


def _view(row: ProgramBook | None) -> BookOut:
    if row is None:
        return BookOut(status="not_requested")
    available = row.pdf_key is not None and row.epub_key is not None
    status: BookStatus = "failed" if row.failed else "ready" if available else "queued"
    return BookOut(
        status=status, available=available, chapters=row.chapters, rendered_at=row.rendered_at
    )


async def read_edition(db: AsyncSession, user_id: str, program_id: str) -> BookOut:
    await load(db, user_id, program_id)
    return _view(await BookRepository(db, user_id).get(program_id))


async def queue_edition(db: AsyncSession, user_id: str, program_id: str) -> BookOut:
    await load(db, user_id, program_id)
    return _view(await BookRepository(db, user_id).queue(program_id))


async def download(
    runtime: BookRuntime, user_id: str, program_id: str, format_: BookFormat
) -> bytes:
    for _ in range(2):
        async with runtime.session_factory() as db:
            edition = await BookRepository(db, user_id).get(program_id)
            if edition is None:
                break
            key = edition.pdf_key if format_ == "pdf" else edition.epub_key
        if key is None:
            break
        try:
            return await runtime.storage.read(user_id, key)
        except (FileNotFoundError, StorageKeyInvalid):
            # Une nouvelle édition a pu remplacer l'ancienne entre la lecture et le disque.
            continue
    raise AppError("book_file_missing", "Cette édition n’est pas disponible.", 404)
