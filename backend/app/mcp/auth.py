"""La porte d'authentification du MCP (phase 10, P16) : seul un jeton `tmcp_…` ouvre `/mcp`.

- Le jeton se lit **uniquement** dans `Authorization: Bearer` : jamais le cookie de session, jamais
  la chaîne de requête. À l'inverse, ce jeton n'ouvre jamais `/api/v1` (l'authentificateur de
  l'application ne lit que le cookie).
- Seul le SHA-256 du jeton est en base ; le clair n'existe qu'à la création (affiché une fois).
  Jamais journalisé, jamais mis dans un message d'erreur.
- `Origin` et `Host` doivent être locaux (`localhost`, `127.0.0.1`) : défense contre le « DNS
  rebinding » demandée par la spécification du transport.
- Interrupteur général coupé (par défaut), jeton inconnu, expiré, révoqué ou compte qui n'a plus le
  droit d'entrer : refus, rien d'exécuté."""

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import McpIdentity
from app.core.errors import AppError
from app.core.security import KnownSecrets
from app.db.models.mcp import McpPrefs, McpToken
from app.mcp.base import NEVER_EXPOSED_FEATURES
from app.mcp.tools import McpGate

TOKEN_PREFIX = "tmcp_"
_TOKEN = re.compile(r"tmcp_[A-Za-z0-9_-]{43}")  # `token_urlsafe(32)` : 43 caractères
_BEARER = re.compile(r"Bearer ([^\s]+)", re.IGNORECASE)
_LOCAL_HOST = re.compile(r"(localhost|127\.0\.0\.1)(:[0-9]{1,5})?", re.IGNORECASE)
_LOCAL_ORIGIN = re.compile(r"https?://(localhost|127\.0\.0\.1)(:[0-9]{1,5})?", re.IGNORECASE)


_LAST_USED_EVERY = timedelta(minutes=1)  # `last_used_at` : une écriture par minute au plus


