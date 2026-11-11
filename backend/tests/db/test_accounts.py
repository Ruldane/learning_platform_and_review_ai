import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import User


async def test_users_without_email_are_allowed(db_session: AsyncSession) -> None:
    db_session.add(User(id="u1", user_id="u1", name="local"))
    db_session.add(User(id="u2", user_id="u2", name="autre"))
    await db_session.flush()


async def test_email_stays_unique_when_set(db_session: AsyncSession) -> None:
    db_session.add(User(id="u1", user_id="u1", email="a@x.test"))
    db_session.add(User(id="u2", user_id="u2", email="a@x.test"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
