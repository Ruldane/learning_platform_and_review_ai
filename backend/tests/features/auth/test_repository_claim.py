from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.repository import UserRepository


async def test_attach_identity_is_conditional(db_session: AsyncSession) -> None:
    users = UserRepository(db_session)
    local = await users.add_local()
    other = await users.add_local()  # une seconde ligne sans identité (cas anormal)
    assert not await users.any_google_user()
    assert await users.attach_identity(local.id, "sub-1", "a@example.org", "A")
    assert await users.any_google_user()
    assert (local.google_sub, local.email, local.name) == ("sub-1", "a@example.org", "A")
    # Plus de reprise : la ligne a un propriétaire, et un compte Google existe déjà.
    assert not await users.attach_identity(local.id, "sub-2", "b@example.org", "B")
    assert not await users.attach_identity(other.id, "sub-2", "b@example.org", "B")
    assert other.google_sub is None
