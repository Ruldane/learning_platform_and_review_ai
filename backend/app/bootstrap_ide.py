"""Python IDE wiring (phase 10): the sandbox (`CodeSandbox`), the runs executor and the
professor. 10.A1 plugs the sandbox in here (`SpoolSandbox` on the exchange volume, or
`FakeSandbox` in tests, set beforehand by the test); 10.A3 composes the agent port here
(professor, generated exercises: `AgentIdeStore`, read by `app.main` in
`app.state.ide_store`). As with `app.bootstrap`, only `app.main` imports it, via
`app.bootstrap` (contract 5)."""

from contextlib import AsyncExitStack

from fastapi import FastAPI

from app.core.providers import Providers
from app.features.health.checks import SandboxCheck
from app.features.ide.service.agent_store import AgentIdeStore
from app.features.ide.service.model_gateway import ModelGateway
from app.features.ide.service.model_socket import open_model_socket
from app.providers.sandbox.spool import SpoolSandbox


def compose_ide(app: FastAPI) -> None:
    """Sets the sandbox on `app.state.providers.sandbox` and its check in the health (« Bac à sable
    »),
    then the agents' IDE port. A sandbox already set (in tests) is kept."""
    providers: Providers = app.state.providers
    if providers.sandbox is None:
        providers.sandbox = SpoolSandbox(app.state.settings.sandbox_spool_dir)
    providers.health_checks.append(SandboxCheck(providers.sandbox))
    app.state.ide_store = AgentIdeStore(app.state.session_factory, providers)


async def start_ide_gateway(app: FastAPI, stack: AsyncExitStack) -> None:
    providers: Providers = app.state.providers
    if not isinstance(providers.sandbox, SpoolSandbox):
        return
    gateway = ModelGateway(app.state.session_factory, providers.llm_factory)
    try:
        channel = await open_model_socket(app.state.settings.sandbox_spool_dir, gateway)
    except OSError:
        return
    if channel is not None:
        stack.push_async_callback(channel.close)
