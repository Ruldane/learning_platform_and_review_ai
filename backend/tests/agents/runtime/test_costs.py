import asyncio
import json
from pathlib import Path

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.costs import (
    CostTracker,
    ModelPrice,
    TokenBudgetExceeded,
    estimate_cost,
    load_prices,
)
from app.agents.runtime.repositories import EventRepository, LlmCallRepository, SessionRepository
from app.providers.llm.fake import FakeLlmProvider

PRICES = {"m": ModelPrice(1.0, 5.0), "modele-test": ModelPrice(1_000_000.0, 2_000_000.0)}


def test_estimate_cost_uses_price_table() -> None:
    prices = {"m": ModelPrice(1.0, 5.0)}
    assert estimate_cost("m", 1_000_000, 200_000, prices) == pytest.approx(2.0)
    assert estimate_cost("inconnu", 10, 10, prices) == 0.0


def test_load_prices_reads_the_shipped_table() -> None:
    path = Path(__file__).parents[3] / "app" / "providers" / "llm" / "model_prices.json"
    prices = load_prices(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert set(prices) == set(raw)
    assert prices["glm-5.3-flash"] == ModelPrice(0.47, 1.47)


def test_load_prices_rejects_a_malformed_entry(tmp_path: Path) -> None:
    path = tmp_path / "prices.json"
    path.write_text('{"m": {"input_per_mtok": 1}}', encoding="utf-8")
    with pytest.raises(ValueError, match="m"):
        load_prices(path)


def make_tracker(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    user_id: str,
    session_id: str,
    cap_tokens: int = 300_000,
) -> CostTracker:
    return CostTracker(
        user_id=user_id,
        session_id=session_id,
        graph="demo",
        bus=bus,
        session_factory=db_factory,
        prices=PRICES,
        cap_tokens=cap_tokens,
    )


def model_with(replies: list[str]) -> BaseChatModel:
    return FakeLlmProvider(replies).build("modele-test", "fake-key")


async def call(model: BaseChatModel, tracker: CostTracker, agent: str = "demo_critic") -> None:
    chat = model.with_config(metadata={"agent": agent})
    await chat.ainvoke([HumanMessage("un deux trois quatre")], config={"callbacks": [tracker]})


async def test_cost_tracker_logs_call_and_publishes_cost_updated(
    db_factory: async_sessionmaker[AsyncSession], bus: EventBus, user_id: str, session_id: str
) -> None:
    tracker = make_tracker(db_factory, bus, user_id, session_id)
    await call(model_with(["a b c d e"]), tracker)  # 4 mots en entrée, 5 en sortie

    async with db_factory() as db:
        [row] = await LlmCallRepository(db, user_id).list()
        session = await SessionRepository(db, user_id).get(session_id)
        events = await EventRepository(db, user_id).list_after(session_id, 0)
    assert (row.tokens_in, row.tokens_out, row.agent) == (4, 5, "demo_critic")
    assert (row.session_id, row.graph) == (session_id, "demo")
    assert (row.provider, row.model) == ("fake", "modele-test")
    assert row.latency_ms >= 0
    assert row.cost_usd == pytest.approx(4 * 1.0 + 5 * 2.0)  # 1 et 2 USD par token (PRICES)
    assert session is not None
    assert (session.tokens_in, session.tokens_out) == (4, 5)
    assert session.cost_usd == pytest.approx(row.cost_usd)
    last = events[-1]
    assert last.type == "cost.updated" and last.agent == "demo_critic"
    assert last.payload == {
        "tokens_in": 4,
        "tokens_out": 5,
        "cost_usd": pytest.approx(row.cost_usd),
        "cap_tokens": 300_000,
    }


async def test_cost_tracker_accumulates_across_calls(
    db_factory: async_sessionmaker[AsyncSession], bus: EventBus, user_id: str, session_id: str
) -> None:
    tracker = make_tracker(db_factory, bus, user_id, session_id)
    model = model_with(["a b", "c d e"])
    await call(model, tracker)
    await call(model, tracker)
    async with db_factory() as db:
        session = await SessionRepository(db, user_id).get(session_id)
        events = await EventRepository(db, user_id).list_after(session_id, 0)
    assert session is not None and (session.tokens_in, session.tokens_out) == (8, 5)
    assert [e.payload["tokens_out"] for e in events] == [2, 5]


async def test_cost_tracker_blocks_when_cap_reached(
    db_factory: async_sessionmaker[AsyncSession], bus: EventBus, user_id: str, session_id: str
) -> None:
    async with db_factory() as db:
        await SessionRepository(db, user_id).update(
            session_id, tokens_in=200_000, tokens_out=100_000
        )
        await db.commit()
    tracker = make_tracker(db_factory, bus, user_id, session_id, cap_tokens=300_000)
    model = model_with(["jamais lu"])
    with pytest.raises(TokenBudgetExceeded) as e:
        await call(model, tracker)
    assert e.value.code == "token_cap_reached"
    assert e.value.message == "Plafond de 300000 tokens atteint pour cette session."
    # Le modèle n'a jamais été appelé : aucun appel journalisé.
    async with db_factory() as db:
        assert await LlmCallRepository(db, user_id).list() == []


async def test_cost_tracker_allows_calls_below_cap(
    db_factory: async_sessionmaker[AsyncSession], bus: EventBus, user_id: str, session_id: str
) -> None:
    async with db_factory() as db:
        await SessionRepository(db, user_id).update(session_id, tokens_in=299_998)
        await db.commit()
    await call(model_with(["ok"]), make_tracker(db_factory, bus, user_id, session_id))


async def test_cost_tracker_concurrent_calls_keep_exact_totals_and_unique_seq(
    db_factory: async_sessionmaker[AsyncSession], bus: EventBus, user_id: str, session_id: str
) -> None:
    tracker = make_tracker(db_factory, bus, user_id, session_id)
    await asyncio.gather(*(call(model_with(["a b"]), tracker) for _ in range(8)))
    async with db_factory() as db:
        session = await SessionRepository(db, user_id).get(session_id)
        events = await EventRepository(db, user_id).list_after(session_id, 0)
    assert session is not None and (session.tokens_in, session.tokens_out) == (32, 16)
    assert [e.seq for e in events] == list(range(1, 9))
    assert events[-1].payload["tokens_in"] == 32


async def test_cost_tracker_does_not_fail_the_call_when_bookkeeping_fails(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    user_id: str,
    other_user_id: str,
    session_id: str,
) -> None:
    # Session d'un autre utilisateur : le bus refuse de publier, la réponse du modèle passe.
    tracker = make_tracker(db_factory, bus, other_user_id, session_id)
    await call(model_with(["ok"]), tracker)
    async with db_factory() as db:
        assert len(await LlmCallRepository(db, other_user_id).list()) == 1
        assert await EventRepository(db, user_id).list_after(session_id, 0) == []
