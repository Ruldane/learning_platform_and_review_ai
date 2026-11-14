"""Le fichier d'un document importé, relu pour une autre feature (contrat 2) : le profil maître
relit le PDF du CV par son fichier, pas par les fragments indexés (preflight G6, D124). Rien
n'est journalisé du fichier ni de son nom."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.memory.repository import DocumentRepository
from app.features.memory.service.runtime import MemoryRuntime


@dataclass(frozen=True)
class StoredFile:
    document_id: str
    source_kind: str  # `DocumentSourceKind`
    tags: tuple[str, ...]
    data: bytes


async def document_file(
    runtime: MemoryRuntime, user_id: str, document_id: str
) -> StoredFile | None:
    """Le fichier du document de l'utilisateur ; `None` s'il est absent, d'un autre ou sans
    fichier (lien)."""
    async with runtime.session_factory() as db:
        doc = await DocumentRepository(db, user_id).get(document_id)
        if doc is None or doc.storage_key is None:
            return None
        kind, tags, key = doc.source_kind, tuple(map(str, doc.tags)), doc.storage_key
    data = await runtime.providers.storage.read(user_id, key)
    return StoredFile(document_id, kind, tags, data)


async def document_tags(db: AsyncSession, user_id: str, document_id: str) -> tuple[str, ...] | None:
    """Les étiquettes du document de l'utilisateur ; `None` s'il est absent ou d'un autre."""
    doc = await DocumentRepository(db, user_id).get(document_id)
    return None if doc is None else tuple(map(str, doc.tags))
