"""The « À confirmer » requests as seen by the adapter (phase 10, P15): the guarded request as it
would be sent, its neutral summary, the full preview January reads before confirming
(`preview_fields`), and the port the sender uses to file it. The life of the request (state,
expiry, confirmation, refusal) is in `features/mcp/service/confirmations.py`."""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Protocol

from app.core.caller import McpIdentity
from app.mcp.arguments import ToolRequest, clip
from app.mcp.base import PrecheckInput, Verdict
from app.mcp.envelope import scrub_text
from app.mcp.tools import ToolSpec

logger = logging.getLogger(__name__)

CONFIRMATION_TTL = timedelta(hours=24)
MAX_PENDING_PER_TOKEN = 20
PRECHECK_TIMEOUT_S = 60.0
_PREVIEW = 60
_PREVIEW_FIELDS = 6
FIELD_PREVIEW_MAX = 500  # characters shown per field
TOTAL_PREVIEW_MAX = 4_000  # characters shown for the whole request


@dataclass(frozen=True)
class StoredRequest:
    """What is kept of a request: the tool, the full request (method, path, parameters, body) and
    the identity that made it (label, features, token mode). The account and the token are in
    the request's row, not here."""

    tool: str
    request: ToolRequest
    label: str
    features: tuple[str, ...]
    mode: str
    route: str | None = None  # the route template (`/applications/{application_id}`)
    target_label: str | None = None  # the readable label of the target, read at creation

    def to_json(self) -> dict[str, Any]:
        request = self.request
        return {
            "tool": self.tool,
            "method": request.method,
            "path": request.path,
            "params": request.params,
            "body": request.body,
            "form": request.form,
            "merge_path": request.merge_path,
            "merge_fields": list(request.merge_fields) if request.merge_fields else None,
            "route": self.route,
            "target_label": self.target_label,
            "identity": {"label": self.label, "features": list(self.features), "mode": self.mode},
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StoredRequest":
        who = data["identity"]
        fields = data.get("merge_fields")
        request = ToolRequest(
            method=data["method"],
            path=data["path"],
            params=dict(data.get("params") or {}),
            body=data.get("body"),
            form=bool(data.get("form")),
            merge_path=data.get("merge_path"),
            merge_fields=tuple(fields) if fields else None,
        )
        return cls(
            data["tool"],
            request,
            who["label"],
            tuple(who["features"]),
            who["mode"],
            data.get("route"),
            data.get("target_label"),
        )

    def identity(self, user_id: str, token_id: str) -> McpIdentity:
        """The identity under which the request runs: the one recorded at creation."""
        mode: Literal["read", "write"] = "write" if self.mode == "write" else "read"
        return McpIdentity(
            user_id=user_id,
            token_id=token_id,
            label=self.label,
            features=frozenset(self.features),
            mode=mode,
        )


class Pending(Protocol):
    """What the sender reads from a created request."""

    @property
    def id(self) -> str: ...

    @property
    def expires_at(self) -> datetime: ...


class ConfirmationPort(Protocol):
    """Filing of a request (provided by the `mcp` feature, for a given account). Raises `AppError`
    429 `too_many_pending` at 20 pending requests for the token."""

    async def ensure_room(self, identity: McpIdentity) -> None:
        """Raises `AppError` 429 `too_many_pending` if the token already has 20 pending requests (to
        be
        checked before the precheck, which may cost a model call)."""
        ...

    async def create(
        self,
        identity: McpIdentity,
        stored: StoredRequest,
        summary: str,
        precheck: dict[str, Any] | None,
    ) -> Pending: ...


def _render(value: Any) -> str:
    """A value as text: as is for text, compact JSON otherwise (objects, lists...)."""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def preview_fields(request: ToolRequest) -> tuple[list[tuple[str, str]], bool]:
    """**All** the fields of the request (parameters then body), each rendered as text, the keys
    masked before cutting (a key cut in two is never left readable), 500 characters per field
    and 4,000 in total. Returns `(fields, truncated)`; a cut field ends with "…", a field beyond
    the total is named with an empty preview."""
    items: list[tuple[str, Any]] = list(request.params.items())
    if isinstance(request.body, dict):
        items += list(request.body.items())
    elif request.body is not None:
        items.append(("body", request.body))
    fields: list[tuple[str, str]] = []
    remaining = TOTAL_PREVIEW_MAX
    truncated = False
    for name, value in items:
        text = scrub_text(_render(value))
        room = min(FIELD_PREVIEW_MAX, remaining)
        if len(text) > room:
            truncated = True
            text = text[:room] + ("…" if room else "")
            remaining -= room
        else:
            remaining -= len(text)
        fields.append((clip(name, 60), text))
    return fields, truncated


def summarize(tool: ToolSpec, request: ToolRequest) -> str:
    """The summary January reads: what the tool does, the target route and, for each argument (6 at
    most), its name and a short preview in quotes. Keys are masked, nothing is interpreted: a
    trapped text stays a text."""
    what = (tool.summary or tool.description).strip()
    parts: list[str] = []
    fields = dict(request.params)
    if isinstance(request.body, dict):
        fields.update(request.body)
    for name, value in list(fields.items())[:_PREVIEW_FIELDS]:
        if isinstance(value, str | int | float | bool):
            parts.append(f'{clip(name, 30)} = "{clip(scrub_text(str(value)), _PREVIEW)}"')
        else:
            parts.append(clip(name, 30))
    text = f"{what} — {request.method} {request.path}"
    if parts:
        text += " — " + " ; ".join(parts)
    return text[:1000]


async def check_before_confirmation(
    identity: McpIdentity, tool: ToolSpec, request: ToolRequest
) -> dict[str, Any] | None:
    if tool.precheck is None:
        return None
    asked = PrecheckInput(
        user_id=identity.user_id,
        method=request.method,
        path=request.path,
        params=request.params,
        body=request.body,
    )
    try:
        verdict = await asyncio.wait_for(tool.precheck(asked), PRECHECK_TIMEOUT_S)
    except Exception as exc:
        logger.error("MCP: precheck failed (%s)", type(exc).__name__)
        verdict = Verdict(ok=False, reasons=("The precheck could not be run.",))
    return {"ok": verdict.ok, "reasons": list(verdict.reasons), "summary": verdict.summary}
