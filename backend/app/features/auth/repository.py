from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.base import new_id
from app.db.models.accounts import LOCAL_CLAIM_CLOSED, User, UserSettingsRow

LOCAL_USER_NAME = "local"


class UserRepository:
    """Access to the `users` table.

    Documented exception to filtering by `user_id` (DECISIONS D23): this is the table of
    accounts, filtered by `id`. It does not inherit `UserScopedRepository`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)

    async def get_local(self) -> User | None:
        """Local account: no email or Google identifier, named `local`."""
        stmt = select(User).where(
            User.name == LOCAL_USER_NAME, User.email.is_(None), User.google_sub.is_(None)
        )
        return (await self._session.execute(stmt.limit(1))).scalar_one_or_none()

    async def only_user(self) -> User | None:
        """The account, if there is only one in `users` (otherwise `None`)."""
        rows = list((await self._session.execute(select(User).limit(2))).scalars())
        return rows[0] if len(rows) == 1 else None

    async def add_local(self) -> User:
        user_id = new_id()
        user = User(id=user_id, user_id=user_id, name=LOCAL_USER_NAME)  # convention user_id == id
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_google_sub(self, sub: str) -> User | None:
        stmt = select(User).where(User.google_sub == sub)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_google(self, *, sub: str, email: str, name: str) -> User:
        user_id = new_id()
        user = User(id=user_id, user_id=user_id, google_sub=sub, email=email, name=name)
        self._session.add(user)
        await self._session.flush()
        return user

    async def update_identity(self, user: User, *, email: str, name: str) -> None:
        user.email = email
        user.name = name
        await self._session.flush()

    async def any_google_user(self) -> bool:
        """True as soon as a Google account exists (no more taking over the local space)."""
        stmt = select(User.id).where(User.google_sub.is_not(None)).limit(1)
        return (await self._session.execute(stmt)).first() is not None

    async def local_claim_closed(self, local_id: str) -> bool:
        """True if taking over the local space is closed (settings of the `local` row)."""
        stmt = select(UserSettingsRow.id).where(
            UserSettingsRow.user_id == local_id,
            func.coalesce(func.json_extract(UserSettingsRow.data, f"$.{LOCAL_CLAIM_CLOSED}"), 0)
            == 1,
        )
        return (await self._session.execute(stmt.limit(1))).first() is not None

    async def attach_identity(self, user_id: str, sub: str, email: str, name: str) -> bool:
        """Attaches the Google identity to the `user_id` row (taking over the local space: same
        `id`, so no data moves). A single conditional UPDATE, so atomic: it only touches the row
        if it has no identity yet AND no Google account exists (two simultaneous takeovers, a
        takeover after a first "empty space" choice, or a closed takeover, even if the Google
        account has been deleted since: 0 rows, `False`). Never two owners."""
        other = aliased(User)
        taken = select(other.id).where(other.google_sub.is_not(None)).exists()
        closed = (
            select(UserSettingsRow.id)
            .where(
                UserSettingsRow.user_id == user_id,
                func.coalesce(func.json_extract(UserSettingsRow.data, f"$.{LOCAL_CLAIM_CLOSED}"), 0)
                == 1,
            )
            .exists()
        )
        stmt = (
            update(User)
            .where(User.id == user_id, User.google_sub.is_(None), ~taken, ~closed)
            .values(google_sub=sub, email=email, name=name)
            .execution_options(synchronize_session=False)
        )
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        if result.rowcount != 1:
            return False
        row = await self._session.get(User, user_id)
        if row is not None:  # the object already loaded reflects the row written
            await self._session.refresh(row)
        return True
