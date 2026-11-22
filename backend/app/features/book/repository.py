"""Demandes et pointeurs de publication du livre d'un compte."""

from sqlalchemy import ColumnElement, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models.book import ProgramBook


class BookRepository:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._db = db
        self._user = user_id

    def _owned(self, program_id: str) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
        return (ProgramBook.user_id == self._user, ProgramBook.program_id == program_id)

    async def get(self, program_id: str) -> ProgramBook | None:
        stmt = select(ProgramBook).where(*self._owned(program_id))
        return (
            await self._db.scalars(stmt.execution_options(populate_existing=True))
        ).one_or_none()

    async def program_ids(self) -> tuple[str, ...]:
        stmt = (
            select(ProgramBook.program_id)
            .where(ProgramBook.user_id == self._user)
            .order_by(ProgramBook.updated_at, ProgramBook.id)
        )
        return tuple(await self._db.scalars(stmt))

    async def queue(self, program_id: str) -> ProgramBook:
        stmt = insert(ProgramBook).values(program_id=program_id, user_id=self._user)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "program_id"])
        await self._db.execute(stmt)
        await self._db.execute(
            update(ProgramBook)
            .where(*self._owned(program_id), ProgramBook.failed.is_(True))
            .values(failed=False, revision=ProgramBook.revision + 1)
        )
        edition = await self.get(program_id)
        assert edition is not None
        return edition

    async def publish(
        self, program_id: str, revision: int, source_hash: str, keys: tuple[str, str], chapters: int
    ) -> bool:
        stmt = (
            update(ProgramBook)
            .where(*self._owned(program_id), ProgramBook.revision == revision)
            .values(
                revision=revision + 1,
                source_hash=source_hash,
                pdf_key=keys[0],
                epub_key=keys[1],
                chapters=chapters,
                rendered_at=utcnow(),
                failed=False,
            )
            .returning(ProgramBook.id)
        )
        return (await self._db.scalars(stmt)).one_or_none() is not None

    async def fail(self, program_id: str, revision: int) -> None:
        await self._db.execute(
            update(ProgramBook)
            .where(
                *self._owned(program_id),
                ProgramBook.revision == revision,
                ProgramBook.failed.is_(False),
            )
            .values(failed=True, revision=revision + 1)
        )
