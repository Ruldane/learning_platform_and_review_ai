"""The MCP authentication gate (phase 10, P16): only a `tmcp_…` token opens `/mcp`.

- The token is read **only** from `Authorization: Bearer`: never the session cookie, never
  the query string. Conversely, this token never opens `/api/v1` (the application's
  authenticator reads only the cookie).
- Only the SHA-256 of the token is stored in the database; the plain value exists only at
  creation (shown once). Never logged, never put in an error message.
- `Origin` and `Host` must be local (`localhost`, `127.0.0.1`): protection against "DNS
  rebinding", required by the transport specification.
- Master switch off (default), unknown, expired or revoked token, or an account that no longer
  has the right to enter: refused, nothing executed."""

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import McpIdentity
from app.core.errors import AppError
from app.core.security import KnownSecrets
from app.db.models.mcp import McpPrefs, McpToken
from app.mcp.base import NEVER_EXPOSED_FEATURES
from app.mcp.tools import McpGate

TOKEN_PREFIX = "tmcp_"
_TOKEN = re.compile(r"tmcp_[A-Za-z0-9_-]{43}")  # `token_urlsafe(32)`: 43 characters
_BEARER = re.compile(r"Bearer ([^\s]+)", re.IGNORECASE)
_LOCAL_HOST = re.compile(r"(localhost|127\.0\.0\.1)(:[0-9]{1,5})?", re.IGNORECASE)
_LOCAL_ORIGIN = re.compile(r"https?://(localhost|127\.0\.0\.1)(:[0-9]{1,5})?", re.IGNORECASE)


_LAST_USED_EVERY = timedelta(minutes=1)  # `last_used_at`: at most one write per minute


class McpRefusal(AppError):
    """A refusal by the gate. `user_id` and `token_id`: who the token belongs to, when known
    (`None`: unknown token or refusal before looking it up); for the refusal journal."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        *,
        user_id: str | None = None,
        token_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code, message, status_code, details)
        self.user_id = user_id
        self.token_id = token_id


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    """`(plain, fingerprint)` of a new token: `tmcp_` + 32 random bytes. The plain value is masked
    in the logs from the moment it is created."""
    plain = TOKEN_PREFIX + secrets.token_urlsafe(32)
    KnownSecrets.add(plain)
    return plain, hash_token(plain)


def check_local_origin(request: Request) -> None:
    """403 if `Host` is not local, or if an `Origin` is present and not local."""
    hosts = request.headers.getlist("host")
    if len(hosts) != 1 or not _LOCAL_HOST.fullmatch(hosts[0]):
        raise McpRefusal(
            "host_not_allowed", "The MCP server can only be reached from this machine.", 403
        )
    origins = request.headers.getlist("origin")
    if len(origins) > 1 or (origins and not _LOCAL_ORIGIN.fullmatch(origins[0])):
        raise McpRefusal("origin_not_allowed", "Origin refused: the MCP server is local only.", 403)


async def guard_interface_request(request: Request) -> None:
    """Guard of the MCP management routes (`/api/v1/mcp/*`, interface gesture). An MCP token
    presented here is refused (403) instead of being ignored: a client that replays its token in
    the wrong place gets nothing. In local mode (the API has no authentication), the host and
    origin must also be local: another site cannot reach these routes (DNS rebinding)."""
    for value in request.headers.getlist("authorization"):
        match = _BEARER.fullmatch(value)
        if match is not None and match.group(1).startswith(TOKEN_PREFIX):
            raise AppError(
                "mcp_token_on_api",
                "An MCP token only opens the MCP server: these settings belong to the interface.",
                403,
            )
    if request.app.state.settings.auth_mode == "local":
        check_local_origin(request)


def _bearer(request: Request) -> str:
    """The presented token, or 401. Only one `Authorization` header is accepted."""
    headers = request.headers.getlist("authorization")
    match = _BEARER.fullmatch(headers[0]) if len(headers) == 1 else None
    if match is None or not _TOKEN.fullmatch(match.group(1)):
        raise McpRefusal(
            "mcp_token_invalid",
            'MCP token missing or invalid: send "Authorization: Bearer tmcp_…".',
            401,
        )
    return match.group(1)


async def _find(db: AsyncSession, plain: str) -> McpToken:
    # Only lookup without `user_id`: we do not yet know whose token it is (like the sign-in
    # session, found by its fingerprint).
    digest = hash_token(plain)
    row = (await db.execute(select(McpToken).where(McpToken.hash == digest))).scalar_one_or_none()
    if row is None:
        raise McpRefusal("mcp_token_invalid", "Unknown MCP token.", 401)
    return row


def _refuse(
    token: McpToken,
    code: str,
    message: str,
    status: int,
    details: dict[str, Any] | None = None,
) -> McpRefusal:
    return McpRefusal(
        code, message, status, user_id=token.user_id, token_id=token.id, details=details
    )


def _check_validity(token: McpToken, now: datetime) -> None:
    if token.revoked_at is not None:
        raise _refuse(token, "mcp_token_revoked", "This MCP token has been revoked.", 401)
    if token.expires_at <= now:
        raise _refuse(
            token, "mcp_token_expired", "This MCP token has expired: create a new one.", 401
        )


async def _is_enabled(db: AsyncSession, user_id: str) -> bool:
    stmt = select(McpPrefs.enabled).where(McpPrefs.user_id == user_id)
    return bool((await db.execute(stmt)).scalar_one_or_none())


async def authenticate(request: Request, db: AsyncSession) -> McpIdentity:
    """The identity of the presented token, or `AppError`: 403 (origin, switch off), 401 (token
    missing, unknown, expired, revoked, account removed). Sets `last_used_at` (the calling
    session must validate)."""
    check_local_origin(request)
    gate: McpGate | None = getattr(request.app.state, "mcp_gate", None)
    if gate is None:
        raise AppError("mcp_unavailable", "The MCP server is not ready.", 503)
    plain = _bearer(request)
    token = await _find(db, plain)
    KnownSecrets.add(plain)  # a valid token is masked in the logs, even after a restart
    now = datetime.now(UTC)
    _check_validity(token, now)
    try:  # rough cap before any write: a request loop writes nothing
        await gate.limiter.check_request(token.id, now)
    except AppError as exc:
        raise _refuse(token, exc.code, exc.message, exc.status_code, exc.details) from exc
    if not await gate.user_allowed(db, token.user_id):
        raise _refuse(
            token, "mcp_token_invalid", "This account no longer has access to the app.", 401
        )
    if not await _is_enabled(db, token.user_id):
        raise _refuse(
            token,
            "mcp_disabled",
            "MCP access is turned off: turn it back on in Tremplin's settings.",
            403,
        )
    if token.last_used_at is None or now - token.last_used_at >= _LAST_USED_EVERY:
        await db.execute(update(McpToken).where(McpToken.id == token.id).values(last_used_at=now))
    features = frozenset(str(name) for name in token.features) - NEVER_EXPOSED_FEATURES
    mode: Literal["read", "write"] = "write" if token.mode == "write" else "read"
    return McpIdentity(
        user_id=token.user_id,
        token_id=token.id,
        label=token.label,
        features=features,
        mode=mode,
    )
