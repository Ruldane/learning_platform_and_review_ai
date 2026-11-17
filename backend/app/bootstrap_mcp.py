"""Composition du serveur MCP (phase 10) : la porte (jetons, limites, journal) et le point d'entrée
`POST /mcp`, monté ici hors de `/api/v1` et hors du contrat. Les outils et l'envoyeur viennent de
10.B2 (`install_gate`) ; sans eux, la porte répond mais n'expose aucun outil. Comme `app.bootstrap`,
seul `app.main` l'importe, par `app.bootstrap` (contrat 5)."""

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.caller import McpIdentity
from app.features.auth.repository import UserRepository
from app.features.auth.service.allowlist import allowed
from app.features.mcp.service import CallJournal, GuardedDispatcher
from app.features.registry import MCP_FEATURES
from app.mcp.endpoint import mcp_endpoint
from app.mcp.limits import Limits, RateLimiter
from app.mcp.tools import (
    Dispatcher,
    McpGate,
    ToolRegistry,
    ToolResult,
    ToolSpec,
    UserCheck,
)

_MCP_PATH = "/mcp"


class NoTools:
    """Registre vide : tant que B2 n'a pas posé le sien, aucun outil n'existe."""

    def list_for(self, identity: McpIdentity) -> list[ToolSpec]:
        return []

    def get(self, name: str) -> ToolSpec | None:
        return None


class NoDispatcher:
    """Envoyeur vide : jamais appelé, puisque `NoTools` ne connaît aucun outil."""

    async def call(
        self, identity: McpIdentity, tool: ToolSpec, arguments: dict[str, Any]
    ) -> ToolResult:
        return ToolResult(data={"error": {"code": "no_tools", "message": "Aucun outil."}}, code=404)


def _user_allowed(settings: Settings) -> UserCheck:
    """Le compte du jeton existe-t-il et a-t-il encore le droit d'entrer ? En mode Google,
    retirer une adresse de `ALLOWED_EMAILS` coupe aussi ses jetons (comme ses sessions)."""

    async def check(db: AsyncSession, user_id: str) -> bool:
        user = await UserRepository(db).get(user_id)
        if user is None:
            return False
        if settings.auth_mode != "google":
            return True
        return bool(user.email) and allowed(user.email or "", settings.allowed_emails)

    return check


def _local_user(app: FastAPI) -> Callable[[], str | None]:
    """L'utilisatrice du mode local (seule candidate au journal d'un refus sans jeton connu) ;
    en mode Google, personne : un jeton inconnu n'appartient à aucun compte."""

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
) -> McpGate:
    """Pose la porte sur `app.state.mcp_gate` : l'envoyeur donné, enveloppé des limites et du
    journal. Les features connues viennent des déclarations (`None` tant qu'aucune n'existe)."""
    limiter = RateLimiter(limits)
    journal = CallJournal(app.state.session_factory, _local_user(app))
    guarded = GuardedDispatcher(dispatcher, limiter, journal)
    known = frozenset(declared.feature for declared in MCP_FEATURES) or None
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


def compose_mcp(app: FastAPI) -> None:
    """Monte `POST /mcp` (`GET` et `DELETE` répondent 405) et pose la porte. Sans outil pour
    l'instant : B2 appelle `install_gate` avec son registre et son envoyeur."""
    install_gate(app, NoTools(), NoDispatcher())
    app.add_route(_MCP_PATH, mcp_endpoint, methods=["POST", "GET", "DELETE"], name="mcp")
