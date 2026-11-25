"""Google sign-in, from start to return (P5, P6, P10): the `tremplin_oauth` cookie keeps the
`state`, PKCE verifier and `nonce` (encrypted, 10 minutes); on return, nothing is created until
everything is checked. Each failure becomes a code (`/login?error=<code>`).

No authorization code, `state`, verifier, token, e-mail, `sub` or `login_hint` is logged: only
ids and error codes are (SPEC 17.2)."""

import json
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import AppError
from app.core.security import Cipher
from app.db.models.accounts import User
from app.features.auth.repository import UserRepository
from app.features.auth.service import sessions
from app.features.auth.service.allowlist import allowed, explicitly_allowed
from app.features.auth.service.claim import ClaimIdentity, claim_offered, close_claim, seal_identity
from app.features.auth.service.cookies import OAUTH_COOKIE_SECONDS
from app.providers.auth import pkce
from app.providers.auth.base import OidcError, OidcIdentity, OidcProvider

logger = logging.getLogger(__name__)

# Maximum lengths of the return parameters: checked here, not by the route (a JSON 422 has no
# place on the return from Google, which always ends with a redirect).
MAX_CODE = 2048
MAX_STATE = 2048
MAX_ERROR = 256
MAX_EMAIL = 320
MAX_NAME = 200
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@dataclass(frozen=True)
class CallbackOutcome:
    kind: Literal["signed_in", "claim", "error"]
    token: str | None = None
    claim_cookie: str | None = None
    error: str | None = None


def _failed(code: str) -> CallbackOutcome:
    logger.info("Google sign-in refused: %s", code)
    return CallbackOutcome(kind="error", error=code)


def _valid_hint(login_hint: str | None) -> str | None:
    """A plausible e-mail address of at most 320 characters, otherwise it is ignored."""
    if login_hint and len(login_hint) <= MAX_EMAIL and _EMAIL.fullmatch(login_hint):
        return login_hint
    return None


def start_login(oidc: OidcProvider, cipher: Cipher, login_hint: str | None) -> tuple[str, str]:
    """(Google address to send the browser to, value of the `tremplin_oauth` cookie)."""
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = pkce.new_verifier()
    url = oidc.authorization_url(
        state=state,
        code_challenge=pkce.challenge(verifier),
        nonce=nonce,
        login_hint=_valid_hint(login_hint),
    )
    pending = json.dumps({"state": state, "verifier": verifier, "nonce": nonce})
    return url, cipher.encrypt(pending)


def _read_pending(cipher: Cipher, raw: str | None) -> dict[str, str] | None:
    """The content of the `tremplin_oauth` cookie, `None` if it is missing, tampered with or
    older than 10 minutes."""
    if not raw:
        return None
    try:
        pending = json.loads(cipher.decrypt(raw, ttl=OAUTH_COOKIE_SECONDS))
    except (AppError, ValueError):  # unreadable or expired (`SecretUnreadable`), or not JSON
        return None
    if not isinstance(pending, dict) or not all(
        isinstance(pending.get(key), str) for key in ("state", "verifier", "nonce")
    ):
        return None
    return {key: pending[key] for key in ("state", "verifier", "nonce")}


def _too_long(code: str | None, state: str | None, error: str | None) -> bool:
    return (
        len(code or "") > MAX_CODE or len(state or "") > MAX_STATE or len(error or "") > MAX_ERROR
    )


async def finish_login(
    db: AsyncSession,
    oidc: OidcProvider,
    cipher: Cipher,
    settings: Settings,
    *,
    code: str | None,
    state: str | None,
    error: str | None,
    oauth_cookie: str | None,
    now: datetime,
) -> CallbackOutcome:
    """The return from Google. Nothing is written until the `state`, the identity token, the
    verified address and `ALLOWED_EMAILS` have all passed. An unexpected exception (race on a
    uniqueness constraint, future oversight) never becomes a 500: it is logged by its class,
    the transaction is rolled back and the person returns to `/login`."""
    if _too_long(code, state, error):
        return _failed("state_invalid")
    if error:
        return _failed("access_denied")
    pending = _read_pending(cipher, oauth_cookie)
    if pending is None or not state:
        return _failed("state_invalid")
    if not secrets.compare_digest(state.encode(), pending["state"].encode()):
        return _failed("state_invalid")
    if not code:
        return _failed("token_invalid")
    try:
        return await _sign_in(db, oidc, cipher, settings, code=code, pending=pending, now=now)
    except Exception as exc:
        await db.rollback()
        logger.warning("Google sign-in: unexpected error (%s)", type(exc).__name__)
        return _failed("token_invalid")


async def _sign_in(
    db: AsyncSession,
    oidc: OidcProvider,
    cipher: Cipher,
    settings: Settings,
    *,
    code: str,
    pending: dict[str, str],
    now: datetime,
) -> CallbackOutcome:
    """The code exchange, the identity checks, then the user and their session."""
    try:
        identity = await oidc.exchange(
            code=code, code_verifier=pending["verifier"], nonce=pending["nonce"]
        )
    except OidcError as exc:
        return _failed(exc.code)
    if not identity.email_verified:
        return _failed("email_unverified")
    if len(identity.email.strip()) > MAX_EMAIL:  # never silently truncated
        return _failed("token_invalid")
    if not allowed(identity.email, settings.allowed_emails):
        return _failed("email_not_allowed")
    users = UserRepository(db)
    if (
        await users.get_by_google_sub(identity.sub) is None
        and explicitly_allowed(identity.email, settings.allowed_emails)
        and await claim_offered(db)
    ):
        # Very first Google account, named in the list, local space present: nothing is created
        # avant son choix (P9).
        logger.info("takeover of the local space offered")
        clean = ClaimIdentity(
            identity.sub, identity.email.strip().lower(), identity.name[:MAX_NAME]
        )
        return CallbackOutcome(kind="claim", claim_cookie=seal_identity(cipher, clean))
    user = await _find_or_create(db, users, identity)
    if user is None:
        return _failed("token_invalid")
    token = await sessions.open_session(db, user.id, now=now, days=settings.session_days)
    logger.info("Google sign-in succeeded for user %s", user.id)
    return CallbackOutcome(kind="signed_in", token=token)


async def _find_or_create(
    db: AsyncSession, users: UserRepository, identity: OidcIdentity
) -> User | None:
    """The user of this Google identity (found by `sub`: e-mail and name are refreshed), otherwise
    a new one. `None`, nothing written, if the address already belongs to another account (never
    two accounts merged, nor a database error, nor a checked address that is not the one kept)."""
    email = identity.email.strip().lower()
    name = identity.name[:MAX_NAME]
    holder = await users.get_by_email(email)
    user = await users.get_by_google_sub(identity.sub)
    if holder is not None and (user is None or holder.id != user.id):
        return None
    if user is None:
        if not await users.any_google_user():
            await close_claim(db, users)  # the first Google account closes the takeover
        return await users.add_google(sub=identity.sub, email=email, name=name)
    await users.update_identity(user, email=email, name=name)
    return user
