"""Recherche dans la mémoire d'un utilisateur. L'index ne donne que des identifiants et des
scores : le texte, le titre et l'auteur sont relus en base, qui fait foi (D65)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.memory.repository import ChunkRepository, MemoryItemRepository
from app.features.memory.schemas import SearchHitOut, SearchRequest, SearchResponse
from app.features.memory.service.agent_view import format_for_agent
from app.features.memory.service.runtime import MemoryRuntime


async def search(
    db: AsyncSession, user_id: str, runtime: MemoryRuntime, req: SearchRequest
) -> SearchResponse:
    """Une requête vide est refusée avant toute vectorisation. Un vecteur sans fragment ou sans
    élément en base (orphelin) ou dont l'élément attend sa confirmation est écarté. Ollama ou
    Qdrant indisponible : 503 lisible (l'erreur du port)."""
    query = req.query.strip()
    if not query:
        raise AppError("memory_query_empty", "La recherche ne peut pas être vide.", 422)
    found = await runtime.providers.index.search(user_id, query, kinds=req.kinds or None, k=req.k)
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
