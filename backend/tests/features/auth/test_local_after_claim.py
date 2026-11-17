"""Revue finale 9.R (A-I1) : repasser en `AUTH_MODE=local` après « Reprendre » rend les données."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.repository import UserRepository
from app.features.auth.service import AuthService


async def test_local_mode_after_take_local_reuses_the_only_account(
    db_session: AsyncSession,
) -> None:
    users = UserRepository(db_session)
    local = await users.add_local()
    assert await users.attach_identity(local.id, "sub-1", "camille@example.org", "Camille")

    again = await AuthService(db_session).ensure_local_user()

    assert again.id == local.id  # le même espace, pas un compte vide
    assert await users.only_user() is not None


async def test_local_mode_is_idempotent_on_a_fresh_database(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    first = await service.ensure_local_user()
    assert (await service.ensure_local_user()).id == first.id


async def test_local_mode_with_several_accounts_creates_a_new_empty_space(
    db_session: AsyncSession,
) -> None:
    users = UserRepository(db_session)
    taken = await users.add_local()
    assert await users.attach_identity(taken.id, "sub-1", "camille@example.org", "Camille")
    other = await users.add_google(sub="sub-2", email="dominique@example.org", name="Dominique")

    created = await AuthService(db_session).ensure_local_user()

    assert created.id not in (taken.id, other.id)
    assert created.google_sub is None and created.email is None