class McpRefusal(AppError):
    """Un refus de la porte. `user_id` et `token_id` : à qui est le jeton, quand on le sait
    (`None` : jeton inconnu ou refus avant de le chercher) ; pour le journal des refus."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        *,
        user_id: str | None = None,
        token_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code, message, status_code, details)
        self.user_id = user_id
        self.token_id = token_id


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    """`(clair, empreinte)` d'un jeton neuf : `tmcp_` + 32 octets aléatoires. Le clair est masqué
    dans les journaux dès sa création."""
    plain = TOKEN_PREFIX + secrets.token_urlsafe(32)
    KnownSecrets.add(plain)
    return plain, hash_token(plain)


def check_local_origin(request: Request) -> None:
    """403 si `Host` n'est pas local, ou si un `Origin` est présent et n'est pas local."""
    hosts = request.headers.getlist("host")
    if len(hosts) != 1 or not _LOCAL_HOST.fullmatch(hosts[0]):
        raise McpRefusal(
            "host_not_allowed", "Le serveur MCP n'est joignable que depuis ce poste.", 403
        )
    origins = request.headers.getlist("origin")
    if len(origins) > 1 or (origins and not _LOCAL_ORIGIN.fullmatch(origins[0])):
        raise McpRefusal("origin_not_allowed", "Origine refusée : le MCP est local seulement.", 403)


async def guard_interface_request(request: Request) -> None:
    """Garde des routes de gestion du MCP (`/api/v1/mcp/*`, geste de l'interface). Un jeton MCP
    présenté ici est refusé (403) au lieu d'être ignoré : un client qui rejoue son jeton au mauvais
    endroit n'obtient rien. En mode local (l'API n'a aucune authentification), l'hôte et l'origine
    doivent aussi être locaux : un autre site ne peut pas atteindre ces routes (DNS rebinding)."""
    for value in request.headers.getlist("authorization"):
        match = _BEARER.fullmatch(value)
        if match is not None and match.group(1).startswith(TOKEN_PREFIX):
            raise AppError(
                "mcp_token_on_api",
                "Un jeton MCP n'ouvre que le serveur MCP : ces réglages sont ceux de l'interface.",
                403,
            )
    if request.app.state.settings.auth_mode == "local":
        check_local_origin(request)


def _bearer(request: Request) -> str:
    """Le jeton présenté, ou 401. Un seul en-tête `Authorization` est accepté."""
    headers = request.headers.getlist("authorization")
    match = _BEARER.fullmatch(headers[0]) if len(headers) == 1 else None
    if match is None or not _TOKEN.fullmatch(match.group(1)):
        raise McpRefusal(
            "mcp_token_invalid",
            "Jeton MCP manquant ou invalide : envoie « Authorization: Bearer tmcp_… ».",
            401,
        )
    return match.group(1)


async def _find(db: AsyncSession, plain: str) -> McpToken:
    # Seule recherche sans `user_id` : on ne sait pas encore à qui est le jeton (comme la session
    # de connexion, retrouvée par son empreinte).
    digest = hash_token(plain)
    row = (await db.execute(select(McpToken).where(McpToken.hash == digest))).scalar_one_or_none()
    if row is None:
        raise McpRefusal("mcp_token_invalid", "Jeton MCP inconnu.", 401)
    return row


def _refuse(
    token: McpToken,
    code: str,
    message: str,
    status: int,
    details: dict[str, Any] | None = None,
) -> McpRefusal:
    return McpRefusal(
        code, message, status, user_id=token.user_id, token_id=token.id, details=details
    )


def _check_validity(token: McpToken, now: datetime) -> None:
    if token.revoked_at is not None:
        raise _refuse(token, "mcp_token_revoked", "Ce jeton MCP a été révoqué.", 401)
    if token.expires_at <= now:
        raise _refuse(
            token, "mcp_token_expired", "Ce jeton MCP a expiré : crées-en un nouveau.", 401
        )


async def _is_enabled(db: AsyncSession, user_id: str) -> bool:
    stmt = select(McpPrefs.enabled).where(McpPrefs.user_id == user_id)
    return bool((await db.execute(stmt)).scalar_one_or_none())


async def authenticate(request: Request, db: AsyncSession) -> McpIdentity:
    """L'identité du jeton présenté, ou `AppError` : 403 (origine, interrupteur coupé), 401
    (jeton absent, inconnu, expiré, révoqué, compte retiré). Pose `last_used_at` (la session
    appelante doit valider)."""
    check_local_origin(request)
    gate: McpGate | None = getattr(request.app.state, "mcp_gate", None)
    if gate is None:
        raise AppError("mcp_unavailable", "Le serveur MCP n'est pas prêt.", 503)
    plain = _bearer(request)
    token = await _find(db, plain)
    KnownSecrets.add(
        plain
    )  # un jeton valide est masqué dans les journaux, même après un redémarrage
    now = datetime.now(UTC)
    _check_validity(token, now)
    try:  # plafond grossier avant toute écriture : une boucle de requêtes n'écrit rien
        await gate.limiter.check_request(token.id, now)
    except AppError as exc:
        raise _refuse(token, exc.code, exc.message, exc.status_code, exc.details) from exc
    if not await gate.user_allowed(db, token.user_id):
        raise _refuse(token, "mcp_token_invalid", "Ce compte n'a plus accès à l'application.", 401)
    if not await _is_enabled(db, token.user_id):
        raise _refuse(
            token,
            "mcp_disabled",
            "L'accès MCP est coupé : rallume-le dans les réglages de Tremplin.",
            403,
        )
    if token.last_used_at is None or now - token.last_used_at >= _LAST_USED_EVERY:
        await db.execute(update(McpToken).where(McpToken.id == token.id).values(last_used_at=now))
    features = frozenset(str(name) for name in token.features) - NEVER_EXPOSED_FEATURES
    mode: Literal["read", "write"] = "write" if token.mode == "write" else "read"
    return McpIdentity(
        user_id=token.user_id,
        token_id=token.id,
        label=token.label,
        features=features,
        mode=mode,
    )
