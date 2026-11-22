"""Consentement OAuth lié au compte, consommé avant l’échange et sans jeton en sortie."""

from base64 import urlsafe_b64encode
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from secrets import compare_digest, token_urlsafe

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import new_id
from app.features.calendar.repository import Connections
from app.features.calendar.schemas import CalendarStatus
from app.features.calendar.service.runtime import CalendarRuntime

OAUTH_COOKIE = "tremplin_calendar_oauth"
COOKIE_PATH = "/api/v1/calendar/callback"
STATE_SECONDS = 600


@dataclass(frozen=True, repr=False)
class Credential:
    generation: str
    refresh: str


async def status(rt: CalendarRuntime, db: AsyncSession, user_id: str) -> CalendarStatus:
    if rt.port is None:
        return CalendarStatus(status="unconfigured")
    current = await Connections(db, user_id).current()
    if current and current.revoke_pending:
        return CalendarStatus(status="revocation_pending")
    return CalendarStatus(
        status="connected" if current and current.encrypted_refresh_token else "disconnected"
    )


async def credential(rt: CalendarRuntime, db: AsyncSession, user_id: str) -> Credential | None:
    row = await Connections(db, user_id).current() if rt.port is not None else None
    if row is None or row.revoke_pending or not row.generation or not row.encrypted_refresh_token:
        return None
    return Credential(row.generation, rt.cipher.decrypt(row.encrypted_refresh_token))


def _digest(state: str) -> str:
    return sha256(state.encode()).hexdigest()


async def start(rt: CalendarRuntime, user_id: str, consent: bool) -> tuple[str, str]:
    if not consent:
        raise AppError("calendar_consent_required", "Confirme d’abord la connexion Agenda.", 422)
    port = rt.provider()
    state, verifier = token_urlsafe(32), token_urlsafe(48)
    challenge = urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip("=")
    async with rt.lock(user_id), rt.factory() as db:
        repo = Connections(db, user_id)
        row = await repo.current()
        if row and (row.encrypted_refresh_token or row.revoke_pending):
            raise AppError("calendar_already_connected", "Déconnecte d’abord cet Agenda.", 409)
        if row is None:
            row = await repo.add()
        row.oauth_state_hash = _digest(state)
        row.oauth_expires_at = rt.now() + timedelta(seconds=STATE_SECONDS)
        await db.commit()
    return port.authorization_url(state, challenge), rt.cipher.encrypt(f"{state}:{verifier}")


async def finish(
    rt: CalendarRuntime, user_id: str, state: str | None, code: str | None, cookie: str | None
) -> bool:
    if rt.port is None or not state or not cookie or len(state) > 128:
        return False
    try:
        original, verifier = rt.cipher.decrypt(cookie, ttl=STATE_SECONDS).split(":", 1)
    except (AppError, ValueError):
        return False
    if not compare_digest(_digest(original), _digest(state)):
        return False
    async with rt.lock(user_id):
        async with rt.factory() as db:
            consumed = await Connections(db, user_id).consume(_digest(state), rt.now())
            await db.commit()
        if not consumed or not code or len(code) > 4096:
            return False
        try:
            refresh = await rt.port.exchange(code, verifier)
        except AppError:
            return False
        async with rt.factory() as db:
            row = await Connections(db, user_id).current()
            if row is None:
                await rt.port.revoke(refresh)
                return False
            row.encrypted_refresh_token = rt.cipher.encrypt(refresh)
            row.generation = new_id()
            await db.commit()
    return True


async def disconnect(rt: CalendarRuntime, user_id: str) -> CalendarStatus:
    async with rt.lock(user_id):
        async with rt.factory() as db:
            row = await Connections(db, user_id).current()
            if row is None:
                return await status(rt, db, user_id)
            encrypted = row.encrypted_refresh_token
            row.revoke_pending = bool(encrypted)
            row.generation = row.oauth_state_hash = None
            row.oauth_expires_at = None
            await db.commit()
        if encrypted:
            await rt.provider().revoke(rt.cipher.decrypt(encrypted))
        async with rt.factory() as db:
            row = await Connections(db, user_id).current()
            if row is not None:
                row.encrypted_refresh_token = None
                row.revoke_pending = False
                await db.commit()
            return await status(rt, db, user_id)
