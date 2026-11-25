"""Agents' memory gateway (D68): implements the `MemoryGateway` port of `app.agents` on the
memory service. Each call opens its own short database session: an agent session never holds
an open transaction during a call to Ollama or Qdrant (D66).

Writing goes through `MemoryService.write`: write rules, deduplication (a replayed node doubles
nothing), log (agent, session, reason) and indexing, which is the LAST step (it commits the
transaction before vectorizing, then sets `indexed_at` separately). During a reindexing,
`index_item` leaves the item unindexed: the reindexing loop catches it up. No log quotes
content."""

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
from app.db.models.memory import MEMORY_KINDS, MemoryKind, current_memory_kind
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
SKILLS_MAX = 500  # learned items read for the summary (the most recent)


def _kinds(kinds: Sequence[str] | None) -> list[MemoryKind] | None:
    if not kinds:
        return None
    resolved = [current_memory_kind(kind) for kind in kinds]
    if unknown := [kind for kind in resolved if kind not in MEMORY_KINDS]:
        raise AppError(
            "memory_kind_invalid", "Unknown memory item type.", 422, {"kinds": sorted(set(unknown))}
        )
    return cast(list[MemoryKind], resolved)


class AgentMemoryGateway:
    def __init__(self, runtime: MemoryRuntime) -> None:
        self._runtime = runtime

    async def search(
        self, user_id: str, query: str, *, kinds: Sequence[str] | None, k: int
    ) -> MemorySearchResult:
        """Query trimmed to 500 characters, `k` bounded to 1..50; Ollama or Qdrant down: readable
        503 (the service's error)."""
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
            if item.status != "active":  # nothing validated the write: no indexing
                await db.commit()
        if result.created:
            logger.info("Memory: %s written by %s (session %s)", item.id, author, session_id)
        return result

    async def skills(self, user_id: str) -> SkillsSummary:
        """Active learned items (the 500 most recent): the total is exact, the breakdown by level
        covers the items read. Until phase 4 (`user_skills`, D6), learned items are read from
        memory."""
        async with self._runtime.session_factory() as db:
            rows, total = await MemoryItemRepository(db, user_id).filtered(
                ItemFilter(kind="skill"), limit=SKILLS_MAX, offset=0
            )
        skills = [
            SkillEntry(
                item_id=row.id,
                title=row.title,
                level=str((row.meta or {}).get("level", "declared")),
                tags=[str(tag) for tag in row.tags],
            )
            for row in rows
        ]
        return SkillsSummary(total, dict(Counter(skill.level for skill in skills)), skills)

    async def document_text(
        self, user_id: str, document_id: str, *, max_chunks: int
    ) -> DocumentText | None:
        """The first chunks of one of the user's indexed documents, in order; `None` if the
        document does not exist, is not theirs or is not (yet) indexed."""
        async with self._runtime.session_factory() as db:
            doc = await DocumentRepository(db, user_id).get(document_id)
            if doc is None or doc.status != "indexed" or doc.item_id is None:
                return None
            item = await MemoryItemRepository(db, user_id).get(doc.item_id)
            if item is None:
                return None
            chunks = await ChunkRepository(db, user_id).for_item(item.id, limit=max_chunks)
        return DocumentText(document_id, item.title or doc.name, [chunk.text for chunk in chunks])
