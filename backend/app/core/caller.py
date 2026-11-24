"""Who is calling: January's interface or Claude through the MCP server (phase 10, P12).

`MCP_IDENTITY` is only written by the MCP dispatcher (`app/mcp`), never from a header or a
cookie: nothing external can forge it. When empty, the caller is the application. A service
that writes (IDE notes, change history) reads `current_caller()` to know who made the
gesture: the internal professor and Claude go through the same service, only the author changes
(P8)."""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends

from app.core.errors import AppError


@dataclass(frozen=True)
class McpIdentity:
    """The identity set by the MCP dispatcher for the duration of a call: the user who owns the
    token, the token (identifier, never its value), its label, the features it opens and
    its mode (`read` by default)."""

    user_id: str
    token_id: str
    label: str
    features: frozenset[str]
    mode: Literal["read", "write"]


MCP_IDENTITY: ContextVar[McpIdentity | None] = ContextVar("mcp_identity", default=None)
MCP_CONFIRMED: ContextVar[bool] = ContextVar("mcp_confirmed", default=False)


@dataclass(frozen=True)
class Caller:
    """`kind`: `app` (the interface, or an internal task) or `mcp`; `label`: "app" or
    the token's label."""

    kind: Literal["app", "mcp"]
    label: str


def current_caller() -> Caller:
    """`app` if `MCP_IDENTITY` is empty, otherwise the token's label."""
    identity = MCP_IDENTITY.get()
    if identity is None:
        return Caller(kind="app", label="app")
    return Caller(kind="mcp", label=identity.label)


CallerDep = Annotated[Caller, Depends(current_caller)]


def require_confirmed_gesture() -> None:
    """A personal action is allowed from the interface or through a confirmed request."""
    if MCP_IDENTITY.get() is not None and not MCP_CONFIRMED.get():
        raise AppError("mcp_gesture_forbidden", "Confirm this action in Tremplin.", 403)


ConfirmedGesture = Depends(require_confirmed_gesture)
