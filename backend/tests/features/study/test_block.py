"""Bloc du jour (D103 n° 1) : tâches de lecture et de pratique dues (retards d'abord), du premier
module dont la leçon est prête, au jour local de January."""

from datetime import UTC, datetime

import httpx
from fastapi import FastAPI
from sqlalchemy import update

from app.db.models.program import Module, Task
from app.features.study.service.block import block_of_day
from tests.features.study.conftest import BLOCK, TUESDAY, Seeded, seed
from tests.features.study.support import API


async def _titles(s: Seeded, user_id: str | None = None) -> list[str] | None:
    async with s.rt.session_factory() as db:
        found = await block_of_day(db, user_id or s.user_id, TUESDAY)
    return [t.title for t in found.tasks] if found is not None else None


async def test_block_is_due_reading_and_practice_late_first(seeded: Seeded) -> None:
    assert await _titles(seeded) == BLOCK  # ni le quiz dû, ni les lectures à venir


async def test_done_tasks_leave_the_block(seeded: Seeded) -> None:
    async with seeded.rt.session_factory() as db:
        await db.execute(
            update(Task).where(Task.title == "Lire le chapitre 1").values(status="done")
        )
        await db.commit()
    assert await _titles(seeded) == BLOCK[1:]


async def test_skipped_module_has_no_block(seeded: Seeded) -> None:
    async with seeded.rt.session_factory() as db:
        await db.execute(update(Module).where(Module.id == seeded.modules[0]).values(skipped=True))
        await db.commit()
    assert await _titles(seeded) is None


async def test_block_of_another_user_is_invisible(seeded: Seeded) -> None:
    assert await _titles(seeded, "un-autre-utilisateur") is None


async def test_block_follows_the_local_day(client: httpx.AsyncClient, app: FastAPI) -> None:
    """Mardi 23 h 30 UTC : déjà mercredi à Paris, la lecture du mercredi entre au bloc."""
    s = await seed(app)
    s.at(datetime(2026, 11, 17, 23, 30, tzinfo=UTC))
    block = (await client.get(f"{API}/summary")).json()["block"]
    assert [t["title"] for t in block["tasks"]] == [*BLOCK, "Lire le chapitre 3"]
    assert block["lesson_id"] == s.lessons[0] and block["lesson_title"] == "Leçon Module Bases"
