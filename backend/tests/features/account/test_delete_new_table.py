"""Une table ajoutée demain avec `user_id` est vidée par « Tout supprimer » sans retoucher le
code de `account` (comme pour l'export), et celle d'un autre compte reste."""

import httpx
from fastapi import FastAPI
from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.support.account import OTHER
from tests.support.account_delete import delete_account, me_of


async def _labels(engine: AsyncEngine, table: Table, user_id: str) -> list[str]:
    async with engine.connect() as conn:
        stmt = select(table.c.label).where(table.c.user_id == user_id).order_by(table.c.id)
        return list((await conn.execute(stmt)).scalars())


async def test_delete_new_table_needs_no_change(
    client: httpx.AsyncClient, app: FastAPI, db_engine: AsyncEngine, extra_table: Table
) -> None:
    me = me_of(app)
    async with db_engine.begin() as conn:
        for id_, owner, label in (("1", me, "a"), ("2", me, "b"), ("3", OTHER, "autrui")):
            await conn.execute(extra_table.insert().values(id=id_, user_id=owner, label=label))

    assert (await delete_account(client)).status_code == 204

    assert await _labels(db_engine, extra_table, me) == []
    assert await _labels(db_engine, extra_table, OTHER) == ["autrui"]
    async with db_engine.connect() as conn:
        total = (await conn.execute(select(func.count()).select_from(extra_table))).scalar_one()
    assert total == 1
