"""Le journal des appels MCP (phase 10, P19) et l'envoyeur gardé. Chaque appel d'outil laisse une
ligne : l'outil, son niveau, le code de résultat, la durée et les identifiants touchés, **jamais le
contenu** des arguments ni de la réponse. `GuardedDispatcher` enveloppe l'envoyeur de B2 : limites
d'abord (429), journal ensuite, même pour un appel refusé ou en échec."""

import logging
import re
import time
from collections import deque
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.caller import McpIdentity
from app.core.errors import AppError
from app.db.models.mcp import McpCall
from app.features.mcp.repository import CallRepository
from app.features.mcp.schemas import McpCallOut
from app.mcp.limits import RateLimiter
from app.mcp.tools import Dispatcher, ToolResult, ToolSpec

logger = logging.getLogger(__name__)

_ID = re.compile(r"[A-Za-z0-9_-]{1,40}")
_MAX_IDS = 10
_REFUSALS_PER_MINUTE = 30
RETENTION_DAYS = 30  # le journal des appels ne garde que les 30 derniers jours


def clean_ids(ids: Mapping[str, Any]) -> dict[str, Any]:
    """Borne les identifiants et codes issus de l'envoyeur avant leur écriture au journal."""
    kept: dict[str, Any] = {}
    for key, value in list(ids.items())[:_MAX_IDS]:
        if not isinstance(key, str) or not _ID.fullmatch(key):
            continue
        if (
            isinstance(value, int)
            and not isinstance(value, bool)
            or isinstance(value, str)
            and _ID.fullmatch(value)
        ):
            kept[key] = value
    return kept


class CallJournal:
    """Écrit une ligne du journal dans sa propre courte session (l'appel est déjà fait)."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        fallback_user: Callable[[], str | None] = lambda: None,
    ) -> None:
        self._session_factory = session_factory
        self._fallback_user = fallback_user  # l'utilisatrice du mode local, pour un jeton inconnu
        self._refusals: dict[str, deque[float]] = {}

    async def record(
        self,
        identity: McpIdentity,
        tool: ToolSpec,
        code: int,
        duration_ms: int,
        ids: Mapping[str, Any],
        call_id: str | None = None,
    ) -> None:
        """Une panne du journal n'annule pas un appel déjà fait : signalée, sans contenu. Un appel
        refusé par la limite (429) passe par le budget des refus : un client qui insiste n'écrit
        pas une ligne par requête."""
        if code == 429 and not self._refusal_budget(f"{identity.token_id}|limit"):
            return
        try:
            async with self._session_factory() as db:
                await CallRepository(db, identity.user_id).record(
                    identity.token_id,
                    tool.name[:80],
                    tool.level,
                    code,
                    duration_ms,
                    clean_ids(ids),
                    call_id,
                )
                await db.commit()
        except Exception as exc:
            logger.error("MCP : journal de l'appel impossible (%s)", type(exc).__name__)

    def _refusal_budget(self, key: str) -> bool:
        """Au plus 30 lignes par minute et par `key` (jeton et motif du refus : un flot de faux
        jetons ne remplit pas la base ni ne masque un refus d'un autre motif)."""
        now = time.monotonic()
        recent = self._refusals.setdefault(key, deque())
        while recent and recent[0] <= now - 60:
            recent.popleft()
        if len(recent) >= _REFUSALS_PER_MINUTE:
            return False
        recent.append(now)
        return True

    async def refusal(
        self, user_id: str | None, token_id: str | None, action: str, level: int, code: int
    ) -> None:
        """Journalise un refus de la porte (niveau 0 : avant de résoudre l'outil), jamais le
        contenu. Sans compte connu (jeton inconnu), c'est l'utilisatrice du mode local, ou rien."""
        owner = user_id or self._fallback_user()
        if owner is None or not self._refusal_budget(f"{token_id or '-'}|{action}"):
            return
        try:
            async with self._session_factory() as db:
                await CallRepository(db, owner).record(token_id, action[:80], level, code, 0, {})
                await db.commit()
        except Exception as exc:
            logger.error("MCP : journal du refus impossible (%s)", type(exc).__name__)


class GuardedDispatcher:
    """Limites puis journal autour de l'envoyeur réel."""

    def __init__(
        self,
        inner: Dispatcher,
        limiter: RateLimiter,
        journal: CallJournal,
    ) -> None:
        self._inner = inner
        self._limiter = limiter
        self._journal = journal

    async def call(
        self, identity: McpIdentity, tool: ToolSpec, arguments: dict[str, Any]
    ) -> ToolResult:
        started = time.monotonic()
        try:
            await self._limiter.check(identity, tool.level, datetime.now(UTC), bucket=tool.bucket)
            outcome = await self._inner.call(identity, tool, arguments)
        except AppError as exc:
            await self._journal.record(identity, tool, exc.status_code, _since(started), {})
            raise
        except Exception:
            await self._journal.record(identity, tool, 500, _since(started), {})
            raise
        await self._journal.record(
            identity, tool, outcome.code, _since(started), outcome.ids, outcome.call_id
        )
        return outcome


async def purge_old_calls(session_factory: async_sessionmaker[AsyncSession], now: datetime) -> int:
    """Retire du journal les appels de plus de `RETENTION_DAYS` jours (tâche planifiée, tous
    comptes : une rétention, pas une lecture). Rend le nombre de lignes retirées."""
    cutoff = now - timedelta(days=RETENTION_DAYS)
    async with session_factory() as db:
        result = await db.execute(delete(McpCall).where(McpCall.created_at < cutoff))
        await db.commit()
    return int(getattr(result, "rowcount", 0) or 0)


def _since(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


class CallsService:
    """Le journal tel que le voit January : mes appels, les plus récents d'abord."""

    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._calls = CallRepository(db, user_id)

    async def recent(self, limit: int) -> list[McpCallOut]:
        return [McpCallOut.model_validate(row) for row in await self._calls.recent(limit)]
