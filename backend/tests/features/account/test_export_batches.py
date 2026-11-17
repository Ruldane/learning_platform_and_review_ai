"""L'export lit les tables par lots (mémoire bornée) et ne casse jamais sur un type non JSON."""

import base64
import uuid
from collections.abc import AsyncIterator, Sequence
from datetime import timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import Column, LargeBinary, Numeric, String, Table
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db.base import Base
from app.db.models.agents import LlmCall
from app.features.account.repository import AccountRepository
from app.features.account.service import export as export_module
from app.features.account.service.tables import row_json
from tests.support.account import export_archive, seed_user


async def _calls(db: AsyncSession, user_id: str, count: int) -> None:
    db.add_all(
        LlmCall(user_id=user_id, provider="glm", model=f"modele-{n:03d}", cost_usd=0.01)
        for n in range(count)
    )
    await db.commit()


async def test_batches_never_exceed_the_batch_size(db_session: AsyncSession) -> None:
    await _calls(db_session, "u1", 25)
    await _calls(db_session, "u2", 5)
    table = Base.metadata.tables["llm_calls"]

    batches = [b async for b in AccountRepository(db_session, "u1").batches(table, None, 10)]

    assert [len(b) for b in batches] == [10, 10, 5]
    assert {row["user_id"] for batch in batches for row in batch} == {"u1"}
    flat = [row["model"] for batch in batches for row in batch]
    assert sorted(flat) == [f"modele-{n:03d}" for n in range(25)] and len(set(flat)) == 25


async def test_batches_read_only_the_given_columns(db_session: AsyncSession) -> None:
    await _calls(db_session, "u1", 3)
    table = Base.metadata.tables["llm_calls"]
    columns = [table.c.id, table.c.model]
    [batch] = [b async for b in AccountRepository(db_session, "u1").batches(table, columns, 10)]
    assert all(set(row) == {"id", "model"} for row in batch)


async def test_an_empty_table_gives_no_batch_and_no_row(db_session: AsyncSession) -> None:
    table = Base.metadata.tables["goals"]
    assert [b async for b in AccountRepository(db_session, "u1").batches(table, None, 10)] == []
    assert await AccountRepository(db_session, "u1").rows(table) == []


async def test_export_reads_each_table_in_several_batches(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    me: str = app.state.local_user_id
    await seed_user(db_session, me, "moi", "jeton")
    await _calls(db_session, me, 24)  # 25 avec celui de `seed_user`
    sizes: dict[str, list[int]] = {}
    real = AccountRepository.batches

    async def spy(
        self: AccountRepository, table: Table, columns: Sequence[Any] | None, size: int
    ) -> AsyncIterator[list[dict[str, Any]]]:
        async for batch in real(self, table, columns, size):
            sizes.setdefault(table.name, []).append(len(batch))
            yield batch

    monkeypatch.setattr(AccountRepository, "batches", spy)
    monkeypatch.setattr(export_module, "BATCH_ROWS", 10)

    archive = await export_archive(client)

    assert sizes["llm_calls"] == [10, 10, 5]
    assert max(max(lengths) for lengths in sizes.values()) <= 10
    rows = archive.table("llm_calls")
    assert len(rows) == 25 and len({row["id"] for row in rows}) == 25
    assert archive.manifest["tables"]["llm_calls"] == 25
    assert [r["created_at"] for r in rows] == sorted(r["created_at"] for r in rows)


async def test_the_default_batch_is_a_few_hundred_rows() -> None:
    assert 100 <= export_module.BATCH_ROWS <= 1000


# --- Types que JSON ne connaît pas ------------------------------------------------------------


def test_row_json_makes_every_value_json_safe() -> None:
    ident = uuid.UUID("0b8a7c1e-4c4e-4a4f-9a7e-2f0d7e0c1a2b")
    row = {
        "raw": b"\x00\xffabc",
        "price": Decimal("12.50"),
        "ident": ident,
        "span": timedelta(minutes=2, seconds=30),
        "tags": {"b"},
        "view": memoryview(b"xy"),
    }
    assert row_json(row) == {
        "raw": base64.b64encode(b"\x00\xffabc").decode(),
        "price": "12.50",
        "ident": str(ident),
        "span": 150.0,
        "tags": ["b"],
        "view": base64.b64encode(b"xy").decode(),
    }


@pytest.fixture
async def odd_table(db_engine: AsyncEngine) -> AsyncIterator[Table]:
    table = Table(
        "odd_things",
        Base.metadata,
        Column("id", String(36), primary_key=True),
        Column("user_id", String(36)),
        Column("blob", LargeBinary),
        Column("price", Numeric(10, 2)),
    )
    async with db_engine.begin() as conn:
        await conn.run_sync(table.create)
    yield table
    async with db_engine.begin() as conn:
        await conn.run_sync(table.drop)
    Base.metadata.remove(table)


async def test_export_survives_a_table_with_binary_and_decimal_columns(
    client: httpx.AsyncClient, app: FastAPI, db_engine: AsyncEngine, odd_table: Table
) -> None:
    me: str = app.state.local_user_id
    async with db_engine.begin() as conn:
        await conn.execute(
            odd_table.insert().values(id="1", user_id=me, blob=b"\x00\x01", price=Decimal("3.10"))
        )
    archive = await export_archive(client)
    [row] = archive.table("odd_things")
    assert row["blob"] == base64.b64encode(b"\x00\x01").decode() and row["price"] == "3.10"
