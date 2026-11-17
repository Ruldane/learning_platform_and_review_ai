"""Les types que la porte partage avec B2 (phase 10) : un outil (`ToolSpec`), le résultat d'un
appel (`ToolResult`), le registre des outils et l'envoyeur (`ToolRegistry`, `Dispatcher`, fournis
par la composition), et `McpGate`, ce que la porte lit sur `app.state.mcp_gate`."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import McpIdentity
from app.mcp.base import Level, PrecheckInput, Verdict
from app.mcp.limits import RateLimiter
from app.mcp.schema import RoutePlan


@dataclass(frozen=True)
class ToolSpec:
    """Un outil exposé (produit par le registre de B2) : `feature` pour le périmètre du jeton,
    `level` (1 lecture, 2 écriture réversible, 3 à confirmer), `untrusted` les champs de la
    réponse qui viennent du web, `bucket` un compteur de limite à part (`code_run`). Posés par le
    registre : `route` (méthode et chemin sans `/api/v1`) ou `graph` (lancement d'un parcours),
    `side_effects`, `precheck` (niveau 3), `plan` (où va chaque argument), `response_fields`."""

    name: str
    feature: str
    level: Level
    description: str
    input_schema: Mapping[str, Any]
    untrusted: tuple[str, ...] = ()
    bucket: str | None = None
    summary: str | None = None
    route: tuple[str, str] | None = None
    graph: str | None = None
    side_effects: Literal["db", "external"] = "db"
    precheck: Callable[[PrecheckInput], Awaitable[Verdict]] | None = None
    plan: RoutePlan | None = None
    response_fields: frozenset[str] | None = None


@dataclass(frozen=True)
class ToolResult:
    """Ce que rend l'envoyeur : le corps de la réponse de la route (`data`), son code HTTP et les
    identifiants touchés (pour le journal : jamais de contenu). Un code de 400 ou plus est une
    erreur de l'outil. `call_id` : l'identifiant de l'appel d'un outil de niveau 2 (celui de ses
    changements annulables), repris par le journal comme identifiant de la ligne."""

    data: Any
    code: int = 200
    ids: Mapping[str, Any] = field(default_factory=dict)
    call_id: str | None = None

    @property
    def is_error(self) -> bool:
        return self.code >= 400


class ToolRegistry(Protocol):
    """Le registre des outils (B2). `list_for` : ceux que cette identité peut voir ; `get` : un
    outil par son nom, **hors périmètre compris** (pour refuser en 403 plutôt que « inconnu »)."""

    def list_for(self, identity: McpIdentity) -> list[ToolSpec]: ...

    def get(self, name: str) -> ToolSpec | None: ...


class Dispatcher(Protocol):
    """L'envoyeur (B2) : appelle la vraie route sous l'identité du jeton, ou crée la demande
    « À confirmer » d'un outil de niveau 3."""

    async def call(
        self, identity: McpIdentity, tool: ToolSpec, arguments: dict[str, Any]
    ) -> ToolResult: ...


UserCheck = Callable[[AsyncSession, str], Awaitable[bool]]
# Journal d'un refus de la porte : (compte du jeton ou `None`, jeton ou `None`, action, niveau,
# code HTTP). Jamais de contenu.
RefusalSink = Callable[[str | None, str | None, str, int, int], Awaitable[None]]


@dataclass(frozen=True)
class McpGate:
    """Ce que la porte lit (`app.state.mcp_gate`, posé par la composition) : les outils,
    l'envoyeur (qui limite et journalise), les limites, et le contrôle « ce compte a-t-il toujours
    le droit d'entrer » (liste `ALLOWED_EMAILS` en mode Google)."""

    tools: ToolRegistry
    dispatcher: Dispatcher
    limiter: RateLimiter
    user_allowed: UserCheck
    refusals: RefusalSink
    known_features: frozenset[str] | None = None
