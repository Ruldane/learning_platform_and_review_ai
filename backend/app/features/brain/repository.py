"""Accès aux dossiers et inventaires, toujours limité au compte."""

import builtins
from collections import Counter, defaultdict

from sqlalchemy import ColumnElement, Select, and_, func, select, update
from sqlalchemy.dialects.sqlite import insert

from app.db.base import utcnow
from app.db.models.brain import BrainFile, BrainFolder, BrainSyncToken
from app.db.models.memory import Document
from app.db.repository import UserScopedRepository


class FolderRepository(UserScopedRepository[BrainFolder]):
    model = BrainFolder

    async def ordered(self) -> builtins.list[BrainFolder]:
        stmt = (
            select(BrainFolder)
            .where(BrainFolder.user_id == self.user_id)
            .order_by(BrainFolder.name, BrainFolder.id)
        )
        return builtins.list(await self.session.scalars(stmt))

    async def begin_write(self) -> None:
        stmt = update(BrainFolder).where(BrainFolder.id == "", BrainFolder.user_id == self.user_id)
        await self.session.execute(stmt.values(updated_at=BrainFolder.updated_at))


class FileRepository(UserScopedRepository[BrainFile]):
    model = BrainFile

    async def by_path(self, folder_id: str, path: str) -> tuple[BrainFile, Document] | None:
        stmt = self._with_document().where(BrainFile.folder_id == folder_id, BrainFile.path == path)
        row = (await self.session.execute(stmt)).one_or_none()
        return None if row is None else (row[0], row[1])

    def _with_document(self) -> Select[BrainFile, Document]:
        return (
            select(BrainFile, Document)
            .join(Document, self._matches())
            .where(BrainFile.user_id == self.user_id)
        )

    def _matches(self) -> ColumnElement[bool]:
        return and_(Document.id == BrainFile.document_id, Document.user_id == self.user_id)

    async def inventory(self, folder_id: str) -> builtins.list[tuple[BrainFile, Document]]:
        stmt = (
            self._with_document().where(BrainFile.folder_id == folder_id).order_by(BrainFile.path)
        )
        return [(row[0], row[1]) for row in await self.session.execute(stmt)]

    async def counts(self) -> dict[str, Counter[str]]:
        stmt = (
            select(BrainFile.folder_id, Document.status, func.count(BrainFile.id))
            .join(Document, self._matches())
            .where(BrainFile.user_id == self.user_id)
            .group_by(BrainFile.folder_id, Document.status)
        )
        result: dict[str, Counter[str]] = defaultdict(Counter)
        for folder_id, status, count in await self.session.execute(stmt):
            result[folder_id][status] = count
        return dict(result)


class SyncTokenRepository(UserScopedRepository[BrainSyncToken]):
    model = BrainSyncToken

    async def matches(self, digest: str) -> bool:
        stmt = select(BrainSyncToken.id).where(
            BrainSyncToken.user_id == self.user_id,
            BrainSyncToken.token_hash == digest,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def rotate(self, digest: str) -> None:
        stmt = insert(BrainSyncToken).values(user_id=self.user_id, token_hash=digest)
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[BrainSyncToken.user_id],
                set_={"token_hash": digest, "updated_at": utcnow()},
            )
        )
