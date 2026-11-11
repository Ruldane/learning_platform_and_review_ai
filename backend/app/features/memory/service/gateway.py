"""Passerelle mémoire des agents (D68) : implémente le port `MemoryGateway` de `app.agents` sur le
service mémoire. Chaque appel ouvre sa propre session de base, courte : une session d'agent ne
tient jamais de transaction ouverte pendant un appel à Ollama ou à Qdrant (D66).

L'écriture passe par `MemoryService.write` : règles d'écriture, dédoublonnage (un nœud rejoué ne
double rien), journal (agent, session, raison) et indexation, qui est la DERNIÈRE étape (elle
valide la transaction avant de vectoriser, puis pose `indexed_at` à part). Pendant une
réindexation, `index_item` laisse l'élément non indexé : la boucle de réindexation le rattrape.
Aucun journal ne cite de contenu."""

import logging
from collections import Counter
from collections.abc import Sequence
from typing import cast

from app.agents.tools.memory_port import (
    AgentWrite,
    DocumentText,
    MemoryHitView,
    MemorySearchResult,
    SkillEntry,
    SkillsSummary,
    WriteResult,
)
from app.core.errors import AppError
from app.db.models.memory import MEMORY_KINDS, MemoryKind
from app.features.memory.repository import (
    ChunkRepository,
    DocumentRepository,
    ItemFilter,
    MemoryItemRepository,
)
from app.features.memory.schemas import SearchRequest
from app.features.memory.service.items import MemoryService
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.search import search

logger = logging.getLogger(__name__)

QUERY_MAX = 500  # `SearchRequest.query`
K_MAX = 50  # `SearchRequest.k`
SKILLS_MAX = 500  # acquis lus pour le résumé (les plus récents)


def _kinds(kinds: Sequence[str] | None) -> list[MemoryKind] | None:
    if not kinds:
        return None
    if unknown := [kind for kind in kinds if kind not in MEMORY_KINDS]:
        raise AppError(
            "memory_kind_invalid", "Type de mémoire inconnu.", 422, {"kinds": sorted(set(unknown))}
        )
    return cast(list[MemoryKind], list(kinds))


class AgentMemoryGateway:
    def __init__(self, runtime: MemoryRuntime) -> None:
        self._runtime = runtime

    async def search(
        self, user_id: str, query: str, *, kinds: Sequence[str] | None, k: int
    ) -> MemorySearchResult:
        """Requête rognée à 500 caractères, `k` borné à 1..50 ; Ollama ou Qdrant arrêté : 503
        lisible (l'erreur du service)."""
        request = SearchRequest(
            query=query.strip()[:QUERY_MAX] or " ", kinds=_kinds(kinds), k=max(1, min(k, K_MAX))
        )
        async with self._runtime.session_factory() as db:
            found = await search(db, user_id, self._runtime, request)
        views = [
            MemoryHitView(
                item_id=hit.item_id,
                chunk_id=hit.chunk_id,
                kind=hit.kind,
                title=hit.title,
                text=hit.text,
                score=hit.score,
                created_by=hit.created_by,
            )
            for hit in found.hits
        ]
        return MemorySearchResult(views, found.agent_text)

    async def write(
        self, user_id: str, session_id: str, author: str, write: AgentWrite
    ) -> WriteResult:
        draft = WriteDraft(
            kind=write.kind,
            title=write.title,
            text=write.text,
            author=author,
            reason=write.reason,
            tags=write.tags,
            evidence=write.evidence,
            level=write.level,
            session_id=session_id,
            source_id=write.source_id,
        )
        async with self._runtime.session_factory() as db:
            outcome = await MemoryService(db, user_id, self._runtime).write(draft)
            item = outcome.item
            result = WriteResult(
                item_id=item.id,
                kind=item.kind,
                title=item.title,
                status="pending" if item.status == "pending" else "active",
                created=outcome.created,
            )
            if item.status != "active":  # rien n'a validé l'écriture : pas d'indexation
                await db.commit()
        if result.created:
            logger.info("Mémoire : %s écrit par %s (session %s)", item.id, author, session_id)
        return result

    async def skills(self, user_id: str) -> SkillsSummary:
        """Acquis actifs (les 500 plus récents) : le total est exact, la répartition par niveau
        porte sur les acquis lus. Jusqu'à la phase 4 (`user_skills`, D6), les acquis sont lus
        dans la mémoire."""
        async with self._runtime.session_factory() as db:
            rows, total = await MemoryItemRepository(db, user_id).filtered(
                ItemFilter(kind="acquis"), limit=SKILLS_MAX, offset=0
            )
        skills = [
            SkillEntry(
                item_id=row.id,
                title=row.title,
                level=str((row.meta or {}).get("level", "declare")),
                tags=[str(tag) for tag in row.tags],
            )
            for row in rows
        ]
        return SkillsSummary(total, dict(Counter(skill.level for skill in skills)), skills)

    async def document_text(
        self, user_id: str, document_id: str, *, max_chunks: int
    ) -> DocumentText | None:
        """Les premiers fragments d'un document indexé de l'utilisateur, dans l'ordre ; `None` si
        le document n'existe pas, n'est pas à lui ou n'est pas (encore) indexé."""
        async with self._runtime.session_factory() as db:
            doc = await DocumentRepository(db, user_id).get(document_id)
            if doc is None or doc.status != "indexed" or doc.item_id is None:
                return None
            item = await MemoryItemRepository(db, user_id).get(doc.item_id)
            if item is None:
                return None
            chunks = await ChunkRepository(db, user_id).for_item(item.id, limit=max_chunks)
        return DocumentText(document_id, item.title or doc.name, [chunk.text for chunk in chunks])
