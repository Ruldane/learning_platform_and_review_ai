import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, String, and_, case, exists, func, literal, or_, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.db.base import new_id
from app.db.models.accounts import LOCAL_CLAIM_CLOSED, ApiKey, User, UserSettingsRow
from app.db.models.agents import LlmCall
from app.db.models.learning import Goal
from app.db.repository import UserScopedRepository


def _prior_data(user_id: InstrumentedAttribute[str] | str) -> ColumnElement[bool]:
    """The account already has an API key, a goal or a model call (D183): a single
    definition, for one account (`has_prior_data`) as for all (`onboarded_user_ids`)."""
    key = select(ApiKey.id).where(ApiKey.user_id == user_id)
    goal = select(Goal.id).where(Goal.user_id == user_id)
    call = select(LlmCall.id).where(LlmCall.user_id == user_id)
    return or_(exists(key), exists(goal), exists(call))


async def onboarded_user_ids(session: AsyncSession) -> list[str]:
    """The accounts whose first run is done, **the same rule as `GET /settings`**
    (`SettingsService.get`, D183): with a settings row, its `onboarding_done` key is true;
    without a row, the account is done if it already has data (`_prior_data`). The ONLY read of
    settings without `user_id` (like D18, D91), reserved for scheduled jobs; reads identifiers
    only and writes nothing."""
    mine = UserSettingsRow.user_id == User.id
    done = exists(
        select(UserSettingsRow.id).where(
            mine,
            func.coalesce(func.json_extract(UserSettingsRow.data, "$.onboarding_done"), 0) == 1,
        )
    )
    has_row = exists(select(UserSettingsRow.id).where(mine))
    stmt = (
        select(User.id)
        .where(or_(done, and_(~has_row, _prior_data(User.id))))
        .order_by(User.created_at, User.id)
    )
    return list((await session.execute(stmt)).scalars())


class UserSettingsRepository(UserScopedRepository[UserSettingsRow]):
    """A single `user_settings` row per user (uniqueness constraint on `user_id`)."""

    model = UserSettingsRow

    async def _row(self) -> UserSettingsRow | None:
        rows = await self.list()
        return rows[0] if rows else None

    async def get_data(self) -> dict[str, Any] | None:
        row = await self._row()
        return row.data if row is not None else None

    async def save_data(self, data: dict[str, Any]) -> None:
        """Replaces the settings. If `data` carries `onboarding_done`, it is written
        **monotonically**, in the query itself: `onboarding_done = onboarding_done OR :new`. A
        request that read `false` before another one committed `true` therefore never undoes it
        (P20). The reserved key `local_claim_closed` survives every replacement (it is not a
        setting)."""
        row = await self._row()
        if row is not None and row.data.get(LOCAL_CLAIM_CLOSED) is True:
            data = {**data, LOCAL_CLAIM_CLOSED: True}
        if row is None:
            await self.add(data=dict(data))
        elif "onboarding_done" not in data:
            # The JSON column is not tracked deeply: always assign a new dict.
            await self.update(row.id, data=dict(data))
        else:
            was_done = func.coalesce(
                func.json_extract(UserSettingsRow.data, "$.onboarding_done"), 0
            )
            done = case(
                (or_(was_done == 1, literal(bool(data["onboarding_done"]))), "true"), else_="false"
            )
            merged = func.json_set(
                literal(json.dumps(data), String), "$.onboarding_done", func.json(done)
            )
            stmt = update(UserSettingsRow).where(
                UserSettingsRow.id == row.id, UserSettingsRow.user_id == self.user_id
            )
            await self.session.execute(
                stmt.values(data=merged, updated_at=datetime.now(UTC)),
                execution_options={"synchronize_session": False},
            )
            await self.session.refresh(row)

    async def close_local_claim(self) -> None:
        """Sets the reserved key `local_claim_closed` (idempotent), creating the settings row if
        needed with the same `onboarding_done` as a first access (D183)."""
        await self.initialize({"onboarding_done": await self.has_prior_data()})
        stmt = update(UserSettingsRow).where(UserSettingsRow.user_id == self.user_id)
        flag = func.json_set(UserSettingsRow.data, f"$.{LOCAL_CLAIM_CLOSED}", func.json("true"))
        await self.session.execute(
            stmt.values(data=flag), execution_options={"synchronize_session": False}
        )

    async def has_prior_data(self) -> bool:
        """True if the account already has a saved API key, a goal or a model call (key only in
        `.env`): it has already used the app, it has no first run to do (P20)."""
        found = await self.session.execute(select(_prior_data(self.user_id)))
        return bool(found.scalar())

    async def initialize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Creates the row if it does not exist yet, without ever overwriting the one a
        concurrent request has just created (a single `INSERT` wins, the other does nothing);
        returns the data that is in the database."""
        now = datetime.now(UTC)
        stmt = insert(UserSettingsRow).values(
            id=new_id(), user_id=self.user_id, data=dict(data), created_at=now, updated_at=now
        )
        await self.session.execute(stmt.on_conflict_do_nothing(index_elements=["user_id"]))
        # Read the column only: the ORM must not keep a row written outside of it.
        read = select(UserSettingsRow.data).where(UserSettingsRow.user_id == self.user_id)
        stored = (await self.session.execute(read)).scalar_one_or_none()
        return stored if isinstance(stored, dict) else dict(data)
