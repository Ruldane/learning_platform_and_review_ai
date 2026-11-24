"""Memory explorer (4.6, D67): 2D map, statistics, JSON export. Read-only; the text in the
database is authoritative, the index only provides the map's vectors."""

from collections import defaultdict
from datetime import UTC, datetime

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models.memory import MEMORY_KINDS
from app.features.memory.repository import (
    ChunkRepository,
    DocumentRepository,
    MemoryItemRepository,
    WriteRepository,
)
from app.features.memory.schemas import (
    MapPoint,
    MapResponse,
    MemoryExport,
    MemoryWriteOut,
    StatsOut,
)
from app.features.memory.service.documents import to_document_out
from app.features.memory.service.items import to_out
from app.features.memory.service.projection import project_2d
from app.features.memory.service.runtime import MemoryRuntime

MAP_MAX_ITEMS = 2000
# Cap on vectors read for the map (≈ 4 times the reference Vectorize quota at 1,024).
MAP_MAX_VECTORS = 20_000
VECTORIZE_LIMIT = 5_000_000


async def memory_map(db: AsyncSession, user_id: str, runtime: MemoryRuntime) -> MapResponse:
    """One point per active item = mean of its vectors; at most the `MAP_MAX_ITEMS` most recent
    (`truncated`). An item without a vector (unindexed) has no point. Qdrant or Ollama
    unavailable: readable 503 (the port's error)."""
    rows = await MemoryItemRepository(db, user_id).active(limit=MAP_MAX_ITEMS + 1)
    truncated = len(rows) > MAP_MAX_ITEMS
    rows = rows[:MAP_MAX_ITEMS]
    if not rows:
        return MapResponse(points=[], method="pca", truncated=False)
    records = await runtime.providers.index.vectors(
        user_id, limit=MAP_MAX_VECTORS, item_ids=[row.id for row in rows]
    )
    by_item: defaultdict[str, list[list[float]]] = defaultdict(list)
    for record in records:
        by_item[record.payload.item_id].append(record.vector)
    placed = [row for row in rows if row.id in by_item]
    means = [np.mean(np.asarray(by_item[row.id]), axis=0).tolist() for row in placed]
    points = [
        MapPoint.model_validate(
            {"item_id": row.id, "title": row.title, "kind": row.kind, "x": x, "y": y}
        )
        for row, (x, y) in zip(placed, project_2d(means), strict=True)
    ]
    return MapResponse(points=points, method="pca", truncated=truncated)


async def memory_stats(
    db: AsyncSession, user_id: str, runtime: MemoryRuntime, settings: Settings
) -> StatsOut:
    """Counts per kind (all 6, zero included) of active items, chunks, pending decisions,
    unindexed items, last write, share of the reference Vectorize quota
    (chunks × dimension / 5,000,000), reindex state, dashboard link."""
    items = MemoryItemRepository(db, user_id)
    counts = await items.count_by_kind()
    by_kind = {kind: counts.get(kind, 0) for kind in MEMORY_KINDS}
    total_chunks = await ChunkRepository(db, user_id).count()
    last = await WriteRepository(db, user_id).last()
    dimension = settings.embedding_dimension
    return StatsOut(
        by_kind=by_kind,
        total_items=sum(by_kind.values()),
        total_chunks=total_chunks,
        pending_decisions=(await items.count_by_kind("pending")).get("decision", 0),
        unindexed_items=await items.count_unindexed(),
        last_write=None
        if last is None
        else MemoryWriteOut.model_validate(last, from_attributes=True),
        dimension=dimension,
        vectorize_limit=VECTORIZE_LIMIT,
        vectorize_share=total_chunks * dimension / VECTORIZE_LIMIT,
        reindex=runtime.jobs.reindex_state(user_id),
        dashboard_url=settings.qdrant_dashboard_url,
    )


async def memory_export(db: AsyncSession, user_id: str) -> MemoryExport:
    """Items (active and pending), documents and the full log; no vectors."""
    items = await MemoryItemRepository(db, user_id).everything()
    documents = await DocumentRepository(db, user_id).list_recent(limit=None)
    writes = await WriteRepository(db, user_id).all()
    return MemoryExport(
        version=1,
        exported_at=datetime.now(UTC),
        items=[to_out(item) for item in items],
        documents=[to_document_out(doc) for doc in documents],
        writes=[MemoryWriteOut.model_validate(w, from_attributes=True) for w in writes],
    )
