"""Reflet des niveaux dans les acquis de la mémoire (D6, D88) : créé ou monté, jamais baissé,
journalisé ; lecture des niveaux des acquis par nom normalisé."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.memory import MemoryItem, MemoryWrite
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.skill_levels import acquis_levels, reflect_skill_level

Factory = async_sessionmaker[AsyncSession]
USER = "u1"


async def _items(factory: Factory) -> list[MemoryItem]:
    async with factory() as db:
        stmt = select(MemoryItem).where(MemoryItem.kind == "skill")
        return list((await db.execute(stmt)).scalars().all())


async def _writes(factory: Factory) -> list[tuple[str, str, str | None, str | None]]:
    async with factory() as db:
        rows = (await db.execute(select(MemoryWrite).order_by(MemoryWrite.created_at))).scalars()
        return [(w.action, w.author, w.session_id, w.reason) for w in rows]


async def _reflect(runtime: MemoryRuntime, title: str, level: str) -> str:
    return await reflect_skill_level(
        runtime,
        USER,
        title=title,
        level=level,  # type: ignore[arg-type]
        author="strategist",
        session_id="s1",
        reason="Programme validé",
    )


async def test_reflect_creates_then_raises_never_lowers(
    runtime: MemoryRuntime, db_session_factory: Factory
) -> None:
    created = await _reflect(runtime, "Pandas", "in_progress")
    [item] = await _items(db_session_factory)
    assert item.id == created and item.meta["level"] == "in_progress"
    assert item.created_by == "strategist" and item.session_id == "s1"
    assert await _reflect(runtime, "pandas ", "declared") == created  # même nom normalisé
    assert await _reflect(runtime, "PANDAS", "validated") == created
    [item] = await _items(db_session_factory)
    assert item.meta["level"] == "validated"
    assert await _writes(db_session_factory) == [
        ("create", "strategist", "s1", "Programme validé"),
        ("update", "strategist", "s1", "Programme validé"),
    ]


async def test_reflect_creates_above_writable_level_in_two_steps(
    runtime: MemoryRuntime, db_session_factory: Factory
) -> None:
    await _reflect(runtime, "SQL", "proven")
    [item] = await _items(db_session_factory)
    assert item.meta["level"] == "proven"
    assert [w[0] for w in await _writes(db_session_factory)] == ["create", "update"]


async def test_acquis_levels_keep_the_highest_per_name(
    runtime: MemoryRuntime, db_session_factory: Factory
) -> None:
    await _reflect(runtime, "Pandas", "in_progress")
    async with db_session_factory() as db:
        db.add(
            MemoryItem(
                user_id=USER,
                kind="skill",
                title="PANDAS",
                text="autre",
                created_by="user",
                content_hash="h-bis",
                meta={"level": "validated"},
            )
        )
        db.add(
            MemoryItem(
                user_id="autre",
                kind="skill",
                title="Rust",
                text="r",
                created_by="user",
                content_hash="h-rust",
                meta={"level": "proven"},
            )
        )
        await db.commit()
        levels = await acquis_levels(db, USER)
    assert levels == {"pandas": "validated"}


async def test_allow_lower_is_the_only_way_down(
    runtime: MemoryRuntime, db_session_factory: Factory
) -> None:
    """D101 : la rétrogradation de F9 (deux échecs de fiches) est la seule baisse admise."""
    await _reflect(runtime, "Pandas", "validated")
    await _reflect(runtime, "Pandas", "in_progress")
    [item] = await _items(db_session_factory)
    assert item.meta["level"] == "validated"  # sans `allow_lower` : jamais baissé
    await reflect_skill_level(
        runtime,
        USER,
        title="pandas",
        level="in_progress",
        author="user",
        session_id=None,
        reason="Deux échecs de suite",
        allow_lower=True,
    )
    [item] = await _items(db_session_factory)
    assert item.meta["level"] == "in_progress"
    assert (await _writes(db_session_factory))[-1] == (
        "update",
        "user",
        None,
        "Deux échecs de suite",
    )
