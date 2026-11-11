from datetime import UTC

from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin
from app.db.repository import UserScopedRepository


class ItemRow(UserScopedMixin, Base):
    __tablename__ = "test_items"

    label: Mapped[str] = mapped_column(String(50))


class ItemRepo(UserScopedRepository[ItemRow]):
    model = ItemRow


async def test_add_sets_user_and_ids(db_session: AsyncSession) -> None:
    repo = ItemRepo(db_session, "u1")
    item = await repo.add(label="a")
    assert item.user_id == "u1" and len(item.id) == 36 and item.created_at.tzinfo is not None


async def test_other_user_cannot_read_update_or_delete(db_session: AsyncSession) -> None:
    item = await ItemRepo(db_session, "u1").add(label="a")
    other = ItemRepo(db_session, "u2")
    assert await other.get(item.id) is None
    assert await other.list() == []
    assert await other.update(item.id, label="b") is None
    assert await other.delete(item.id) is False
    found = await ItemRepo(db_session, "u1").get(item.id)
    assert found is not None and found.label == "a"


async def test_add_ignores_user_id_passed_in_fields(db_session: AsyncSession) -> None:
    item = await ItemRepo(db_session, "u1").add(label="a", user_id="u2")
    assert item.user_id == "u1"


async def test_list_filters(db_session: AsyncSession) -> None:
    repo = ItemRepo(db_session, "u1")
    await repo.add(label="a")
    await repo.add(label="b")
    assert [i.label for i in await repo.list(label="b")] == ["b"]


async def test_update_and_delete_by_owner(db_session: AsyncSession) -> None:
    repo = ItemRepo(db_session, "u1")
    item = await repo.add(label="a")
    created = item.created_at
    updated = await repo.update(item.id, label="b", user_id="u2")
    assert updated is not None and updated.label == "b" and updated.user_id == "u1"
    assert updated.created_at == created
    assert await repo.delete(item.id) is True
    assert await repo.get(item.id) is None


async def test_timestamps_stay_timezone_aware_when_read_back(db_session: AsyncSession) -> None:
    item_id = (await ItemRepo(db_session, "u1").add(label="a")).id
    db_session.expire_all()
    reloaded = await ItemRepo(db_session, "u1").get(item_id)
    assert reloaded is not None
    assert reloaded.created_at.tzinfo is not None
    assert reloaded.created_at.utcoffset() == UTC.utcoffset(None)


async def test_updated_at_changes_on_write(db_session: AsyncSession) -> None:
    repo = ItemRepo(db_session, "u1")
    item = await repo.add(label="a")
    before = item.updated_at
    updated = await repo.update(item.id, label="b")
    assert updated is not None and updated.updated_at > before
