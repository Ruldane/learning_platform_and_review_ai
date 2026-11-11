"""Aller-retour contre un vrai Qdrant : marqué `live`, désélectionné par défaut (`-m 'not live'`).

Lancer avec : `QDRANT_URL=http://localhost:6333 uv run python -m pytest -m live`.
"""

import os
import uuid

import pytest
from qdrant_client import AsyncQdrantClient

from app.providers.embeddings.fake import HashingEmbedder
from app.providers.vector.qdrant import QdrantMemoryRepository
from tests.support.memory import make_chunk

pytestmark = pytest.mark.live


async def test_qdrant_roundtrip_live() -> None:
    url = os.environ.get("QDRANT_URL")
    if not url:
        pytest.skip("QDRANT_URL n'est pas définie")
    name = f"tremplin_test_{uuid.uuid4().hex}"
    client = AsyncQdrantClient(url=url, timeout=10)
    try:
        repo = QdrantMemoryRepository(client, HashingEmbedder(16), collection=name, dimension=16)
        mine = make_chunk("A", "attention multi têtes")
        await repo.index([mine, make_chunk("B", "attention multi têtes")])
        hits = await repo.search("A", "attention")
        assert [h.chunk_id for h in hits] == [mine.chunk_id]
        assert len(await repo.vectors("A", limit=10)) == 1
        await repo.delete_items("A", [mine.payload.item_id])
        assert await repo.search("A", "attention") == []
    finally:
        await client.delete_collection(name)
        await client.close()
