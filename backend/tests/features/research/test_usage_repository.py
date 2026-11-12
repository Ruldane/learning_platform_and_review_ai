import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.research import SearchUsage
from app.features.research.repository import SearchUsageRepository, month_total


async def _seed(db: AsyncSession, user_id: str, count: int, fingerprint: str = "fp1") -> None:
    db.add(
        SearchUsage(
            user_id=user_id,
            provider="brave",
            month="2026-11",
            key_fingerprint=fingerprint,
            count=count,
        )
    )
    await db.commit()


async def _total(db: AsyncSession, fingerprint: str = "fp1") -> int:
    return await month_total(db, provider="brave", month="2026-11", fingerprint=fingerprint)


async def test_reserve_counts_until_cap_for_all_users_of_a_key(db: AsyncSession) -> None:
    await _seed(db, "u0", 2)
    assert await SearchUsageRepository(db, "u1").reserve("brave", "2026-11", "fp1", 4)
    assert await SearchUsageRepository(db, "u2").reserve("brave", "2026-11", "fp1", 4)
    assert await _total(db) == 4
    assert not await SearchUsageRepository(db, "u1").reserve("brave", "2026-11", "fp1", 4)
    assert not await SearchUsageRepository(db, "u3").reserve("brave", "2026-11", "fp1", 4)
    assert await _total(db) == 4
    # Une autre clé, un autre mois : compteurs séparés.
    assert await SearchUsageRepository(db, "u1").reserve("brave", "2026-11", "fp2", 4)
    assert await SearchUsageRepository(db, "u1").reserve("brave", "2026-12", "fp1", 4)
    assert await _total(db, "fp2") == 1


async def test_reserve_is_atomic_across_connections_without_any_lock(
    db_session_factory: async_sessionmaker[AsyncSession], db: AsyncSession
) -> None:
    # Cinq connexions distinctes, aucun verrou asyncio : seule l'instruction gardée protège le
    # plafond (comme deux processus).
    await _seed(db, "u0", 899)

    async def one(user_id: str) -> bool:
        async with db_session_factory() as session:
            reserved = await SearchUsageRepository(session, user_id).reserve(
                "brave", "2026-11", "fp1", 900
            )
            await asyncio.sleep(0)
            await session.commit()
            return reserved

    outcomes = await asyncio.gather(*(one(f"u{i % 2}") for i in range(5)))
    assert sorted(outcomes) == [False, False, False, False, True]
    assert await _total(db) == 900
