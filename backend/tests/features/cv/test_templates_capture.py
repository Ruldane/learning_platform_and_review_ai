"""Capture du design de bout en bout sur le vrai port (`AgentCvTemplateStore`, D125, D126) : le
parcours `cv_capture` (mode `design`) lancé par le service des gabarits, avec des modèles scriptés,
le rendu de test lisible et l'extracteur réel. Validée, la passe rendue devient le gabarit actif ;
une panne du modèle laisse un gabarit en échec, jamais « en capture »."""

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

import pytest

from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.runner import SessionRunner
from app.features.cv.schemas_templates import TemplateOut
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.templates import get_template
from app.features.cv.service.templates_store import AgentCvTemplateStore
from tests.agents.graphs.design_support import _Settings, designer
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import wait_status
from tests.features.cv.templates_support import capture, liberation_spec, template_row
from tests.support.cv_templates import FakeCvTemplateStore

USER = "u-design"


class RunnerLauncher:
    """`Launcher` du CV branché sur le runner du test, comme `SessionLauncher` lié au moteur."""

    def __init__(self, runner: SessionRunner) -> None:
        self.runner = runner

    async def start(
        self,
        user_id: str,
        graph: str,
        input: dict[str, Any],
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
    ) -> str:
        return await self.runner.start(user_id, graph, input, subject_type, subject_id)


type Launch = Callable[[Any], Awaitable[tuple[SessionRunner, str, str]]]


@pytest.fixture
async def launch(tmp_path: Path, cv_runtime: CvRuntime) -> AsyncIterator[Launch]:
    """`launch(models)` : runner réel sur le vrai port, puis gabarit créé par le service (la
    capture part par le lanceur) ; rend `(runner, gabarit, session)`."""
    await add_users(cv_runtime.session_factory, USER, "u-autre")
    async with AsyncExitStack() as stack:

        async def start(models: Any) -> tuple[SessionRunner, str, str]:
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "ckpt.db"))
            bus = EventBus(cv_runtime.session_factory)
            runner = SessionRunner(
                session_factory=cv_runtime.session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(cv_templates=AgentCvTemplateStore(cv_runtime)),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            cv_runtime.launcher = RunnerLauncher(runner)
            template_id = await capture(cv_runtime, user_id=USER)
            row = await template_row(cv_runtime, template_id, USER)
            return runner, template_id, str(row.session_id)

        yield start


async def test_validated_capture_becomes_the_active_template(
    launch: Launch, cv_runtime: CvRuntime
) -> None:
    spec = json.dumps(liberation_spec().model_dump(mode="json"))
    runner, template_id, sid = await launch(designer(draft=[spec] * 3, fix=[spec] * 30))
    waiting = await wait_status(cv_runtime.session_factory, USER, sid, "waiting_user")
    pending = waiting.pending_interrupt or {}
    assert pending.get("kind") == "cv_template"
    await runner.resume(USER, sid, pending["interrupt_id"], "validate")
    await wait_status(cv_runtime.session_factory, USER, sid, "completed")
    template: TemplateOut = await get_template(cv_runtime, USER, template_id)
    assert (template.status, template.active, template.failure_reason) == ("ready", True, None)
    assert 1 <= template.passes <= 3 and template.score is not None
    assert len(template.zones) == 5


async def test_model_outage_leaves_a_failed_template(launch: Launch, cv_runtime: CvRuntime) -> None:
    _, template_id, sid = await launch(designer(sample=["pas du JSON"] * 3))
    await wait_status(cv_runtime.session_factory, USER, sid, "failed")
    template = await get_template(cv_runtime, USER, template_id)
    assert template.status == "failed" and template.failure_reason is not None


def test_fake_store_follows_the_same_port() -> None:
    """Le faux port des tests du graphe et le vrai ont la même interface."""
    real = {name for name in dir(AgentCvTemplateStore) if not name.startswith("_")}
    fake = {name for name in dir(FakeCvTemplateStore) if not name.startswith("_")}
    assert real <= fake
