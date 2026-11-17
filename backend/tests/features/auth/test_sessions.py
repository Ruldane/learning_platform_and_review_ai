import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.accounts import AuthSession
from app.features.auth.repository_sessions import AuthSessionRepository
from app.features.auth.service.allowlist import allowed, entries
from app.features.auth.service.sessions import close_session, hash_token, open_session

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)


async def rows(db: AsyncSession) -> list[AuthSession]:
    return list((await db.execute(select(AuthSession))).scalars())


async def test_open_session_stores_the_hash_and_a_fixed_expiry(db_session: AsyncSession) -> None:
    token = await open_session(db_session, "u1", now=NOW, days=30)
    assert len(token) >= 43  # 32 octets aléatoires, en base 64
    (row,) = await rows(db_session)
    assert row.token_hash == hashlib.sha256(token.encode()).hexdigest() == hash_token(token)
    assert row.user_id == "u1" and row.expires_at == NOW + timedelta(days=30)
    assert token not in {row.token_hash, row.user_id, row.id}


async def test_tokens_are_never_repeated(db_session: AsyncSession) -> None:
    tokens = {await open_session(db_session, "u1", now=NOW, days=1) for _ in range(20)}
    assert len(tokens) == 20


async def test_open_session_purges_only_the_expired_sessions_of_that_user(
    db_session: AsyncSession,
) -> None:
    repo = AuthSessionRepository(db_session)
    await repo.add("u1", "old-u1", NOW - timedelta(seconds=1))
    await repo.add("u1", "live-u1", NOW + timedelta(hours=1))
    await repo.add("u2", "old-u2", NOW - timedelta(days=9))
    await open_session(db_session, "u1", now=NOW, days=30)
    hashes = {row.token_hash for row in await rows(db_session)}
    assert "old-u1" not in hashes and {"live-u1", "old-u2"} <= hashes and len(hashes) == 3


async def test_get_valid_refuses_an_expired_or_unknown_session(db_session: AsyncSession) -> None:
    repo = AuthSessionRepository(db_session)
    await repo.add("u1", "h-live", NOW + timedelta(seconds=1))
    await repo.add("u1", "h-dead", NOW)
    assert (await repo.get_valid("h-live", NOW)) is not None
    assert await repo.get_valid("h-dead", NOW) is None  # expirée à l'instant même
    assert await repo.get_valid("h-nobody", NOW) is None


async def test_close_session_removes_that_session_only(db_session: AsyncSession) -> None:
    first = await open_session(db_session, "u1", now=NOW, days=30)
    second = await open_session(db_session, "u1", now=NOW, days=30)
    await close_session(db_session, first)
    await close_session(db_session, "not-a-token")  # sans effet
    assert [row.token_hash for row in await rows(db_session)] == [hash_token(second)]


def test_allowlist_is_lowercase_and_trimmed() -> None:
    assert entries(" A@Example.org ,, b@example.org ") == {"a@example.org", "b@example.org"}
    assert allowed("A@EXAMPLE.org", "a@example.org, b@example.org")
    assert not allowed("c@example.org", "a@example.org,b@example.org")


def test_allowlist_star_accepts_everyone_and_empty_nobody() -> None:
    assert allowed("anyone@example.invalid", "*") and allowed("x@y.z", " * ")
    assert not allowed("a@example.org", "") and not allowed("a@example.org", None)
    assert not allowed("a@example.org", " , ")


def test_allowlist_matches_whole_addresses_only() -> None:
    assert not allowed("camille@example.org", "camille@example.org.evil.invalid")
    assert not allowed("xcamille@example.org", "camille@example.org")


async def test_sessions_survive_a_session_factory_roundtrip(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with db_session_factory() as db:
        token = await open_session(db, "u1", now=NOW, days=2)
        await db.commit()
    async with db_session_factory() as db:
        found = await AuthSessionRepository(db).get_valid(hash_token(token), NOW)
        assert found is not None and found.expires_at == NOW + timedelta(days=2)
