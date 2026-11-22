"""Un code du navigateur devient le jeton des parcours jouables du relais."""

import secrets
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import KnownSecrets
from app.db.base import utcnow
from app.features.mcp.relay_repository import RelayRepository
from app.features.mcp.relay_schemas import RelayStatus
from app.features.mcp.repository import TokenRepository
from app.features.mcp.service.prefs import PrefsService
from app.features.mcp.service.tokens import TokenService
from app.mcp.auth import hash_token
from app.mcp.registry import Registry
from app.mcp.tools import UserCheck

_CODE_TTL = timedelta(minutes=2)
_TOKEN_DAYS = 30


def required_features(registry: Registry) -> list[str]:
    # Le relais doit aussi pouvoir suivre les graphes lancés directement par l'interface.
    return sorted({"sessions", *registry.graph_features.values()})


class RelayPairingService:
    def __init__(self, db: AsyncSession, registry: Registry) -> None:
        self._db = db
        self._pairs = RelayRepository(db)
        self._features = required_features(registry)

    async def _require_enabled(self, user_id: str) -> None:
        if not (await PrefsService(self._db, user_id).get()).enabled:
            raise AppError("mcp_disabled", "Allume l’accès MCP dans les réglages de Tremplin.", 403)

    async def start(self, user_id: str) -> str:
        await self._require_enabled(user_id)
        code = "trp_" + secrets.token_urlsafe(32)
        KnownSecrets.add(code)
        now = utcnow()
        await self._pairs.issue(user_id, hash_token(code), now + _CODE_TTL, now)
        return code

    async def exchange(self, code: str, user_allowed: UserCheck) -> str:
        now = utcnow()
        claimed = await self._pairs.claim(hash_token(code), now)
        if claimed is None or not await user_allowed(self._db, claimed[0]):
            raise AppError("relay_code_invalid", "Code de connexion invalide ou expiré.", 401)
        user_id, previous = claimed
        await self._require_enabled(user_id)
        await self._revoke_token(user_id, previous)
        token, plain = await TokenService(self._db, user_id).create(
            "Relais Tremplin", self._features, "write", _TOKEN_DAYS
        )
        await self._pairs.attach(user_id, token.id)
        return plain

    async def revoke(self, user_id: str) -> None:
        await self._revoke_token(user_id, await self._pairs.cancel(user_id, utcnow()))

    async def _revoke_token(self, user_id: str, token_id: str | None) -> None:
        if token_id is not None:
            await TokenRepository(self._db, user_id).revoke(token_id, utcnow())

    async def status(self, user_id: str) -> RelayStatus:
        pairing = await self._pairs.get(user_id)
        if pairing is None:
            return RelayStatus(state="unpaired")
        now = utcnow()
        if pairing.code_expires_at is not None and pairing.code_expires_at > now:
            return RelayStatus(state="pending")
        token = (
            await TokenRepository(self._db, user_id).get(pairing.token_id)
            if pairing.token_id is not None
            else None
        )
        if token is None:
            return RelayStatus(state="expired" if pairing.code_expires_at else "unpaired")
        if token.revoked_at is not None:
            return RelayStatus(state="revoked")
        if token.expires_at <= now:
            return RelayStatus(state="expired")
        if not (await PrefsService(self._db, user_id).get()).enabled:
            return RelayStatus(state="disabled")
        missing = sorted(set(self._features) - set(token.features))
        if missing or token.mode != "write":
            return RelayStatus(state="incomplete", missing_features=missing)
        return RelayStatus(state="paired")
