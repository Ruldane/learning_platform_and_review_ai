"""Accès aux tables du MCP (phase 10) : jetons, interrupteur général, journal des appels. Tout est
filtré par `user_id`. La recherche d'un jeton par son empreinte (sans `user_id`, on ne sait pas
encore à qui il est) vit dans `app.mcp.auth`, seule."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.mcp import McpCall, McpChange, McpConfirmation, McpPrefs, McpToken
from app.db.repository import UserScopedRepository


class TokenRepository(UserScopedRepository[McpToken]):
    model = McpToken

    async def newest_first(self) -> list[McpToken]:
        stmt = (
            select(McpToken)
            .where(McpToken.user_id == self.user_id)
            .order_by(McpToken.created_at.desc(), McpToken.id)
        )
        return list((await self.session.execute(stmt)).scalars())

    async def revoke(self, token_id: str, now: datetime) -> McpToken | None:
        """Pose `revoked_at` (jamais d'effacement : le journal garde son `token_id`) ; un jeton
        déjà révoqué garde sa date."""
        row = await self.get(token_id)
        if row is not None and row.revoked_at is None:
            row.revoked_at = now
            await self.session.flush()
        return row


class PrefsRepository:
    """L'interrupteur général, une ligne par compte (absente = coupé)."""

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def get(self) -> McpPrefs | None:
        stmt = select(McpPrefs).where(McpPrefs.user_id == self.user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def set_enabled(self, enabled: bool) -> McpPrefs:
        row = await self.get()
        if row is None:
            row = McpPrefs(user_id=self.user_id, enabled=enabled)
            self.session.add(row)
        else:
            row.enabled = enabled
        await self.session.flush()
        return row


class CallRepository(UserScopedRepository[McpCall]):
    model = McpCall

    async def record(
        self,
        token_id: str | None,
        action: str,
        level: int,
        code: int,
        duration_ms: int,
        ids: dict[str, Any],
        call_id: str | None = None,
    ) -> McpCall:
        """`call_id` : l'identifiant imposé à la ligne (celui des changements de l'appel)."""
        extra: dict[str, Any] = {} if call_id is None else {"id": call_id}
        return await self.add(
            **extra,
            token_id=token_id,
            action=action,
            level=level,
            code=code,
            duration_ms=duration_ms,
            ids=ids,
        )

    async def launches_since(self, actions: frozenset[str], since: datetime) -> int:
        """Les lancements de parcours réussis depuis `since` (journal, jamais le contenu) : les
        appels des outils `actions` qui ont abouti (code 2xx), sans refus ni erreur."""
        if not actions:
            return 0
        stmt = select(func.count()).where(
            McpCall.user_id == self.user_id,
            McpCall.action.in_(actions),
            McpCall.created_at >= since,
            McpCall.code >= 200,
            McpCall.code < 300,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def recent(self, limit: int) -> list[McpCall]:
        stmt = (
            select(McpCall)
            .where(McpCall.user_id == self.user_id)
            .order_by(McpCall.created_at.desc(), McpCall.id)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars())


class ConfirmationRepository(UserScopedRepository[McpConfirmation]):
    """Les demandes « À confirmer » ; chaque changement d'état est un `UPDATE` conditionnel (état
    attendu dans le `WHERE`) : deux clics en même temps ne passent jamais tous les deux."""

    model = McpConfirmation

    async def pending_count(self, token_id: str, now: datetime) -> int:
        stmt = select(func.count()).where(
            McpConfirmation.user_id == self.user_id,
            McpConfirmation.token_id == token_id,
            McpConfirmation.status == "pending",
            McpConfirmation.expires_at > now,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def recent(self, limit: int) -> list[McpConfirmation]:
        stmt = (
            select(McpConfirmation)
            .where(McpConfirmation.user_id == self.user_id)
            .order_by(McpConfirmation.created_at.desc(), McpConfirmation.id)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars())

    async def transition(
        self,
        confirmation_id: str,
        source: str,
        target: str,
        now: datetime,
        *,
        live_only: bool = False,
        result_code: int | None = None,
    ) -> bool:
        """Passe la demande de `source` à `target` si elle y est encore ; `live_only` : seulement
        si elle n'a pas expiré. Vrai si cette demande-ci a fait le passage."""
        conditions = [
            McpConfirmation.id == confirmation_id,
            McpConfirmation.user_id == self.user_id,
            McpConfirmation.status == source,
        ]
        if live_only:
            conditions.append(McpConfirmation.expires_at > now)
        values: dict[str, Any] = {"status": target, "decided_at": now}
        if result_code is not None:
            values["result_code"] = result_code
        result = await self.session.execute(
            update(McpConfirmation).where(*conditions).values(**values)
        )
        return int(getattr(result, "rowcount", 0) or 0) == 1

    async def set_precheck(self, confirmation_id: str, precheck: dict[str, Any] | None) -> None:
        """Remplace le verdict d'une demande encore en attente (contrôle rejoué au clic)."""
        await self.session.execute(
            update(McpConfirmation)
            .where(
                McpConfirmation.id == confirmation_id,
                McpConfirmation.user_id == self.user_id,
                McpConfirmation.status == "pending",
            )
            .values(precheck=precheck)
        )


async def expire_pending(session: AsyncSession, now: datetime) -> int:
    """Toute demande en attente dont l'heure est passée devient « expirée » (tâche planifiée, tous
    comptes : un entretien, pas une lecture de données)."""
    stmt = (
        update(McpConfirmation)
        .where(McpConfirmation.status == "pending", McpConfirmation.expires_at <= now)
        .values(status="expired", decided_at=now)
    )
    return int(getattr(await session.execute(stmt), "rowcount", 0) or 0)


class ChangeRepository(UserScopedRepository[McpChange]):
    """Les changements gardés par appel (historique des écritures de niveau 2)."""

    model = McpChange

    async def calls(self, limit: int) -> list[tuple[str, int, datetime, datetime | None]]:
        """Un tuple par appel : `(call_id, lignes, date, annulé le)`, le plus récent d'abord."""
        stmt = (
            select(
                McpChange.call_id,
                func.count(),
                func.max(McpChange.created_at),
                func.min(McpChange.undone_at),
                func.count(McpChange.undone_at),
            )
            .where(McpChange.user_id == self.user_id)
            .group_by(McpChange.call_id)
            .order_by(func.max(McpChange.created_at).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        # `annulé le` seulement si toutes les lignes le sont.
        return [(r[0], r[1], r[2], r[3] if r[4] == r[1] else None) for r in rows]

    async def tables(self, call_ids: list[str]) -> dict[str, list[str]]:
        stmt = (
            select(McpChange.call_id, McpChange.table_name)
            .where(McpChange.user_id == self.user_id, McpChange.call_id.in_(call_ids))
            .distinct()
        )
        found: dict[str, list[str]] = {}
        for call_id, table in (await self.session.execute(stmt)).all():
            found.setdefault(call_id, []).append(table)
        return {key: sorted(value) for key, value in found.items()}

    async def actions(self, call_ids: list[str]) -> dict[str, str]:
        """L'outil de chaque appel (la ligne du journal porte l'identifiant de l'appel)."""
        stmt = select(McpCall.id, McpCall.action).where(
            McpCall.user_id == self.user_id, McpCall.id.in_(call_ids)
        )
        return {call_id: action for call_id, action in (await self.session.execute(stmt)).all()}
