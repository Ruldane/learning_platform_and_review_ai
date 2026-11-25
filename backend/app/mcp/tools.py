"""The types the gate shares with B2 (phase 10): a tool (`ToolSpec`), the result of a call
(`ToolResult`), the tool registry and the sender (`ToolRegistry`, `Dispatcher`, provided by the
composition), and `McpGate`, what the gate reads from `app.state.mcp_gate`."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import McpIdentity
from app.mcp.base import Level, PrecheckInput, Verdict
from app.mcp.limits import RateLimiter
from app.mcp.schema import RoutePlan

TREMPLIN_OVERVIEW = "tremplin_overview"


@dataclass(frozen=True)
class ToolSpec:
    """An exposed tool (produced by B2's registry): `feature` for the token's scope, `level` (1
    read,
    2 reversible write, 3 to confirm), `untrusted` the response fields that come from the web,
    `bucket` a separate limit counter (`code_run`). Set by the registry: `route` (method and path
    without `/api/v1`) or `graph` (launch of a flow), `side_effects`, `precheck` (level 3), `plan`
    (where each argument goes), `response_fields`."""

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
    launches: str | None = None
    artifact: bool = False
    manual_url: str | None = None

    def in_scope(self, identity: McpIdentity) -> bool:
        return self.name == TREMPLIN_OVERVIEW or self.feature in identity.features

    def available_to(self, identity: McpIdentity) -> bool:
        return self.in_scope(identity) and (self.level == 1 or identity.mode == "write")


@dataclass(frozen=True)
class ToolResult:
    """What the sender returns: the route's response body (`data`), its HTTP code and the
    identifiers
    touched (for the journal: never content). A code of 400 or more is a tool error. `call_id`:
    the identifier of a level 2 tool's call (that of its undoable changes), taken by the journal
    as the row's identifier. `notice`: one more sentence for Claude, added to the envelope's note
    (e.g. a level 2 call without history: it cannot be undone)."""

    data: Any
    code: int = 200
    ids: Mapping[str, Any] = field(default_factory=dict)
    call_id: str | None = None
    notice: str | None = None

    @property
    def is_error(self) -> bool:
        return self.code >= 400


class ToolRegistry(Protocol):
    """The tool registry (B2). `list_for`: those this identity can see; `get`: a tool by its name,
    **out-of-scope ones included** (to refuse with 403 rather than "unknown")."""

    def list_for(self, identity: McpIdentity) -> list[ToolSpec]: ...

    def get(self, name: str) -> ToolSpec | None: ...


class Dispatcher(Protocol):
    """The sender (B2): calls the real route under the token's identity, or creates the « À
    confirmer »
    request of a level 3 tool."""

    async def call(
        self, identity: McpIdentity, tool: ToolSpec, arguments: dict[str, Any]
    ) -> ToolResult: ...


UserCheck = Callable[[AsyncSession, str], Awaitable[bool]]
# Journal entry for a refusal by the gate: (token's account or `None`, token or `None`, action,
# level, HTTP code). Never content.
RefusalSink = Callable[[str | None, str | None, str, int, int], Awaitable[None]]


@dataclass(frozen=True)
class McpGate:
    """What the gate reads (`app.state.mcp_gate`, set by the composition): the tools, the sender
    (which
    limits and logs), the limits, and the check "does this account still have the right to enter"
    (`ALLOWED_EMAILS` list in Google mode)."""

    tools: ToolRegistry
    dispatcher: Dispatcher
    limiter: RateLimiter
    user_allowed: UserCheck
    refusals: RefusalSink
    known_features: frozenset[str] | None = None
