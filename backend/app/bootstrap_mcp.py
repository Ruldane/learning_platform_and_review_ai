"""Composition du serveur MCP (phase 10) : la porte (jetons, limites, journal) et le point d'entrée
`POST /mcp`, monté ici hors de `/api/v1` et hors du contrat. Les outils et l'envoyeur viennent de
10.B2 (`install_adapter`) ; sans déclaration, la porte répond mais n'expose aucun outil. Comme
`app.bootstrap`,
seul `app.main` l'importe, par `app.bootstrap` (contrat 5)."""

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
    features: Sequence[FeatureMcp] = MCP_FEATURES,
) -> McpGate:
    """Pose la porte sur `app.state.mcp_gate` : l'envoyeur donné, enveloppé des limites et du
    journal. Les features connues viennent des déclarations données, celles de l'application par
    défaut (`None` tant qu'aucune n'existe)."""
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
    """Le registre des outils (vérifié contre l'OpenAPI : une déclaration fausse fait échouer le
    démarrage), l'envoyeur réel et les demandes « À confirmer », puis la porte. Pose
    `app.state.mcp_registry` et `app.state.mcp_confirmations` (compte -> service) pour le routeur
    `mcp`. `graphs` : le modèle d'entrée de chaque graphe (`app.mcp` ignore `app.agents`)."""
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
    """Monte `POST /mcp` (`GET` et `DELETE` répondent 405), construit les outils déclarés par les
    features (`MCP_FEATURES`) et pose la porte."""
    models = {name: spec.input_model for name, spec in GRAPHS.items()}
    install_adapter(app, MCP_FEATURES, models)
    app.add_route(_MCP_PATH, mcp_endpoint, methods=["POST", "GET", "DELETE"], name="mcp")
