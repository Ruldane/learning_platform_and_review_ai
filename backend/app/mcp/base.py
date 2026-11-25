"""MCP declarations (phase 10, P11): what a feature exposes to Claude, by allowlist.

No route is exposed on its own: each route of `FEATURE_ROUTERS` is either **declared**
(`McpAction`, with its level) or **excluded with a reason** (`FeatureMcp.excluded`); a test
guard fails otherwise. The same goes for each graph of `GRAPHS` (`McpGraph`).

Levels: 1 read; 2 reversible write (history and undo, database only); 3 action that cannot be
undone (deletion, sending, write to the master profile): the call creates a « À confirmer »
request, and nothing happens until January confirms it; 4 never exposed (`NEVER_EXPOSED_FEATURES`,
and in `settings`: keys, models per level, per-agent overrides, secrets). The other settings go
through the dedicated action `settings_update_preferences` (level 2), which reads the object
(`merge_from`), changes only the non-sensitive fields listed (`body_fields`) and rewrites the
whole; a raw `PUT /settings` stays excluded, as it also carries the models. A route declared
with `body_fields` is allowed even if its feature has sensitive fields (D1)."""

import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

Level = Literal[1, 2, 3]

# Level 4: never exposed to MCP (sign-in and administration of MCP access).
NEVER_EXPOSED_FEATURES = frozenset({"auth", "mcp"})

# POSTs that only read (search): the only ones that can be level 1 without being a GET,
# otherwise a read-only token could not search the memory.
READ_ONLY_POSTS = frozenset({"POST /memory/search"})


class McpExclusion(StrEnum):
    AUTH = "Level 4 — authentication and sign-in sessions."
    MCP_ADMIN = "Level 4 — MCP tokens, pairing, rights and confirmations."
    MODEL_SETTINGS = "Level 4 — API keys and model choices."
    BRAIN_SYNC = "Level 4 — token and protected channel of the Brain relay."
    CALENDAR_OAUTH = "Level 4 — OAuth consent and Calendar connection."
    IDE_RIGHTS = "Level 4 — changes to write rights and token caps."
    SHARING_TOKEN = "Level 4 — issuing or using the mentor's guest access."
    INTEGRATION_TOKEN = "Level 4 — consent and pairing of the integration token."


# Grammar of the `untrusted` paths: paths pointing into `data` of the JSON response (the root
# is `data`); `[]` = "each element of a list"; a response whose root is a list is written
# `[].field`. Examples: `"description"`, `"items[].description"`, `"postings[].company"`,
# `"[].title"`, `"[].company.name"`. Neither `*`, nor an index, nor an empty path.
_UNTRUSTED_PATH = re.compile(r"(\[\]\.)?[a-z_][a-z0-9_]*(\[\])?(\.[a-z_][a-z0-9_]*(\[\])?)*")


def untrusted_paths_valid(paths: tuple[str, ...]) -> bool:
    """All paths follow the grammar above (true for no path). Wrapping the fields ("untrusted data"
    fence) is the job of the MCP server (B2)."""
    return all(_UNTRUSTED_PATH.fullmatch(path) for path in paths)


@dataclass(frozen=True)
class PrecheckInput:
    """What a precheck (level 3) receives: the request as it would be sent (method, path,
    parameters,
    body) and the user concerned."""

    user_id: str
    method: str
    path: str
    params: Mapping[str, Any]
    body: Any = None


@dataclass(frozen=True)
class Verdict:
    """The result of a precheck, kept in the « À confirmer » request: `ok` false = the request says
    why
    it is discouraged (`reasons`, neutral texts), never a silent block. January decides."""

    ok: bool
    reasons: tuple[str, ...] = ()
    summary: str | None = None


@dataclass(frozen=True)
class McpAction:
    """An exposed route: `route` = `"POST /postings"` (method and path without `/api/v1`); `name` =
    the tool name; `side_effects="external"` (vectors, files, external call) forces level 3, as
    undo covers only the database (P14); `untrusted` = paths of the response fields that come
    from the web (rendered as data; grammar: `untrusted_paths_valid`); `precheck` = precheck of a
    level 3 action (e.g. the profile honesty validator); `body_fields` (if not `None`) = allowlist
    of the body fields the MCP may send, any other field is refused; `merge_from` = a GET route
    whose response is the base: the adapter reads it, replaces only `body_fields` and returns the
    whole (requires `body_fields`). An `external` effect is level 3 at least (`ValueError`
    otherwise). `response_fields` (if not `None`): the adapter returns only these keys of the
    response's root object (of each object if it is a list), e.g. the preferences without the
    models; `encoding="form"`: the text fields of the body go as `multipart/form-data` (no file),
    for a form. `launches`: the name of the graph the route launches (a flow of `ROUTE_ONLY`);
    the call counts toward the daily cap on graph launches (M11)."""

    route: str
    level: Level
    name: str
    summary: str | None = None
    side_effects: Literal["db", "external"] = "db"
    untrusted: tuple[str, ...] = ()
    precheck: Callable[[PrecheckInput], Awaitable[Verdict]] | None = None
    body_fields: frozenset[str] | None = None
    merge_from: str | None = None
    response_fields: frozenset[str] | None = None
    encoding: Literal["json", "form"] = "json"
    launches: str | None = None
    artifact: bool = False
    bucket: Literal["code_run"] | None = None
    manual_url: str | None = None

    def __post_init__(self) -> None:
        if self.side_effects == "external" and self.level == 2:
            raise ValueError("an external side effect is level 3 (P14)")
        if self.merge_from is not None and (
            self.body_fields is None or not self.merge_from.startswith("GET ")
        ):
            raise ValueError("merge_from is a GET route and requires body_fields")
        if not untrusted_paths_valid(self.untrusted):
            raise ValueError("untrusted path outside the grammar")
        if self.manual_url and (
            self.level != 1 or not re.fullmatch(r"/[a-z0-9][a-z0-9/-]*", self.manual_url)
        ):
            raise ValueError("a link to a Tremplin page is a read")


@dataclass(frozen=True)
class McpGraph:
    """An application graph launched by Claude (level 2): the internal agents do the work, and
    Claude
    follows the session to the result."""

    graph: str
    level: Literal[2] = 2
    summary: str | None = None
    untrusted: tuple[str, ...] = ()
    # A flow that has only its launch route (`ROUTE_ONLY`): no `graph_<name>` tool (it would be
    # refused with 409); the declaration only serves to mark the result's fields of the session as
    # untrusted when Claude follows it.
    follow_only: bool = False
    # The flow has no paid tool. Its `graph_<name>` name is used by `agents_play_start`.
    play_only: bool = False

    def __post_init__(self) -> None:
        if not untrusted_paths_valid(self.untrusted):
            raise ValueError("untrusted path outside the grammar")


@dataclass(frozen=True)
class FeatureMcp:
    """The actions, graphs, protected routes and transport equivalents."""

    feature: str
    actions: tuple[McpAction, ...] = ()
    graphs: tuple[McpGraph, ...] = ()
    excluded: Mapping[str, McpExclusion] = field(default_factory=dict)
    # These routes can only be called under the played model context.
    play_actions: tuple[McpAction, ...] = ()
    # A transport operation represented by an equivalent tool.
    alternatives: Mapping[str, str] = field(default_factory=dict)
