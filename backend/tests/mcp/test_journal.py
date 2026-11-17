"""Le journal des appels MCP (P19) : l'outil, le niveau, le code, la durée, les identifiants ;
jamais le contenu. Chaque refus de la porte y laisse une ligne (niveau 0)."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.mcp import McpCall, McpToken
from app.features.mcp.service.calls import clean_ids
from app.mcp.tools import ToolResult
from tests.mcp.support import API, FakeDispatcher, Mcp

SECRET_ARGUMENT = "CONTENU-SECRET-DE-LARGUMENT-4242"
SECRET_ANSWER = "réponse secrète du serveur 9191"


async def rows(factory: async_sessionmaker[AsyncSession]) -> list[McpCall]:
    async with factory() as db:
        stmt = select(McpCall).order_by(McpCall.created_at, McpCall.id)
        return list((await db.execute(stmt)).scalars())


async def test_call_journal_has_no_content(
    mcp: Mcp, inner: FakeDispatcher, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    token = await mcp.token(mode="write")
    inner.results["postings_add"] = ToolResult(
        data={"note": SECRET_ANSWER},
        code=201,
        ids={"posting_id": "abc-123", "title": SECRET_ANSWER, "n": 7, "texte libre": "x y z"},
    )

    await mcp.call(token, "postings_add", {"title": SECRET_ARGUMENT})
    await mcp.call(token, "postings_list", {"q": SECRET_ARGUMENT})

    journal = await rows(db_session_factory)
    assert [(r.action, r.level, r.code) for r in journal] == [
        ("postings_add", 2, 201),
        ("postings_list", 1, 200),
    ]
    assert journal[0].ids == {"posting_id": "abc-123", "n": 7}
    assert all(r.duration_ms >= 0 and r.token_id for r in journal)
    everything = repr([vars(r) for r in journal])
    assert SECRET_ARGUMENT not in everything and SECRET_ANSWER not in everything
    assert token not in everything

    listed = (await mcp.http.get(f"{API}/mcp/calls")).json()
    assert [row["action"] for row in listed] == ["postings_list", "postings_add"]  # récents d'abord
    assert SECRET_ARGUMENT not in str(listed) and SECRET_ANSWER not in str(listed)
    assert len((await mcp.http.get(f"{API}/mcp/calls?limit=1")).json()) == 1
    assert (await mcp.http.get(f"{API}/mcp/calls?limit=0")).status_code == 422


async def test_failed_and_crashed_calls_are_journaled(
    mcp: Mcp, inner: FakeDispatcher, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    token = await mcp.token()
    inner.results["postings_list"] = ToolResult(data={"error": {}}, code=404)
    await mcp.call(token, "postings_list")
    inner.boom = RuntimeError("boum")
    await mcp.call(token, "projects_list")  # hors périmètre : refusé avant l'envoyeur
    await mcp.call(token, "postings_read_offer")

    journal = await rows(db_session_factory)
    by_action = {r.action: r.code for r in journal}
    assert by_action["postings_list"] == 404
    assert by_action["postings_read_offer"] == 500
    assert by_action["projects_list"] == 403  # refus d'autorisation : journalisé aussi


async def test_rate_limited_calls_are_journaled(
    mcp: Mcp, gate: Any, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    from app.mcp.limits import Limits

    object.__setattr__(gate.limiter, "_limits", Limits(calls_per_minute=1))
    token = await mcp.token()
    await mcp.call(token, "postings_list")
    assert (await mcp.call(token, "postings_list")).status_code == 429

    assert [r.code for r in await rows(db_session_factory)] == [200, 429]


async def test_every_door_refusal_is_journaled_without_content(
    mcp: Mcp, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    good = await mcp.token()
    await mcp.rpc("tmcp_" + "B" * 43, "ping")  # inconnu : rattaché à l'utilisatrice du mode local
    await mcp.rpc(good, "ping", headers={"Host": "evil.example"})
    async with db_session_factory() as db:
        await db.execute(update(McpToken).values(expires_at=datetime.now(UTC) - timedelta(days=1)))
        await db.commit()
    await mcp.rpc(good, "ping")  # expiré
    await mcp.enable(False)
    async with db_session_factory() as db:
        await db.execute(update(McpToken).values(expires_at=datetime.now(UTC) + timedelta(days=1)))
        await db.commit()
    await mcp.rpc(good, "ping")  # interrupteur coupé

    journal = await rows(db_session_factory)
    actions = sorted((r.action, r.level, r.code) for r in journal)
    assert actions == [
        ("refused:host_not_allowed", 0, 403),
        ("refused:mcp_disabled", 0, 403),
        ("refused:mcp_token_expired", 0, 401),
        ("refused:mcp_token_invalid", 0, 401),
    ]
    assert sum(r.token_id is None for r in journal) == 2  # jeton inconnu, refus d'origine
    assert all(r.ids == {} for r in journal)


async def test_refusal_journal_is_capped(
    mcp: Mcp, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await mcp.enable()
    for _ in range(60):
        await mcp.rpc("tmcp_" + "C" * 43, "ping")

    assert len(await rows(db_session_factory)) == 30


def test_clean_ids_keeps_only_identifiers() -> None:
    cleaned = clean_ids(
        {
            "id": "abc-DEF_1",
            "n": 3,
            "flag": True,
            "long": "x" * 41,
            "text": "avec des espaces",
            "bad key!": "ok",
            "nested": {"a": 1},
            "none": None,
        }
    )

    assert cleaned == {"id": "abc-DEF_1", "n": 3}
