"""Le fournisseur choisi pour un parcours (« API GLM »…) est gardé sur la session, vu par la source
des modèles à chaque appel, après une reprise et dans les sessions filles."""

from langchain_core.language_models import BaseChatModel

from app.agents.runtime.playback import models_for
from app.agents.runtime.runner import SessionRunner
from app.core.played import PLAY_CONTEXT, PlayContext, inherit_source, run_source
from app.db.models.agents import AgentSession
from app.providers.llm.base import ModelChoice, Tier
from app.providers.llm.factory import LlmFactory
from app.providers.llm.fake import FakeLlmProvider
from tests.agents.graphs_for_tests import Probe
from tests.agents.runtime.runner_helpers import fake_llm, get_session, wait_idle, wait_status
from tests.agents.runtime.test_runner_chain import Factory, MakeRunner


class _Choice:
    async def get_model_choice(self, user_id: str, tier: Tier, agent: str | None) -> ModelChoice:
        return ModelChoice(provider="fake", model="modele-test")


class _Keys:
    async def get_key(self, user_id: str, provider: str) -> str | None:
        return "cle-de-test"


def forced_glm(replies: list[str]) -> LlmFactory:
    """Le faux fournisseur répond aussi sous le nom « glm » : un appel n'aboutit que si la
    fabrique a bien remplacé le choix « fake » par le préréglage GLM."""
    provider = FakeLlmProvider(replies)
    return LlmFactory(_Choice(), _Keys(), {"glm": provider}, {})


class _Seen:
    """Source des modèles qui note le fournisseur du parcours vu à chaque appel."""

    def __init__(self, inner: LlmFactory) -> None:
        self.inner = inner
        self.providers: list[str | None] = []

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        play = PLAY_CONTEXT.get()
        self.providers.append(play.provider if play else None)
        return await self.inner.get_chat_model(user_id, tier, agent)


async def _start(runner: SessionRunner, user_id: str, graph: str) -> str:
    flag = PLAY_CONTEXT.set(PlayContext(user_id, None, provider="glm"))
    try:
        return await runner.start(user_id, graph, {})
    finally:
        PLAY_CONTEXT.reset(flag)


async def test_api_source_is_stored_and_seen_by_every_call(
    make_runner: MakeRunner, db_factory: Factory, user_id: str
) -> None:
    seen = _Seen(forced_glm(["Bonjour"]))
    runner = make_runner(seen)
    sid = await _start(runner, user_id, "one_llm_call")
    await wait_status(db_factory, user_id, sid, "completed")
    row = await get_session(db_factory, user_id, sid)
    assert (row.played_by, row.model_provider) == (None, "glm")
    assert seen.providers == ["glm"]


async def test_child_session_inherits_the_provider(
    make_runner: MakeRunner, db_factory: Factory, user_id: str, probe: Probe
) -> None:
    seen = _Seen(forced_glm(["Bonjour", "Salut"]))
    runner = make_runner(seen)
    probe.start_child = lambda: runner.start(user_id, "one_llm_call", {})
    parent = await _start(runner, user_id, "chain")
    await wait_status(db_factory, user_id, parent, "completed")
    await wait_status(db_factory, user_id, probe.child_id, "completed")
    await wait_idle(runner, probe.child_id)
    child = await get_session(db_factory, user_id, probe.child_id)
    assert child.model_provider == "glm" and child.played_by is None
    assert seen.providers == ["glm", "glm"]


async def test_a_resumed_row_restores_its_provider(user_id: str) -> None:
    row = AgentSession(user_id=user_id, graph="g", status="running", model_provider="openai")
    usual = fake_llm([])
    flag = PLAY_CONTEXT.set(None)
    try:
        assert models_for(row, usual) is usual  # mêmes modèles, fournisseur forcé par le contexte
        play = PLAY_CONTEXT.get()
        assert play is not None and (play.client, play.provider) == (None, "openai")
    finally:
        PLAY_CONTEXT.reset(flag)


async def test_inherit_source_restores_client_or_provider(user_id: str) -> None:
    with inherit_source(user_id, None, "anthropic"):
        assert run_source(user_id) == (None, "anthropic")
        assert run_source("someone-else") == (None, None)
    with inherit_source(user_id, "codex", None):
        assert run_source(user_id) == ("codex", None)
    assert run_source(user_id) == (None, None)
