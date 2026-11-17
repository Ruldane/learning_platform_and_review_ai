"""Le journal des agents : les appels journalisés d'une utilisatrice, du plus récent au plus
ancien, par pages. Le curseur `before` est opaque : l'instant et l'identifiant du dernier appel
de la page, en base64 sans remplissage (`iso|id`)."""

import base64
import binascii
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.costs.repository import LlmCallRepository
from app.features.costs.schemas import AgentCallOut, AgentCallPage

_MAX_ID_LENGTH = 36  # `UserScopedMixin.id` : un UUID


def encode_cursor(at: datetime, call_id: str) -> str:
    """Le curseur qui désigne l'appel `call_id` fait à l'instant `at` (rendu en UTC)."""
    raw = f"{at.astimezone(UTC).isoformat()}|{call_id}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _bad_cursor() -> AppError:
    # Ni le curseur reçu ni la cause ne sont recopiés : `details.fields` nomme le champ seul.
    return AppError(
        "validation_error",
        "Requête invalide : vérifie les champs signalés.",
        422,
        {"fields": ["before"]},
    )


def decode_cursor(raw: str) -> tuple[datetime, str]:
    """L'instant (UTC, avec fuseau) et l'identifiant d'un curseur ; 422 `before` s'il est
    illisible : base64 invalide, texte qui n'est pas de l'UTF-8, date sans fuseau, identifiant
    vide ou trop long."""
    try:
        padded = raw + "=" * (-len(raw) % 4)
        text = base64.b64decode(padded, altchars=b"-_", validate=True).decode("utf-8")
        stamp, separator, call_id = text.partition("|")
        at = datetime.fromisoformat(stamp)
    except (binascii.Error, ValueError):  # `UnicodeDecodeError` est une `ValueError`
        raise _bad_cursor() from None
    if not separator or at.tzinfo is None or not 0 < len(call_id) <= _MAX_ID_LENGTH:
        raise _bad_cursor()
    return at.astimezone(UTC), call_id


def _out(row: Row[*tuple[Any, ...]]) -> AgentCallOut:
    return AgentCallOut(
        id=row.id,
        at=row.created_at,
        session_id=row.session_id,
        graph=row.graph,
        agent=row.agent,
        provider=row.provider,
        model=row.model,
        tokens_in=row.tokens_in,
        tokens_out=row.tokens_out,
        latency_ms=row.latency_ms,
        cost_usd=row.cost_usd,
        estimated=row.estimated,
    )


async def list_calls(
    db: AsyncSession,
    user_id: str,
    *,
    before: str | None,
    limit: int,
    agent: str | None,
    graph: str | None,
) -> AgentCallPage:
    """Une page de `limit` appels au plus ; `next_before` n'existe que s'il en reste après."""
    cursor = decode_cursor(before) if before is not None else None
    # Un appel de plus que demandé : sa seule présence dit qu'il y a une page suivante.
    rows = await LlmCallRepository(db, user_id).page(
        before=cursor, limit=limit + 1, agent=agent, graph=graph
    )
    shown = rows[:limit]
    more = len(rows) > limit
    last = shown[-1] if shown else None
    return AgentCallPage(
        items=[_out(row) for row in shown],
        next_before=encode_cursor(last.created_at, last.id) if more and last else None,
    )
