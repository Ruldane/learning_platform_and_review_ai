"""Les demandes « À confirmer » (phase 10, P15) : un outil de niveau 3 ne s'exécute jamais de
lui-même, il laisse une demande ici. January la confirme (la requête s'exécute **une seule fois**,
sous l'identité enregistrée), la refuse, ou elle expire au bout de 24 h. Chaque passage d'état
est un
`UPDATE` conditionnel : deux clics en même temps, ou un clic sur une demande expirée ou refusée, ne
font jamais tourner la requête deux fois ni après coup."""

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.caller import McpIdentity
from app.core.errors import AppError
from app.features.mcp.repository import (
    CallRepository,
    ConfirmationRepository,
    TokenRepository,
    expire_pending,
)
from app.features.mcp.schemas import McpConfirmationOut
from app.mcp.confirm import CONFIRMATION_TTL, MAX_PENDING_PER_TOKEN, StoredRequest
from app.mcp.tools import ToolResult

logger = logging.getLogger(__name__)

Executor = Callable[[McpIdentity, StoredRequest], Awaitable[ToolResult]]
LIST_LIMIT = 100


async def expire_due(session_factory: async_sessionmaker[AsyncSession], now: datetime) -> int:
    """Les demandes en attente dont l'heure est passée deviennent « expirées » (tâche planifiée).
    Rend leur nombre."""
    async with session_factory() as db:
        count = await expire_pending(db, now)
        await db.commit()
    return count


def _closed(status: str) -> AppError:
    names = {"confirmed": "déjà confirmée", "refused": "refusée", "expired": "expirée"}
    state = names.get(status, "déjà traitée")
    return AppError("confirmation_closed", f"Cette demande est {state} : rien à faire.", 409)


def _not_found() -> AppError:
    return AppError("confirmation_not_found", "Demande introuvable.", 404)


class ConfirmationService:
    """Les demandes d'un compte. `execute` : l'envoyeur qui rejoue la requête enregistrée (absent
    pour la création, la liste et le refus)."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        user_id: str,
        execute: Executor | None = None,
    ) -> None:
        self._factory = session_factory
        self._user_id = user_id
        self._execute = execute

    def _repo(self, db: AsyncSession) -> ConfirmationRepository:
        return ConfirmationRepository(db, self._user_id)

    async def create(
        self,
        identity: McpIdentity,
        stored: StoredRequest,
        summary: str,
        precheck: dict[str, Any] | None,
    ) -> McpConfirmationOut:
        """Range la demande (24 h) ; 429 `too_many_pending` à 20 demandes en attente pour ce
        jeton."""
        now = datetime.now(UTC)
        async with self._factory() as db:
            repo = self._repo(db)
            if await repo.pending_count(identity.token_id, now) >= MAX_PENDING_PER_TOKEN:
                raise AppError(
                    "too_many_pending",
                    f"{MAX_PENDING_PER_TOKEN} demandes sont déjà en attente pour ce jeton : "
                    "January doit en confirmer ou en refuser avant d'en ajouter.",
                    429,
                    {"limit": MAX_PENDING_PER_TOKEN},
                )
            row = await repo.add(
                token_id=identity.token_id,
                action=stored.tool[:80],
                request=stored.to_json(),
                summary=summary,
                precheck=precheck,
                status="pending",
                expires_at=now + CONFIRMATION_TTL,
            )
            created = McpConfirmationOut.model_validate(row)
            await db.commit()
        return created

    async def list(self) -> list[McpConfirmationOut]:
        """Mes demandes, les plus récentes d'abord (les périmées sont d'abord marquées)."""
        async with self._factory() as db:
            await expire_pending(db, datetime.now(UTC))
            rows = await self._repo(db).recent(LIST_LIMIT)
            listed = [McpConfirmationOut.model_validate(row) for row in rows]
            await db.commit()
        return listed

    async def get(self, confirmation_id: str) -> McpConfirmationOut:
        async with self._factory() as db:
            row = await self._repo(db).get(confirmation_id)
            if row is None:
                raise _not_found()
            return McpConfirmationOut.model_validate(row)

    async def expire_due(self) -> int:
        return await expire_due(self._factory, datetime.now(UTC))

    async def refuse(self, confirmation_id: str) -> McpConfirmationOut:
        """Refuse : elle ne s'exécutera jamais. 409 si elle est déjà décidée ou expirée."""
        now = datetime.now(UTC)
        async with self._factory() as db:
            repo = self._repo(db)
            row = await repo.get(confirmation_id)
            if row is None:
                raise _not_found()
            status = row.status
            if not await repo.transition(
                confirmation_id, "pending", "refused", now, live_only=True
            ):
                await repo.transition(confirmation_id, "pending", "expired", now)
                await db.commit()
                raise _closed("expired" if status == "pending" else status)
            await db.commit()
        return await self.get(confirmation_id)

    async def confirm(self, confirmation_id: str) -> ToolResult:
        """Exécute la demande, une seule fois, sous l'identité enregistrée. 404 inconnue ; 409
        expirée (elle ne tournera jamais), refusée, déjà traitée, ou jeton révoqué depuis."""
        if self._execute is None:
            raise RuntimeError("confirmation sans envoyeur")
        now = datetime.now(UTC)
        async with self._factory() as db:
            stored, token_id, action = await self._claim(db, confirmation_id, now)
        started = time.monotonic()
        identity = stored.identity(self._user_id, token_id)
        try:
            result = await self._execute(identity, stored)
        except Exception as exc:  # la demande est prise : elle ne repart pas, elle échoue
            logger.error("MCP : exécution d'une demande impossible (%s)", type(exc).__name__)
            error = {"error": {"code": "execution_failed", "message": "L'exécution a échoué."}}
            result = ToolResult(data=error, code=500)
        elapsed = round((time.monotonic() - started) * 1000)
        async with self._factory() as db:
            status = "failed" if result.is_error else "confirmed"
            await self._repo(db).transition(
                confirmation_id, "confirmed", status, now, result_code=result.code
            )
            await CallRepository(db, self._user_id).record(
                token_id, f"{action}:confirm"[:80], 3, result.code, elapsed, dict(result.ids)
            )
            await db.commit()
        return result

    async def _claim(
        self, db: AsyncSession, confirmation_id: str, now: datetime
    ) -> tuple[StoredRequest, str, str]:
        """Prend la demande (passage atomique « en attente » -> « confirmée »), ou refuse."""
        repo = self._repo(db)
        row = await repo.get(confirmation_id)
        if row is None:
            raise _not_found()
        if row.status == "pending" and row.expires_at <= now:
            await repo.transition(confirmation_id, "pending", "expired", now)
            await db.commit()
            raise _closed("expired")
        if row.status != "pending":
            raise _closed(row.status)
        token = await TokenRepository(db, self._user_id).get(row.token_id)
        if token is None or token.revoked_at is not None:
            await repo.transition(confirmation_id, "pending", "refused", now)
            await db.commit()
            raise AppError(
                "token_revoked",
                "Le jeton qui a fait cette demande est révoqué : la demande est refusée.",
                409,
            )
        stored = StoredRequest.from_json(row.request)
        if not await repo.transition(confirmation_id, "pending", "confirmed", now, live_only=True):
            await db.commit()
            raise _closed("confirmed")
        await db.commit()
        return stored, row.token_id, row.action
