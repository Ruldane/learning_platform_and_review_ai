"""Issue d'une session : statut final et événement final écrits ensemble (D52 §2, D61). Une
écriture de l'issue qui échoue est retentée, puis remplacée par un `failed` atomique
(`outcome_not_written`) ; si rien ne s'écrit, la session reste `running` (reprise au
démarrage) et son flux ouvert. Une issue finale en base ferme le bus (D42)."""

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


def _break_writes(monkeypatch: pytest.MonkeyPatch, *kinds: str, times: int = 99) -> list[int]:
    """Les `times` premières insertions d'un événement de type `kinds` lèvent ; `left[0]` = échecs
    restants (0 : la base est revenue)."""
    left = [times]
    real_add = EventRepository.add

    async def add(self: EventRepository, **fields: Any) -> Any:
        if left[0] > 0 and fields.get("type") in kinds:
            left[0] -= 1
            raise RuntimeError("base indisponible")
        return await real_add(self, **fields)

    monkeypatch.setattr(EventRepository, "add", add)
    return left


async def _failed_payload(db: Factory, user_id: str, sid: str) -> dict[str, Any]:
    failed = [e for e in await all_events(db, user_id, sid) if e.type == "run.failed"]
    assert len(failed) == 1
    return failed[0].payload.model_dump()


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


async def test_transient_write_failure_is_retried_and_keeps_the_original_outcome(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    closed = _record_closes(bus, monkeypatch)
    _break_writes(monkeypatch, "run.completed", times=1)
    sid = await runner.start(user_id, "two_steps", {})
    await wait_idle(runner, sid)
    assert (await get_session(db_factory, user_id, sid)).status == "completed"
    kinds = await types(db_factory, user_id, sid)
    assert kinds.count("run.completed") == 1 and "run.failed" not in kinds
    assert closed == [sid]


async def test_failed_completion_write_falls_back_to_an_atomic_failure(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Aucune session `running` sans tâche : l'issue ne s'écrit pas, `failed` la remplace, le
    bus se ferme (1000 sur le WebSocket)."""
    closed = _record_closes(bus, monkeypatch)
    _break_writes(monkeypatch, "run.completed")
    sid = await runner.start(user_id, "two_steps", {})
    await wait_idle(runner, sid)
    row = await get_session(db_factory, user_id, sid)
    payload = await _failed_payload(db_factory, user_id, sid)
    assert row.status == "failed" and payload["code"] == "outcome_not_written"
    assert row.error == payload and "run.completed" not in await types(db_factory, user_id, sid)
    assert closed == [sid]


async def test_failed_question_write_falls_back_to_an_atomic_failure(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    closed = _record_closes(bus, monkeypatch)
    _break_writes(monkeypatch, "interrupt.requested")
    sid = await runner.start(user_id, "ask", {})
    await wait_idle(runner, sid)
    row = await get_session(db_factory, user_id, sid)
    assert row.status == "failed" and row.pending_interrupt is None
    assert (await _failed_payload(db_factory, user_id, sid))["code"] == "outcome_not_written"
    assert closed == [sid]


async def test_outcome_committed_despite_an_error_is_not_written_twice(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Le commit a abouti mais l'écriture a levé : le nouvel essai est refusé par la garde, le
    statut relu est terminal, le bus est fermé ; ni doublon ni repli en échec."""
    closed = _record_closes(bus, monkeypatch)
    real_insert = bus._writer.insert
    raised: list[str] = []

    async def insert(*args: Any, **kwargs: Any) -> Any:
        row = await real_insert(*args, **kwargs)
        if row is not None and row.type == "run.completed" and not raised:
            raised.append(row.type)
            raise RuntimeError("réponse perdue après le commit")
        return row

    monkeypatch.setattr(bus._writer, "insert", insert)
    sid = await runner.start(user_id, "two_steps", {})
    await wait_idle(runner, sid)
    assert (await get_session(db_factory, user_id, sid)).status == "completed"
    kinds = await types(db_factory, user_id, sid)
    assert kinds.count("run.completed") == 1 and "run.failed" not in kinds
    assert closed == [sid]


async def test_when_nothing_can_be_written_the_session_stays_running_and_its_stream_open(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Issue et repli en échec (`crash` : `run.failed` dans les deux cas) : ni statut final sans
    événement, ni 1000 sur une session qui sera reprise au démarrage."""
    closed = _record_closes(bus, monkeypatch)
    _break_writes(monkeypatch, "run.failed")
    sid = await runner.start(user_id, "crash", {})
    await wait_idle(runner, sid)
    assert closed == []
    assert (await get_session(db_factory, user_id, sid)).status == "running"
    assert "run.failed" not in await types(db_factory, user_id, sid)


async def test_failed_final_write_leaves_running_then_recovery_completes_once(
    make_runner: Callable[[ChatModelSource], SessionRunner],
    db_factory: Factory,
    user_id: str,
    probe: Probe,
    monkeypatch: pytest.MonkeyPatch,
):
    left = _break_writes(monkeypatch, "run.completed", "run.failed")  # base indisponible
    first = make_runner(fake_llm([]))
    sid = await first.start(user_id, "two_steps", {})
    await wait_idle(first, sid)
    assert (await get_session(db_factory, user_id, sid)).status == "running"
    await first.shutdown()  # redémarrage du serveur
    left[0] = 0
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
