"""M11 : au plus 30 lancements de graphe par utilisatrice et par jour glissant, comptés sur le
journal des appels. Les lancements sont les outils `graph_<nom>` et les actions dont la route lance
un graphe (`McpAction.launches`). Au-delà : refus `mcp_graph_quota`, en français, sans contenu,
journalisé au niveau de l'outil ; rien n'est envoyé."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.mcp import McpCall
from app.mcp.limits import Limits
from app.mcp.tools import McpGate, ToolSpec
from tests.mcp.support import FakeDispatcher, FakeTools, Mcp, spec

LAUNCH_LIMIT = 30


def _launcher(name: str, **kw: str) -> ToolSpec:
    base = spec(name, "postings", 2)
    return ToolSpec(**{**base.__dict__, **kw})


@pytest.fixture
def tools() -> FakeTools:
    fake = FakeTools()
    for item in (
        _launcher("graph_web_research", graph="web_research"),
        _launcher("postings_analyse", launches="gap_analysis"),
    ):
        fake.specs[item.name] = item
    return fake


@pytest.fixture(autouse=True)
def _roomy_limits(gate: McpGate) -> None:
    """Les limites par minute ne sont pas l'objet : on teste le plafond du jour."""
    object.__setattr__(
        gate.limiter,
        "_limits",
        Limits(calls_per_minute=10_000, writes_per_minute=10_000, calls_per_day=10_000,
               writes_per_day=10_000),
    )  # fmt: skip


def _error_of(response: httpx.Response) -> dict[str, Any] | None:
    """L'erreur d'outil d'une réponse (un refus du plafond arrive comme résultat d'outil en erreur,
    que Claude lit), `None` si l'appel a réussi."""
    result = response.json()["result"]
    if not result["isError"]:
        return None
    error: dict[str, Any] = json.loads(result["content"][0]["text"])["data"]["error"]
    return error


async def _count(factory: async_sessionmaker[AsyncSession], code: int) -> int:
    async with factory() as db:
        stmt = select(func.count()).select_from(McpCall).where(McpCall.code == code)
        return int((await db.execute(stmt)).scalar_one())


async def test_the_31st_launch_of_the_day_is_refused_in_french_without_content(
    mcp: Mcp, inner: FakeDispatcher, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    token = await mcp.token(("postings",), "write")
    for i in range(LAUNCH_LIMIT):
        # Les deux sortes de lancement comptent ensemble.
        name = "graph_web_research" if i % 2 else "postings_analyse"
        assert (await mcp.call(token, name, {"topic": "secret"})).status_code == 200

    response = await mcp.call(token, "postings_analyse", {"posting_id": "CONTENU-A-NE-PAS-REVOIR"})

    error = _error_of(response)
    assert error is not None and error["code"] == "mcp_graph_quota"
    assert "30" in error["message"] and "parcours" in error["message"]
    assert "CONTENU-A-NE-PAS-REVOIR" not in response.text
    assert len(inner.calls) == LAUNCH_LIMIT  # le refusé n'est jamais parti
    async with db_session_factory() as db:
        refused = (await db.execute(select(McpCall).where(McpCall.code == 429))).scalar_one()
    assert (refused.action, refused.level) == ("postings_analyse", 2)  # niveau de l'outil
    assert refused.ids == {}


async def test_other_calls_are_not_counted_nor_blocked(mcp: Mcp, inner: FakeDispatcher) -> None:
    token = await mcp.token(("postings",), "write")
    for _ in range(LAUNCH_LIMIT + 5):
        assert (await mcp.call(token, "postings_add", {})).status_code == 200
        assert (await mcp.call(token, "postings_list")).status_code == 200
    assert (await mcp.call(token, "postings_analyse")).status_code == 200


async def test_the_day_is_rolling_and_a_refusal_does_not_count(
    mcp: Mcp, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    token = await mcp.token(("postings",), "write")
    assert (await mcp.call(token, "postings_analyse")).status_code == 200
    async with db_session_factory() as db:
        owner = (await db.execute(select(McpCall.user_id))).scalar_one()
        old = datetime.now(UTC) - timedelta(hours=25)
        for _ in range(LAUNCH_LIMIT):  # hors de la fenêtre : ne comptent plus
            db.add(McpCall(user_id=owner, token_id=None, action="postings_analyse", level=2,
                           code=200, duration_ms=1, ids={}, created_at=old))  # fmt: skip
        await db.commit()

    for _ in range(LAUNCH_LIMIT - 1):
        assert (await mcp.call(token, "postings_analyse")).status_code == 200
    assert _error_of(await mcp.call(token, "postings_analyse")) is not None
    assert (
        _error_of(await mcp.call(token, "postings_analyse")) is not None
    )  # un refus ne compte pas
    assert await _count(db_session_factory, 200) == LAUNCH_LIMIT * 2


async def test_failed_launches_do_not_use_the_quota(mcp: Mcp, inner: FakeDispatcher) -> None:
    from app.mcp.tools import ToolResult

    token = await mcp.token(("postings",), "write")
    inner.results["postings_analyse"] = ToolResult(data={"error": {}}, code=422)
    for _ in range(LAUNCH_LIMIT + 3):
        assert (await mcp.call(token, "postings_analyse")).status_code == 200  # HTTP du MCP
    inner.results.clear()
    assert (await mcp.call(token, "postings_analyse")).status_code == 200
