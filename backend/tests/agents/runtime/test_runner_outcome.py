"""Issue d'une session : le bus est fermé même si la publication de l'événement final échoue
(sinon les abonnés du WebSocket attendraient indéfiniment, D42)."""

from collections.abc import Callable
from typing import Any

import httpx
import openai
import pytest

from app.agents.runtime.bus import EventBus
from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.runner import SessionRunner
from app.providers.llm.base import Tier
from tests.agents.graphs_for_tests import SECRET
from tests.agents.runtime.fakes import FlakyModel
from tests.agents.runtime.runner_helpers import (
    Factory,
    all_events,
    get_session,
    wait_idle,
)


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


class _RejectedKey:
    """Source de modèles dont le fournisseur refuse la clé, comme le ferait le SDK d'OpenAI."""

    async def get_chat_model(self, user_id: str, tier: Tier, agent: str | None = None) -> Any:
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        exc = openai.AuthenticationError(
            f"Incorrect API key provided: {SECRET}",
            response=httpx.Response(401, request=request),
            body=None,
        )
        metadata = {"tremplin_provider": "openai", "tremplin_provider_label": "OpenAI"}
        return FlakyModel(fail_times=99, exc=exc, metadata=metadata)


async def test_a_provider_failure_reaches_the_user_as_a_readable_run_failed(
    make_runner: Callable[[ChatModelSource], SessionRunner],
    db_factory: Factory,
    user_id: str,
    caplog: pytest.LogCaptureFixture,
):
    """I3 : pas d'« erreur inattendue » pour une clé refusée ; ni la clé ni le message du SDK."""
    runner = make_runner(_RejectedKey())
    sid = await runner.start(user_id, "one_llm_call", {})
    await wait_idle(runner, sid)
    failed = [e for e in await all_events(db_factory, user_id, sid) if e.type == "run.failed"]
    assert len(failed) == 1
    payload = failed[0].payload.model_dump()
    assert payload["code"] == "llm_key_rejected"
    assert payload["message"].startswith("Clé refusée par OpenAI")
    row = await get_session(db_factory, user_id, sid)
    assert row.status == "failed" and row.error == payload
    assert SECRET not in str(payload) and SECRET not in caplog.text
