from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.ledger.service.ledger import last_done
from app.features.reading_stack.repository import ReadingRepository, ReadingSources
from app.features.reading_stack.service import schedule
from app.features.reading_stack.types import CollectedItem
from app.features.research.service.runtime import ResearchRuntime
from tests.features.radar.support import add_users
from tests.support.memory import FakeWebReader
from tests.support.research import fake_research_providers

NOW = datetime(2026, 11, 22, 8, tzinfo=UTC)


async def test_daily_collection_is_replayed_once_per_account(
    db_session_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    await add_users(db_session_factory, "moi")
    await add_users(db_session_factory, "autre", onboarded=False)
    async with db_session_factory() as db:
        await ReadingSources(db, "moi").add(kind="topic", label="Python", value="Python")
        await db.commit()
    called: list[str] = []

    async def collect(rt, user_id, sources, known):
        called.append(user_id)
        assert [source.value for source in sources] == ["Python"]
        return [
            CollectedItem("article", "https://example.org/python", "Python", "Résumé", "", "Test")
        ]

    async def no_key(_: str) -> None:
        return None

    rt = ResearchRuntime(
        db_session_factory, fake_research_providers(FakeWebReader()), no_key, now=lambda: NOW
    )
    monkeypatch.setattr(schedule, "collect_web", collect)
    assert await schedule.run_reading_stack(rt, NOW) == 1
    assert await schedule.run_reading_stack(rt, NOW) == 0
    assert called == ["moi"]
    async with db_session_factory() as db:
        done = await last_done(db, "moi", schedule.JOB)
        assert done is not None and done.period == "2026-11-22"
        assert await ReadingRepository(db, "moi").unread_count() == 1
        assert await ReadingRepository(db, "autre").unread_count() == 0
