"""What the pending confirmations show and what is kept of them (phase 10, P15): the request as
January reads it (`confirmation_out`, the whole request), the comparison of two verdicts of
the preliminary check, and the purge of closed requests."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.mcp import McpConfirmation
from app.features.mcp.schemas import McpConfirmationOut, McpRequestField, McpRequestPreview
from app.features.mcp.service.calls import RETENTION_DAYS
from app.mcp.confirm import StoredRequest, preview_fields


def confirmation_out(row: McpConfirmation) -> McpConfirmationOut:
    """The request as January reads it: the summary and **all** of the stored request (method,
    route, target, fields), with keys masked."""
    stored = StoredRequest.from_json(row.request)
    fields, truncated = preview_fields(stored.request)
    preview = McpRequestPreview(
        method=stored.request.method,
        route=stored.route or stored.request.path,
        target_label=stored.target_label,
        fields=[McpRequestField(name=name, value_preview=text) for name, text in fields],
        truncated=truncated,
    )
    return McpConfirmationOut(
        id=row.id,
        token_id=row.token_id,
        action=row.action,
        summary=row.summary,
        request=preview,
        precheck=row.precheck,
        status=row.status,  # type: ignore[arg-type]
        expires_at=row.expires_at,
        decided_at=row.decided_at,
        created_at=row.created_at,
    )


def verdict_key(verdict: dict[str, Any] | None) -> tuple[bool, tuple[str, ...]] | None:
    """What matters in a verdict: `ok` and the reasons (the summary is just more text)."""
    if verdict is None:
        return None
    return bool(verdict.get("ok")), tuple(str(item) for item in verdict.get("reasons") or ())


async def purge_closed_confirmations(
    session_factory: async_sessionmaker[AsyncSession], now: datetime
) -> int:
    """Removes closed requests (confirmed, refused, expired, failed) older than `RETENTION_DAYS`
    days: their request kept the full text (scheduled task, all accounts: a retention job). A
    request still pending stays. Returns the number of rows removed."""
    cutoff = now - timedelta(days=RETENTION_DAYS)
    stmt = delete(McpConfirmation).where(
        McpConfirmation.status != "pending", McpConfirmation.created_at < cutoff
    )
    async with session_factory() as db:
        result = await db.execute(stmt)
        await db.commit()
    return int(getattr(result, "rowcount", 0) or 0)
