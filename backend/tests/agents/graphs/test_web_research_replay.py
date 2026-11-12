"""`judge` coupé en plein nœud puis repris par le runner (D82, reliquat de la phase 3) : les pages
déjà notées ne repassent pas par le modèle, leur verdict est réémis à l'identique et la mémoire
n'est écrite qu'une fois."""

import asyncio
from typing import Any

from app.features.memory.repository import ItemFilter, MemoryItemRepository
from app.features.research.repository import SourceRepository
from tests.agents.graphs.web_support import (
    PLAN,
    SCORE_41,
    SCORE_82,
    URL_A,
    URL_B,
    GatedModels,
    MakeWeb,
    Web,
    script_web,
)
from tests.agents.runtime.runner_helpers import all_events, wait_status, wait_until


async def _verdict(web: Web, user_id: str, sid: str, url: str) -> str | None:
    async with web.factory() as db:
        rows = await SourceRepository(db, user_id).list_for_session(sid)
    return next((r.verdict for r in rows if r.url == url), None)


async def _found(web: Web, user_id: str, sid: str, url: str) -> list[dict[str, Any]]:
    events = await all_events(web.factory, user_id, sid)
    return [
        e.payload.model_dump()
        for e in events
        if e.type == "source.found" and e.payload.url == url  # type: ignore[union-attr]
    ]


async def test_judge_stopped_midway_does_not_rescore_judged_pages(
    make_web_runner: MakeWeb, user_id: str
) -> None:
    # Plan, puis la note de A ; le modèle se fige sur la note de B (arrêt du back en plein
    # `judge`, après l'enregistrement du verdict de A).
    first = await make_web_runner([], models=GatedModels([PLAN, SCORE_82], block_from=2))
    script_web(first)
    sid = await first.runner.start(user_id, "web_research", {"query": "attention multi-têtes"})
    async with asyncio.timeout(5):
        while await _verdict(first, user_id, sid, URL_A) != "kept":
            await asyncio.sleep(0.01)
    await wait_until(lambda: first.runner.is_active(sid))
    await first.runner.shutdown()
    assert await _verdict(first, user_id, sid, URL_B) == "pending"
    # Reprise : une seule réponse prévue, celle de B. Si A était renotée, elle prendrait la
    # note de B et B n'en aurait plus (échec de la session).
    second = await make_web_runner([SCORE_41])
    assert await second.runner.recover_on_startup() == [sid]
    await wait_status(second.factory, user_id, sid, "completed")
    assert second.fake is not None and len(second.fake.received) == 1
    assert "Billet B" in str(second.fake.received[0])
    assert await _verdict(second, user_id, sid, URL_A) == "kept"
    assert await _verdict(second, user_id, sid, URL_B) == "rejected"
    found_a = await _found(second, user_id, sid, URL_A)
    assert len(found_a) == 2 and found_a[0] == found_a[1]  # réémis à l'identique
    async with second.factory() as db:
        items, _ = await MemoryItemRepository(db, user_id).filtered(
            ItemFilter(kind="source"), limit=10, offset=0
        )
    assert len(items) == 1  # A seule, écrite une fois


async def test_gateway_verdicts_are_scoped_to_user_and_session(
    make_web_runner: MakeWeb, user_id: str, other_user_id: str
) -> None:
    web = await make_web_runner([PLAN, SCORE_82, SCORE_41])
    script_web(web)
    sid = await web.runner.start(user_id, "web_research", {"query": "attention multi-têtes"})
    await wait_status(web.factory, user_id, sid, "completed")
    async with web.factory() as db:
        ids = [r.id for r in await SourceRepository(db, user_id).list_for_session(sid)]
    mine = await web.gateway.verdicts(user_id, sid, ids)
    assert {v.verdict for v in mine.values()} == {"kept", "rejected"} and len(mine) == 3
    assert await web.gateway.verdicts(other_user_id, sid, ids) == {}
    assert await web.gateway.verdicts(user_id, "autre-session", ids) == {}
    assert await web.gateway.verdicts(user_id, sid, []) == {}
