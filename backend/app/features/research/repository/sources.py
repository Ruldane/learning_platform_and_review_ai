import builtins

from sqlalchemy import ColumnElement, func, literal_column, select

from app.db.models.research import Source
from app.db.repository import UserScopedRepository


class SourceRepository(UserScopedRepository[Source]):
    """Sources found by a user's search sessions."""

    model = Source

    def _of_session(self, session_id: str) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
        return (Source.user_id == self.user_id, Source.session_id == session_id)

    async def get_by_url(self, session_id: str, url_hash: str) -> Source | None:
        stmt = select(Source).where(*self._of_session(session_id), Source.url_hash == url_hash)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def add(self, source: Source) -> Source:  # type: ignore[override]
        """Records `source` for this user (the `user_id` received is ignored)."""
        source.user_id = self.user_id
        self.session.add(source)
        await self.session.flush()
        return source

    async def count_pages(self, session_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Source)
            .where(*self._of_session(session_id), Source.kind == "page")
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_for_session(self, session_id: str) -> builtins.list[Source]:
        stmt = (
            select(Source)
            .where(*self._of_session(session_id))
            .order_by(Source.created_at, literal_column("rowid"))  # rowid: insertion order
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())
