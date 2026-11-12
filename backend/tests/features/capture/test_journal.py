"""Journal (F18) : un seul écrivain, idempotent par `ref_key`."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.study import JournalEntry
from app.features.capture.service.journal import JournalLinks, add_entry

DAY = date(2026, 11, 12)


async def _count(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count()).select_from(JournalEntry))).scalar_one())


async def test_add_entry_is_idempotent_by_ref_key(db_session: AsyncSession) -> None:
    first = await add_entry(
        db_session,
        "u1",
        kind="weekly_review",
        text="Bilan",
        occurred_on=DAY,
        ref_key="wr:2026-11-09",
    )
    again = await add_entry(
        db_session,
        "u1",
        kind="weekly_review",
        text="Autre",
        occurred_on=DAY,
        ref_key="wr:2026-11-09",
    )
    assert first == again and await _count(db_session) == 1
    row = (await db_session.execute(select(JournalEntry))).scalar_one()
    assert row.text == "Bilan"  # la première écriture gagne


async def test_add_entry_without_ref_key_always_inserts(db_session: AsyncSession) -> None:
    a = await add_entry(db_session, "u1", kind="capture", text="a", occurred_on=DAY, ref_key=None)
    b = await add_entry(db_session, "u1", kind="capture", text="a", occurred_on=DAY, ref_key=None)
    assert a != b and await _count(db_session) == 2


async def test_ref_key_is_per_user(db_session: AsyncSession) -> None:
    a = await add_entry(db_session, "u1", kind="quiz", text="a", occurred_on=DAY, ref_key="k")
    b = await add_entry(db_session, "u2", kind="quiz", text="b", occurred_on=DAY, ref_key="k")
    assert a != b and await _count(db_session) == 2


async def test_links_and_data_are_stored(db_session: AsyncSession) -> None:
    links = JournalLinks(session_id="s1", study_session_id="ss1", quiz_attempt_id="qa1")
    entry_id = await add_entry(
        db_session,
        "u1",
        kind="study_session",
        text="Session",
        occurred_on=DAY,
        ref_key="ss1",
        links=links,
        data={"minutes": 50},
    )
    row = (await db_session.execute(select(JournalEntry))).scalar_one()
    assert row.id == entry_id and row.user_id == "u1" and row.kind == "study_session"
    assert (row.session_id, row.study_session_id, row.quiz_attempt_id) == ("s1", "ss1", "qa1")
    assert row.memory_item_id is None and row.data == {"minutes": 50}
    assert row.occurred_on == DAY and row.created_at is not None


async def test_default_data_is_empty(db_session: AsyncSession) -> None:
    await add_entry(db_session, "u1", kind="capture", text="a", occurred_on=DAY, ref_key=None)
    assert (await db_session.execute(select(JournalEntry))).scalar_one().data == {}
