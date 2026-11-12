"""Une session lancée depuis le nœud d'une autre (la chaîne des leçons, D90) part d'un contexte
vierge : elle n'hérite ni du suivi des coûts ni du plafond de tokens de sa lanceuse. Cas réel de
la fin de phase 4 : chaque appel des leçons était aussi compté dans `program_builder`, qui a passé
son plafond, et la leçon suivante échouait à son premier appel (`token_cap_reached`)."""

from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.runner import SessionRunner
from app.db.models.agents import LlmCall
from tests.agents.graphs_for_tests import Probe
from tests.agents.runtime.runner_helpers import fake_llm, get_session, wait_idle, wait_status

type Factory = async_sessionmaker[AsyncSession]
type MakeRunner = Callable[[ChatModelSource], SessionRunner]


async def _calls(db_factory: Factory, session_id: str) -> int:
    async with db_factory() as db:
        query = select(func.count()).select_from(LlmCall).where(LlmCall.session_id == session_id)
        return int((await db.execute(query)).scalar_one())


async def test_a_session_started_from_a_node_does_not_inherit_the_parent_cost_tracker(
    make_runner: MakeRunner, db_factory: Factory, user_id: str, probe: Probe
) -> None:
    runner = make_runner(fake_llm(["Bonjour", "Salut"]))
    probe.start_child = lambda: runner.start(user_id, "one_llm_call", {})
    parent = await runner.start(user_id, "chain", {})
    await wait_status(db_factory, user_id, parent, "completed")
    await wait_status(db_factory, user_id, probe.child_id, "completed")
    await wait_idle(runner, probe.child_id)
    assert await _calls(db_factory, parent) == 1  # le sien seulement
    assert await _calls(db_factory, probe.child_id) == 1
    before = await get_session(db_factory, user_id, parent)
    child = await get_session(db_factory, user_id, probe.child_id)
    assert child.tokens_in > 0 and before.tokens_in == child.tokens_in  # rien de compté deux fois
