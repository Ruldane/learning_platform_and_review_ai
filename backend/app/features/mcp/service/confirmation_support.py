"""Ce que les demandes « À confirmer » montrent et ce qu'on en garde (phase 10, P15) : la demande
telle que January la lit (`confirmation_out`, toute la requête), la comparaison de deux verdicts
du contrôle préalable et la purge des demandes closes."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.mcp import McpConfirmation
from app.features.mcp.schemas import McpConfirmationOut, McpRequestField, McpRequestPreview
from app.features.mcp.service.calls import RETENTION_DAYS
from app.mcp.confirm import StoredRequest, preview_fields


def confirmation_out(row: McpConfirmation) -> McpConfirmationOut:
    """La demande telle que January la lit : le résumé, et **toute** la requête gardée (méthode,
    route, cible, champs), les clés masquées."""
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
    """Ce qui compte d'un verdict : `ok` et les raisons (le résumé n'est qu'un texte de plus)."""
    if verdict is None:
        return None
    return bool(verdict.get("ok")), tuple(str(item) for item in verdict.get("reasons") or ())


async def purge_closed_confirmations(
    session_factory: async_sessionmaker[AsyncSession], now: datetime
) -> int:
    """Retire les demandes closes (confirmées, refusées, expirées, échouées) de plus de
    `RETENTION_DAYS` jours : leur requête gardait le texte complet (tâche planifiée, tous comptes :
    une rétention). Une demande encore en attente reste. Rend le nombre de lignes retirées."""
    cutoff = now - timedelta(days=RETENTION_DAYS)
    stmt = delete(McpConfirmation).where(
        McpConfirmation.status != "pending", McpConfirmation.created_at < cutoff
    )
    async with session_factory() as db:
        result = await db.execute(stmt)
        await db.commit()
    return int(getattr(result, "rowcount", 0) or 0)
