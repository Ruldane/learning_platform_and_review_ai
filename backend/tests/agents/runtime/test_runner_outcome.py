"""Issue d'une session : le bus est fermé même si la publication de l'événement final échoue
(sinon les abonnés du WebSocket attendraient indéfiniment, D42)."""

from typing import Any

import pytest

from app.agents.runtime.bus import EventBus
from app.agents.runtime.runner import SessionRunner
from tests.agents.runtime.runner_helpers import wait_idle


@pytest.mark.parametrize(
    ("graph", "final"), [("two_steps", "run.completed"), ("crash", "run.failed")]
)
async def test_bus_is_closed_even_if_the_final_publish_fails(
    runner: SessionRunner,
    bus: EventBus,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
    graph: str,
    final: str,
):
    closed: list[str] = []
    real_publish, real_close = bus.publish, bus.close

    async def publish(**kwargs: Any) -> Any:
        if kwargs["type"] == final:
            raise RuntimeError("base indisponible")
        return await real_publish(**kwargs)

    async def close(**kwargs: Any) -> None:
        closed.append(kwargs["session_id"])
        await real_close(**kwargs)

    monkeypatch.setattr(bus, "publish", publish)
    monkeypatch.setattr(bus, "close", close)
    sid = await runner.start(user_id, graph, {})
    await wait_idle(runner, sid)
    assert closed == [sid]
