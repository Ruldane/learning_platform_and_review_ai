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
        stmt = select(MemoryItem).where(MemoryItem.kind == "acquis")
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
    created = await _reflect(runtime, "Pandas", "en_cours")
    [item] = await _items(db_session_factory)
    assert item.id == created and item.meta["level"] == "en_cours"
    assert item.created_by == "strategist" and item.session_id == "s1"
    assert await _reflect(runtime, "pandas ", "declare") == created  # même nom normalisé
    assert await _reflect(runtime, "PANDAS", "valide") == created
    [item] = await _items(db_session_factory)
    assert item.meta["level"] == "valide"
    assert await _writes(db_session_factory) == [
        ("create", "strategist", "s1", "Programme validé"),
        ("update", "strategist", "s1", "Programme validé"),
    ]


async def test_reflect_creates_above_writable_level_in_two_steps(
    runtime: MemoryRuntime, db_session_factory: Factory
) -> None:
    await _reflect(runtime, "SQL", "prouve")
    [item] = await _items(db_session_factory)
    assert item.meta["level"] == "prouve"
    assert [w[0] for w in await _writes(db_session_factory)] == ["create", "update"]


async def test_acquis_levels_keep_the_highest_per_name(
    runtime: MemoryRuntime, db_session_factory: Factory
) -> None:
    await _reflect(runtime, "Pandas", "en_cours")
    async with db_session_factory() as db:
        db.add(
            MemoryItem(
                user_id=USER,
                kind="acquis",
                title="PANDAS",
                text="autre",
                created_by="user",
                content_hash="h-bis",
                meta={"level": "valide"},
            )
        )
        db.add(
            MemoryItem(
                user_id="autre",
                kind="acquis",
                title="Rust",
                text="r",
                created_by="user",
                content_hash="h-rust",
                meta={"level": "prouve"},
            )
        )
        await db.commit()
        levels = await acquis_levels(db, USER)
    assert levels == {"pandas": "valide"}
