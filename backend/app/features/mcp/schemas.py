"""MCP access schemas (phase 10, P1, P15 to P19): final from 10.P. A token appears in clear
only once, in `McpTokenCreated`; neither the list nor the log ever return it."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.mcp import ConfirmationStatus, McpMode

__all__ = [
    "McpActionOut",
    "McpCallOut",
    "McpChangeOut",
    "McpConfirmationOut",
    "ConfirmationStatus",
    "McpFeatureOut",
    "McpMode",
    "McpRequestField",
    "McpRequestPreview",
    "McpSettingsIn",
    "McpSettingsOut",
    "McpTokenCreateIn",
    "McpTokenCreated",
    "McpTokenOut",
    "McpUndoOut",
]

LABEL_MAX = 60
ExpiryDays = Literal[1, 7, 30, 90]
ActionKind = Literal["route", "graph"]


class McpSettingsIn(BaseModel):
    """The master switch: false = no token opens anything (off by default)."""

    enabled: bool


class McpSettingsOut(McpSettingsIn):
    pass


class McpFeatureOut(BaseModel):
    """A feature that declares MCP tools: its name and its tools per level."""

    feature: str
    read_actions: int
    write_actions: int
    confirm_actions: int


class McpActionOut(BaseModel):
    """An exposed tool (level table). `kind`: a route or a graph of the application.
    `untrusted`: the fields returned as data, never as instructions."""

    name: str
    feature: str
    kind: ActionKind
    route: str | None
    level: Literal[1, 2, 3]
    summary: str | None
    side_effects: Literal["db", "external"]
    untrusted: list[str]


# "Check all" opens every feature (75 on 23/11); margin for the following ones (D306).
MAX_TOKEN_FEATURES = 120


class McpTokenCreateIn(BaseModel):
    """Creates a token: limited to certain features, read-only by default, 30 days by
    default (1, 7, 30 or 90)."""

    label: str = Field(min_length=1, max_length=LABEL_MAX)
    features: list[str] = Field(min_length=1, max_length=MAX_TOKEN_FEATURES)
    mode: McpMode = "read"
    expires_in_days: ExpiryDays = 30


class McpTokenOut(BaseModel):
    """A token, without its value: it is never seen again."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    features: list[str]
    mode: McpMode
    expires_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class McpTokenCreated(McpTokenOut):
    """The creation response: `token` (`tmcp_…`) is shown only here, once."""

    token: str


class McpRequestField(BaseModel):
    """A field of the request to confirm: its name and its value as text (objects and lists as
    compact JSON), truncated to 500 characters; API keys are masked."""

    name: str
    value_preview: str


class McpRequestPreview(BaseModel):
    """The request that will go out on confirmation, enough to read it in full: method, route
    (the template, without an id), readable label of the target when the route has one (title,
    name; read by the read route of the same resource; a text from the web is wrapped in
    `<donnee_non_fiable>`), **all** the body and parameter fields, and `truncated` if a value
    or the total (4,000 characters) was cut."""

    method: str
    route: str
    target_label: str | None
    fields: list[McpRequestField]
    truncated: bool


class McpConfirmationOut(BaseModel):
    """A "To confirm" request (level 3): what Claude wants to do (a neutral summary and the full
    request in `request`) and the verdict of any prior check. Nothing runs before the
    confirmation."""

    id: str
    token_id: str
    action: str
    summary: str
    request: McpRequestPreview
    precheck: dict[str, Any] | None
    status: ConfirmationStatus
    expires_at: datetime
    decided_at: datetime | None
    created_at: datetime


class McpCallOut(BaseModel):
    """A log line: the tool, the level, the result code, the duration, the ids. Never the
    content. Level 0: call refused before the tool was resolved; empty `token_id`: token not
    recognized."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    token_id: str | None
    action: str
    level: Literal[0, 1, 2, 3]
    code: int
    duration_ms: int
    ids: dict[str, Any]
    created_at: datetime


class McpChangeOut(BaseModel):
    """The changes of a level 2 call: enough to undo them together (`undone_at` set once
    undone)."""

    call_id: str
    action: str
    rows: int
    tables: list[str]
    undone_at: datetime | None
    created_at: datetime


class McpUndoOut(BaseModel):
    """`undone`: the number of rows put back in their previous state."""

    call_id: str
    undone: int
