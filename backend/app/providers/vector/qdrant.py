"""`MemoryRepository` sur Qdrant (`qdrant-client`, API asynchrone).

Une seule collection ; l'id d'un point est le `chunk_id`. CHAQUE requête porte la condition
`user_id` : aucune lecture ni suppression ne sort du périmètre d'un utilisateur. Les erreurs du
client deviennent `VectorStoreUnavailable` (jamais le texte de l'exception)."""

import asyncio
import logging
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import asdict

import httpx
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from app.providers.embeddings.base import Embedder
from app.providers.vector.base import (
    DEFAULT_K,
    ChunkPayload,
    ChunkToIndex,
    VectorHit,
    VectorRecord,
    VectorStoreUnavailable,
)

logger = logging.getLogger(__name__)

_INDEXED_FIELDS = ("user_id", "kind", "item_id")
_SCROLL_PAGE = 256
_CLIENT_ERRORS = (httpx.HTTPError, UnexpectedResponse, ResponseHandlingException)


@asynccontextmanager
async def _store_errors() -> AsyncIterator[None]:
    try:
        yield
    except _CLIENT_ERRORS as exc:
        logger.warning("Qdrant indisponible : %s", type(exc).__name__)
        raise VectorStoreUnavailable() from None


def _match(key: str, value: str) -> models.FieldCondition:
    return models.FieldCondition(key=key, match=models.MatchValue(value=value))


def _user_filter(
    user_id: str,
    *extra: models.Condition,
    must_not: list[models.Condition] | None = None,
) -> models.Filter:
    return models.Filter(must=[_match("user_id", user_id), *extra], must_not=must_not)


def _payload(raw: dict[str, object] | None) -> ChunkPayload | None:
    if raw is None:
        return None
    try:
        return ChunkPayload(**raw)  # type: ignore[arg-type]
    except TypeError:  # point écrit par autre chose que ce dépôt : ignoré
        return None


def _dense(vector: object) -> list[float] | None:
    """Le vecteur d'un point s'il est dense et unique (collection anonyme), sinon `None`."""
    if isinstance(vector, list) and all(isinstance(x, int | float) for x in vector):
        return [float(x) for x in vector]
    return None


class QdrantMemoryRepository:
    def __init__(
        self, client: AsyncQdrantClient, embedder: Embedder, *, collection: str, dimension: int
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection = collection
        self._dimension = dimension
        self._ready = False
        self._lock = asyncio.Lock()

    async def _ensure_collection(self) -> None:
        """Créée à la première utilisation : le back démarre même si Qdrant est arrêté."""
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return
            if not await self._client.collection_exists(self._collection):
                await self._client.create_collection(
                    self._collection,
                    vectors_config=models.VectorParams(
                        size=self._dimension, distance=models.Distance.COSINE
                    ),
                )
            for field in _INDEXED_FIELDS:  # idempotent côté serveur
                await self._client.create_payload_index(
                    self._collection, field, models.PayloadSchemaType.KEYWORD
                )
            self._ready = True

    async def index(self, chunks: Sequence[ChunkToIndex]) -> None:
        if not chunks:
            return
        vectors = await self._embedder.aembed_documents([c.payload.text for c in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("un vecteur par fragment attendu")
        points = [
            models.PointStruct(id=c.chunk_id, vector=vector, payload=asdict(c.payload))
            for c, vector in zip(chunks, vectors, strict=True)
        ]
        async with _store_errors():
            await self._ensure_collection()
            await self._client.upsert(self._collection, points=points, wait=True)

    async def search(
        self, user_id: str, query: str, *, kinds: Sequence[str] | None = None, k: int = DEFAULT_K
    ) -> list[VectorHit]:
        vector = await self._embedder.aembed_query(query)
        # Aucun type demandé : tous les types (un filtre vide ne renverrait jamais rien).
        by_kind: list[models.Condition] = (
            [models.FieldCondition(key="kind", match=models.MatchAny(any=list(kinds)))]
            if kinds
            else []
        )
        async with _store_errors():
            await self._ensure_collection()
            return await self._nearest(_user_filter(user_id, *by_kind), vector, k)

    async def similar(
        self, user_id: str, chunk_id: str, *, k: int, exclude_item_id: str | None = None
    ) -> list[VectorHit]:
        itself = models.HasIdCondition(has_id=[chunk_id])
        async with _store_errors():
            await self._ensure_collection()
            # Vecteur lu sous le filtre `user_id` : l'id d'un autre utilisateur ne donne rien.
            found, _ = await self._client.scroll(
                self._collection,
                scroll_filter=_user_filter(user_id, itself),
                limit=1,
                with_vectors=True,
            )
            vector = _dense(found[0].vector) if found else None
            if vector is None:
                return []
            exclude: list[models.Condition] = [itself]
            if exclude_item_id is not None:
                exclude.append(_match("item_id", exclude_item_id))
            return await self._nearest(_user_filter(user_id, must_not=exclude), vector, k)

    async def _nearest(
        self, query_filter: models.Filter, vector: list[float], k: int
    ) -> list[VectorHit]:
        response = await self._client.query_points(
            self._collection,
            query=vector,
            query_filter=query_filter,
            limit=k,
            with_payload=True,
        )
        hits: list[VectorHit] = []
        for point in response.points:
            payload = _payload(point.payload)
            if payload is not None:
                hits.append(VectorHit(str(point.id), point.score, payload))
        return hits

    async def delete_items(self, user_id: str, item_ids: Sequence[str]) -> None:
        if not item_ids:
            return
        by_item = models.FieldCondition(key="item_id", match=models.MatchAny(any=list(item_ids)))
        await self._delete(_user_filter(user_id, by_item))

    async def delete_user(self, user_id: str) -> None:
        await self._delete(_user_filter(user_id))

    async def _delete(self, selector: models.Filter) -> None:
        async with _store_errors():
            await self._ensure_collection()
            await self._client.delete(
                self._collection, points_selector=models.FilterSelector(filter=selector), wait=True
            )

    async def vectors(
        self, user_id: str, *, limit: int, item_ids: Sequence[str] | None = None
    ) -> list[VectorRecord]:
        by_item: list[models.Condition] = (
            [models.FieldCondition(key="item_id", match=models.MatchAny(any=list(item_ids)))]
            if item_ids is not None
            else []
        )
        records: list[VectorRecord] = []
        offset: models.ExtendedPointId | None = None
        async with _store_errors():
            await self._ensure_collection()
            while len(records) < limit:
                page, offset = await self._client.scroll(
                    self._collection,
                    scroll_filter=_user_filter(user_id, *by_item),
                    limit=min(_SCROLL_PAGE, limit - len(records)),
                    offset=offset,
                    with_vectors=True,
                )
                for point in page:
                    payload, vector = _payload(point.payload), _dense(point.vector)
                    if payload is not None and vector is not None:
                        records.append(VectorRecord(str(point.id), vector, payload))
                if offset is None:
                    break
        return records
