"""`SessionLauncher` (D82) : lancer une session hors requête HTTP (port, tâche planifiée)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.runtime.runner import SessionRunner
from app.core.errors import AppError
from tests.agents.runtime.runner_helpers import get_session, wait_status


async def test_launcher_unbound_is_engine_unavailable() -> None:
    with pytest.raises(AppError) as e:
        await SessionLauncher().start("u", "demo_debate", {"topic": "abc"})
    assert e.value.code == "engine_unavailable" and e.value.status_code == 503
    assert e.value.message == "Le moteur d'agents n'est pas prêt."


async def test_launcher_starts_session_with_subject(
    runner: SessionRunner, db_factory: async_sessionmaker[AsyncSession], user_id: str
) -> None:
    launcher = SessionLauncher()
    launcher.bind(runner)
    sid = await launcher.start(user_id, "two_steps", {}, subject_type="program", subject_id="p-1")
    await wait_status(db_factory, user_id, sid, "completed")
    row = await get_session(db_factory, user_id, sid)
    assert (row.graph, row.subject_type, row.subject_id) == ("two_steps", "program", "p-1")


async def test_launcher_keeps_runner_errors(runner: SessionRunner, user_id: str) -> None:
    launcher = SessionLauncher()
    launcher.bind(runner)
    with pytest.raises(AppError) as e:
        await launcher.start(user_id, "nope", {})
    assert e.value.code == "unknown_graph"


async def test_launcher_on_stopping_server_is_engine_unavailable(
    runner: SessionRunner, user_id: str
) -> None:
    launcher = SessionLauncher()
    launcher.bind(runner)
    await runner.shutdown()
    with pytest.raises(AppError) as e:
        await launcher.start(user_id, "two_steps", {})
    assert e.value.code == "engine_unavailable" and e.value.status_code == 503


async def test_launcher_unbound_after_unbind(runner: SessionRunner, user_id: str) -> None:
    launcher = SessionLauncher()
    launcher.bind(runner)
    launcher.unbind()
    with pytest.raises(AppError) as e:
        await launcher.start(user_id, "two_steps", {})
    assert e.value.code == "engine_unavailable"
