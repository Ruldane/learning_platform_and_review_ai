"""Connexion Google, du départ au retour (P5, P6, P10) : le témoin `tremplin_oauth` garde `state`,
vérificateur PKCE et `nonce` (chiffrés, 10 minutes) ; au retour, rien n'est créé tant que tout
n'est pas contrôlé. Chaque échec devient un code (`/connexion?erreur=<code>`).

Ni code d'autorisation, ni `state`, ni vérificateur, ni jeton, ni e-mail, ni `sub`, ni `login_hint`
ne sont journalisés : seuls des identifiants et des codes d'erreur le sont (SPEC 17.2)."""

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
from app.features.auth.service.allowlist import allowed
from app.features.auth.service.cookies import OAUTH_COOKIE_SECONDS
from app.providers.auth import pkce
from app.providers.auth.base import OidcError, OidcIdentity, OidcProvider

logger = logging.getLogger(__name__)

# Longueurs maximales des paramètres du retour : contrôlées ici, pas par la route (une 422 JSON
# n'a pas sa place au retour de Google, qui finit toujours par une redirection).
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
    logger.info("connexion Google refusée : %s", code)
    return CallbackOutcome(kind="error", error=code)


def _valid_hint(login_hint: str | None) -> str | None:
    """Une adresse e-mail plausible de 320 caractères au plus, sinon on l'ignore."""
    if login_hint and len(login_hint) <= MAX_EMAIL and _EMAIL.fullmatch(login_hint):
        return login_hint
    return None


def start_login(oidc: OidcProvider, cipher: Cipher, login_hint: str | None) -> tuple[str, str]:
    """(adresse Google où envoyer le navigateur, valeur du témoin `tremplin_oauth`)."""
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
    """Le contenu du témoin `tremplin_oauth`, `None` s'il manque, est trafiqué ou a plus de
    10 minutes."""
    if not raw:
        return None
    try:
        pending = json.loads(cipher.decrypt(raw, ttl=OAUTH_COOKIE_SECONDS))
    except (AppError, ValueError):  # illisible ou périmé (`SecretUnreadable`), ou pas du JSON
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
    """Le retour de Google. Rien n'est écrit tant que le `state`, le jeton d'identité, l'adresse
    vérifiée et `ALLOWED_EMAILS` ne sont pas tous passés."""
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
        identity = await oidc.exchange(
            code=code, code_verifier=pending["verifier"], nonce=pending["nonce"]
        )
    except OidcError as exc:
        return _failed(exc.code)
    if not identity.email_verified:
        return _failed("email_unverified")
    if not allowed(identity.email, settings.allowed_emails):
        return _failed("email_not_allowed")
    user = await _find_or_create(UserRepository(db), identity)
    if user is None:
        return _failed("token_invalid")
    token = await sessions.open_session(db, user.id, now=now, days=settings.session_days)
    logger.info("connexion Google réussie pour l'utilisateur %s", user.id)
    return CallbackOutcome(kind="signed_in", token=token)


async def _find_or_create(users: UserRepository, identity: OidcIdentity) -> User | None:
    """L'utilisateur de cette identité Google (retrouvé par `sub` : e-mail et nom sont remis à
    jour), sinon un nouveau. `None` si l'adresse appartient déjà à un autre compte (jamais deux
    comptes fusionnés ni une erreur de base)."""
    email = identity.email.strip().lower()[:MAX_EMAIL]
    name = identity.name[:MAX_NAME]
    holder = await users.get_by_email(email)
    user = await users.get_by_google_sub(identity.sub)
    if user is None:
        return None if holder else await users.add_google(sub=identity.sub, email=email, name=name)
    if holder is None or holder.id == user.id:
        await users.update_identity(user, email=email, name=name)
    return user
