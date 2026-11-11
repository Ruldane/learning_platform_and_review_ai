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
        """Documents de l'utilisateur, les plus récents d'abord (`None` : tous, pour l'export)."""
        stmt = (
            select(Document)
            .where(Document.user_id == self.user_id)
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def for_item(self, item_id: str) -> builtins.list[Document]:
        """Documents dont l'élément `item_id` est le résumé appris."""
        stmt = (
            select(Document)
            .where(Document.user_id == self.user_id, Document.item_id == item_id)
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


async def list_documents_to_resume(db: AsyncSession) -> list[tuple[str, str]]:
    """`(user_id, document_id)` des documents `queued` ou `processing`, tous utilisateurs
    confondus, du plus ancien au plus récent.

    Deuxième lecture du projet qui ne filtre pas par `user_id`, après `list_sessions_to_recover` :
    elle est réservée au démarrage du serveur, quand le worker reprend les ingestions
    interrompues par un arrêt. Ne jamais l'appeler depuis une requête d'un utilisateur.
    """
    stmt = (
        select(Document.user_id, Document.id)
        .where(Document.status.in_(("queued", "processing")))
        .order_by(Document.created_at, Document.id)
    )
    return [(user_id, doc_id) for user_id, doc_id in (await db.execute(stmt)).all()]
