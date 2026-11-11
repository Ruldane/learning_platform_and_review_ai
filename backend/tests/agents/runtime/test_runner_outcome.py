"""Issue d'une session : statut final et événement final écrits ensemble (D52 §2, D61). Une
écriture de l'issue qui échoue laisse la session `running` (reprise au démarrage) et le flux
ouvert ; une issue écrite ferme le bus (D42)."""

from collections.abc import Callable
from typing import Any

import httpx
import openai
import pytest

from app.agents.runtime.bus import EventBus
from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.repositories import EventRepository
from app.agents.runtime.runner import SessionRunner
from app.providers.llm.base import Tier
from tests.agents.graphs_for_tests import SECRET, Probe
from tests.agents.runtime.fakes import FlakyModel
from tests.agents.runtime.runner_helpers import (
    Factory,
    all_events,
    fake_llm,
    get_session,
    types,
    wait_idle,
    wait_status,
)

_FINALS = [("two_steps", "run.completed", "completed"), ("crash", "run.failed", "failed")]


def _record_closes(bus: EventBus, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    closed: list[str] = []
    real_close = bus.close

    async def close(**kwargs: Any) -> None:
        closed.append(kwargs["session_id"])
        await real_close(**kwargs)

    monkeypatch.setattr(bus, "close", close)
    return closed


def _break_final_write(monkeypatch: pytest.MonkeyPatch, final: str) -> list[bool]:
    """L'insertion de l'événement `final` lève tant que `broken[0]` est vrai."""
    broken = [True]
    real_add = EventRepository.add

    async def add(self: EventRepository, **fields: Any) -> Any:
        if broken[0] and fields.get("type") == final:
            raise RuntimeError("base indisponible")
        return await real_add(self, **fields)

    monkeypatch.setattr(EventRepository, "add", add)
    return broken


@pytest.mark.parametrize(("graph", "final", "status"), _FINALS)
async def test_written_outcome_closes_the_bus(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
    graph: str,
    final: str,
    status: str,
):
    closed = _record_closes(bus, monkeypatch)
    sid = await runner.start(user_id, graph, {})
    await wait_idle(runner, sid)
    assert closed == [sid]
    assert (await get_session(db_factory, user_id, sid)).status == status
    assert (await types(db_factory, user_id, sid))[-1] == final


@pytest.mark.parametrize(("graph", "final", "status"), _FINALS)
async def test_failed_final_write_leaves_the_session_running_and_its_stream_open(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
    graph: str,
    final: str,
    status: str,
):
    """Ni statut final sans événement, ni flux fermé (1000 = fin définitive pour le front) sur
    une session qui sera reprise : les abonnés restent, le redémarrage les reconnectera."""
    closed = _record_closes(bus, monkeypatch)
    _break_final_write(monkeypatch, final)
    sid = await runner.start(user_id, graph, {})
    await wait_idle(runner, sid)
    assert closed == []
    assert (await get_session(db_factory, user_id, sid)).status == "running"
    assert final not in await types(db_factory, user_id, sid)


async def test_failed_final_write_leaves_running_then_recovery_completes_once(
    make_runner: Callable[[ChatModelSource], SessionRunner],
    db_factory: Factory,
    user_id: str,
    probe: Probe,
    monkeypatch: pytest.MonkeyPatch,
):
    broken = _break_final_write(monkeypatch, "run.completed")
    first = make_runner(fake_llm([]))
    sid = await first.start(user_id, "two_steps", {})
    await wait_idle(first, sid)
    assert (await get_session(db_factory, user_id, sid)).status == "running"
    await first.shutdown()  # redémarrage du serveur
    broken[0] = False
    second = make_runner(fake_llm([]))
    assert await second.recover_on_startup() == [sid]
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(second, sid)
    assert (await types(db_factory, user_id, sid)).count("run.completed") == 1
    assert (probe.counter["A"], probe.counter["B"]) == (1, 1)  # aucun nœud rejoué


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
