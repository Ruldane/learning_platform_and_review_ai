"""`agent_runtime` : checkpointer séparé, reprise au démarrage, arrêt sans tâche orpheline."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.lifespan import agent_runtime
from app.agents.runtime.repositories import SessionRepository
from app.config import Settings
from tests.agents.runtime.runner_helpers import all_events, fake_llm, wait_idle, wait_status


async def test_runtime_opens_a_separate_checkpoint_file_and_recovers_sessions(
    tmp_path: Path, db_factory: async_sessionmaker[AsyncSession], user_id: str
):
    """Une session `running` dont le parcours n'existe plus (mise à jour du code) est reprise au
    démarrage et échoue de façon lisible, sans bloquer le démarrage."""
    settings = Settings(_env_file=None, data_dir=tmp_path / "data")  # type: ignore[call-arg]
    async with db_factory() as db:
        row = await SessionRepository(db, user_id).add(graph="disparu", status="running", input={})
        await db.commit()
    async with agent_runtime(settings, db_factory, fake_llm([]), {}) as runtime:
        assert settings.checkpoints_path.exists()
        await wait_status(db_factory, user_id, row.id, "failed")
        await wait_idle(runtime.runner, row.id)
        last = (await all_events(db_factory, user_id, row.id))[-1]
        assert last.payload.model_dump()["code"] == "unknown_graph"
    assert not runtime.runner.is_active(row.id)
