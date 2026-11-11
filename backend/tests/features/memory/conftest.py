from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.memory import MemoryItem
from app.features.memory.repository import MemoryItemRepository

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
