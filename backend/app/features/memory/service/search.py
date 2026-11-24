"""Search in a user's memory. The index only returns identifiers and scores: the text,
the title and the author are reread from the database, which is authoritative (D65)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.memory import PREVIOUS_MEMORY_KINDS, MemoryKind
from app.features.memory.repository import ChunkRepository, MemoryItemRepository
from app.features.memory.schemas import SearchHitOut, SearchRequest, SearchResponse
from app.features.memory.service.agent_view import format_for_agent
from app.features.memory.service.runtime import MemoryRuntime


def _indexed_kinds(kinds: list[MemoryKind] | None) -> list[str] | None:
    """Match existing index entries as well as entries indexed since the migration."""
    if not kinds:
        return None
    previous = [PREVIOUS_MEMORY_KINDS[kind] for kind in kinds if kind in PREVIOUS_MEMORY_KINDS]
    return [*kinds, *previous]


async def search(
    db: AsyncSession, user_id: str, runtime: MemoryRuntime, req: SearchRequest
) -> SearchResponse:
    """An empty query is rejected before any embedding. A vector without a chunk or item in the
    database (orphan), or whose item awaits confirmation, is dropped. Ollama or Qdrant
    unavailable: readable 503 (the port's error)."""
    query = req.query.strip()
    if not query:
        raise AppError("memory_query_empty", "The search cannot be empty.", 422)
    found = await runtime.providers.index.search(
        user_id, query, kinds=_indexed_kinds(req.kinds), k=req.k
    )
    chunks = await ChunkRepository(db, user_id).get_many([h.chunk_id for h in found])
    items = await MemoryItemRepository(db, user_id).get_many(
        list({chunk.item_id for chunk in chunks.values()})
    )
    hits: list[SearchHitOut] = []
    for hit in found:
        chunk = chunks.get(hit.chunk_id)
        item = items.get(chunk.item_id) if chunk is not None else None
        if chunk is None or item is None or item.status != "active":
            continue
        hits.append(
            SearchHitOut.model_validate(
                {
                    "chunk_id": chunk.id,
                    "item_id": item.id,
                    "kind": item.kind,
                    "title": item.title,
                    "text": chunk.text,
                    "score": min(hit.score, 1.0),
                    "created_by": item.created_by,
                }
            )
        )
    return SearchResponse(hits=hits, agent_text=format_for_agent(query, hits))
