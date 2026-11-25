"""MCP server wiring (phase 10): the gate (tokens, limits, journal) and the entry point
`POST /mcp`, mounted here outside `/api/v1` and outside the contract. The tools and the sender
come from 10.B2 (`install_adapter`); without a declaration, the gate answers but exposes no
tool. As with `app.bootstrap`, only `app.main` imports it, via `app.bootstrap` (contract 5)."""

from collections.abc import Callable, Mapping, Sequence

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graphs.registry import GRAPHS
from app.config import Settings
from app.features.auth.repository import UserRepository
from app.features.auth.service.allowlist import allowed
from app.features.mcp.service import CallJournal, GuardedDispatcher
from app.features.mcp.service.confirmations import ConfirmationService
from app.features.registry import MCP_FEATURES
from app.mcp.base import FeatureMcp
from app.mcp.dispatch import McpDispatcher
from app.mcp.endpoint import mcp_endpoint
from app.mcp.limits import Limits, RateLimiter
from app.mcp.registry import Registry, build_registry
from app.mcp.tools import (
    Dispatcher,
    McpGate,
    ToolRegistry,
    UserCheck,
)

_MCP_PATH = "/mcp"


def _user_allowed(settings: Settings) -> UserCheck:
    """Does the token's account exist and still have the right to enter? In Google mode, removing
    an address from `ALLOWED_EMAILS` also cuts its tokens (like its sessions)."""

    async def check(db: AsyncSession, user_id: str) -> bool:
        user = await UserRepository(db).get(user_id)
        if user is None:
            return False
        if settings.auth_mode != "google":
            return True
        return bool(user.email) and allowed(user.email or "", settings.allowed_emails)

    return check


def _local_user(app: FastAPI) -> Callable[[], str | None]:
    """The local mode user (the only candidate for the journal of a refusal without a known token);
    in Google mode, nobody: an unknown token belongs to no account."""

    def local() -> str | None:
        if app.state.settings.auth_mode != "local":
            return None
        user_id: str | None = getattr(app.state, "local_user_id", None)
        return user_id

    return local


def install_gate(
    app: FastAPI,
    tools: ToolRegistry,
    dispatcher: Dispatcher,
    limits: Limits | None = None,
    features: Sequence[FeatureMcp] = MCP_FEATURES,
) -> McpGate:
    """Sets the gate on `app.state.mcp_gate`: the given sender, wrapped in the limits and the
    journal. The known features come from the declarations given, those of the default
    application (`None` while none exists)."""
    limiter = RateLimiter(limits)
    journal = CallJournal(app.state.session_factory, _local_user(app))
    guarded = GuardedDispatcher(dispatcher, limiter, journal)
    known = frozenset(declared.feature for declared in features) or None
    gate = McpGate(
        tools=tools,
        dispatcher=guarded,
        limiter=limiter,
        user_allowed=_user_allowed(app.state.settings),
        refusals=journal.refusal,
        known_features=known,
    )
    app.state.mcp_gate = gate
    return gate


def install_adapter(
    app: FastAPI,
    features: Sequence[FeatureMcp],
    graphs: Mapping[str, type[BaseModel]] | None = None,
    limits: Limits | None = None,
) -> Registry:
    """The tool registry (checked against the OpenAPI: a wrong declaration makes startup fail),
    the real sender and the « à confirmer » requests, then the gate. Sets
    `app.state.mcp_registry` and `app.state.mcp_confirmations` (account -> service) for the
    `mcp` router. `graphs`: the input model of each graph (`app.mcp` ignores `app.agents`)."""
    registry = build_registry(features, app, graphs)

    def confirmations(user_id: str) -> ConfirmationService:
        return ConfirmationService(
            app.state.session_factory, user_id, dispatcher.run_stored, dispatcher.recheck
        )

    dispatcher = McpDispatcher(app, app.state.session_factory, registry, confirmations)
    app.state.mcp_play_launch = dispatcher.play_launch
    app.state.mcp_registry = registry
    app.state.mcp_confirmations = confirmations
    install_gate(app, registry, dispatcher, limits, features)
    return registry


def compose_mcp(app: FastAPI) -> None:
    """Mounts `POST /mcp` (`GET` and `DELETE` answer 405), builds the tools declared by the
    features (`MCP_FEATURES`) and sets the gate."""
    models = {name: spec.input_model for name, spec in GRAPHS.items()}
    settings: Settings = app.state.settings
    limits = Limits.with_daily(
        writes_per_day=settings.mcp_writes_per_day, calls_per_day=settings.mcp_calls_per_day
    )
    install_adapter(app, MCP_FEATURES, models, limits)
    app.add_route(_MCP_PATH, mcp_endpoint, methods=["POST", "GET", "DELETE"], name="mcp")
