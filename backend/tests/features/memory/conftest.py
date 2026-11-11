from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import MemoryProviders
from app.db.models.memory import MemoryItem
from app.features.memory.repository import MemoryItemRepository
from app.features.memory.service.items import MemoryService
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from tests.features.memory.helpers import with_embeddings_down, with_vector_store_down

MakeItem = Callable[..., Awaitable[MemoryItem]]


@pytest.fixture
async def db(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with db_session_factory() as session:
        yield session


@pytest.fixture
def make_item(db: AsyncSession) -> MakeItem:
    """Fabrique un élément pour `user_id` ; le hash de contenu est dérivé du titre."""

    async def make(user_id: str = "u1", **fields: Any) -> MemoryItem:
        title = str(fields.pop("title", "Titre"))
        values: dict[str, Any] = {
            "kind": "lecon",
            "title": title,
            "text": f"texte de {title}",
            "created_by": "user",
            "content_hash": f"h-{user_id}-{title}",
            **fields,
        }
        return await MemoryItemRepository(db, user_id).add(**values)

    return make


# --- service mémoire : écriture, indexation, recherche -------------------------------------------


@pytest.fixture
async def runtime(
    db_session_factory: async_sessionmaker[AsyncSession], memory_providers: MemoryProviders
) -> AsyncIterator[MemoryRuntime]:
    async with memory_runtime(db_session_factory, memory_providers) as rt:
        yield rt


@pytest.fixture
def service(db: AsyncSession, runtime: MemoryRuntime) -> MemoryService:
    return MemoryService(db, "u1", runtime)


@pytest.fixture(params=["embeddings", "vector_store"])
async def service_down(
    request: pytest.FixtureRequest,
    db: AsyncSession,
    db_session_factory: async_sessionmaker[AsyncSession],
    memory_providers: MemoryProviders,
) -> AsyncIterator[MemoryService]:
    """Service dont l'indexation échoue : Ollama arrêté, puis Qdrant arrêté."""
    down = (
        with_embeddings_down(memory_providers)
        if request.param == "embeddings"
        else with_vector_store_down(memory_providers)
    )
    async with memory_runtime(db_session_factory, down) as rt:
        yield MemoryService(db, "u1", rt)
