"""Recherche avec les outils du client, puis notation et mémoire de Tremplin."""

import json

import pytest

from app.core.errors import AppError
from app.core.played import PLAY_CONTEXT, PlayContext
from app.features.research.repository import SourceRepository
from tests.agents.graphs.web_support import SCORE_82, URL_A, URL_B, MakeWeb
from tests.agents.runtime.runner_helpers import get_session, wait_idle


async def test_played_web_uses_client_sources(make_web_runner: MakeWeb, user_id: str) -> None:
    web = await make_web_runner([])
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "codex"))
    try:
        sid = await web.runner.start(user_id, "web_research", {"query": "attention"})
    finally:
        PLAY_CONTEXT.reset(flag)

    async def answer(schema: str, value: object, *, contains: str = "") -> None:
        await wait_idle(web.runner, sid)
        row = await get_session(web.factory, user_id, sid)
        assert row.pending_interrupt, (row.status, row.error)
        brief = row.pending_interrupt["brief"]
        assert brief["output_schema"]["title"] == schema
        assert contains in "\n".join(m["content"] for m in brief["messages"])
        await web.runner.submit_step(user_id, sid, brief["step_id"], json.dumps(value))

    await answer("SearchPlan", {"queries": [{"text": "attention", "lang": "fr"}]})
    with pytest.raises(AppError, match="Invalid reply"):
        await answer("SearchSources", {"sources": [{"url": "file:///tmp"}]})
    await answer("SearchSources", {"sources": [{"url": u, "title": "Doc"} for u in [URL_A, URL_B]]})
    for url in [URL_A, URL_B]:
        await answer("ReadSource", {"text": "Phrase du web.", "title": "Doc"}, contains=url)
    for _ in [URL_A, URL_B]:
        await answer("SourceScore", json.loads(SCORE_82), contains="<<<UNTRUSTED_CONTENT")
    await wait_idle(web.runner, sid)
    row = await get_session(web.factory, user_id, sid)
    assert (row.status, row.cost_usd) == ("completed", 0)
    async with web.factory() as db:
        rows = await SourceRepository(db, user_id).list_for_session(sid)
    assert {(r.url, r.verdict, r.score) for r in rows} == {(URL_A, "kept", 82), (URL_B, "kept", 82)}
    assert web.search.calls == [] and web.reader.calls == [] and web.fake and not web.fake.received
