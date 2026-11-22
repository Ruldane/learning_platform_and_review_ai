from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reading_stack.repository import ReadingRepository
from app.features.reading_stack.types import CollectedItem

NOW = datetime(2026, 11, 22, 8, tzinfo=UTC)
ARTICLE = CollectedItem(
    kind="article",
    url="https://example.org/python",
    title="Python",
    summary="Un article.",
    text="Le texte de l’article.",
    reason="Sujet suivi",
)


@pytest.mark.asyncio
async def test_collection_replay_preserves_the_read_state_and_scopes_items(
    db_session: AsyncSession,
) -> None:
    mine = ReadingRepository(db_session, "moi")
    other = ReadingRepository(db_session, "autre")
    item_id = await mine.record(ARTICLE, NOW)
    assert item_id is not None
    assert await mine.unread_count() == 1
    await mine.mark_read(item_id, True, NOW)

    assert await mine.record(ARTICLE, NOW) is None
    assert await mine.unread_count() == 0
    [article] = await mine.items(unread=False)
    assert article.id == item_id
    assert article.read_at == NOW
    assert await mine.items(unread=True) == []
    assert await other.get(item_id) is None
    assert await other.mark_read(item_id, False, NOW) is None
    assert await other.record(ARTICLE, NOW) != item_id
