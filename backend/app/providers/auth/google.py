"""Connexion Google par OpenID Connect, code d'autorisation avec PKCE, écrite à la main avec httpx.

Le jeton d'identité vient directement du point `token` par TLS : OIDC Core 3.1.3.7 n° 6 permet de
se passer de la vérification de signature. On contrôle `iss`, `aud`, `exp` et `nonce`, et on rend
`email_verified` tel quel. Les adresses et l'émetteur viennent de la configuration, pour que le
faux fournisseur (`scripts/fake_oidc.py`) serve par le même code.

Rien de ce qui passe ici (code, vérificateur, jeton, revendications) n'est journalisé ni cité
dans une erreur : seul le code de `OidcError` sort."""

import base64
import hmac
import json
import logging
import time
from urllib.parse import quote, urlencode

import httpx

from app.providers.auth.base import OidcError, OidcIdentity

logger = logging.getLogger(__name__)

TOKEN_TIMEOUT_S = 10.0
SCOPE = "openid email profile"


def _claims(id_token: object) -> dict[str, object]:
    """La charge d'un JWT (sa deuxième partie), sans vérifier la signature (voir l'en-tête)."""
    parts = id_token.split(".") if isinstance(id_token, str) else []
    if len(parts) != 3:
        raise OidcError("token_invalid")
    try:
        raw = base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
        claims = json.loads(raw)
    except ValueError as exc:  # base64, UTF-8 ou JSON invalide
        raise OidcError("token_invalid") from exc
    if not isinstance(claims, dict):
        raise OidcError("token_invalid")
    return claims


def _same(left: object, right: str) -> bool:
    return isinstance(left, str) and hmac.compare_digest(left.encode(), right.encode())


def _audience_ok(aud: object, client_id: str) -> bool:
    """Notre `client_id` seul : une liste n'est acceptée que d'un seul élément."""
    if isinstance(aud, list):
        return len(aud) == 1 and _same(aud[0], client_id)
    return _same(aud, client_id)


def _verified(value: object) -> bool:
    """Google rend un booléen ; `tokeninfo` et d'anciens jetons, la chaîne « true »."""
    return value is True or value == "true"


def _filled(value: object) -> bool:
    return isinstance(value, str) and bool(value)


class GoogleOidc:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        auth_url: str,
        token_url: str,
        issuer: str,
        redirect_uri: str,
        http: httpx.AsyncClient,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._auth_url = auth_url
        self._token_url = token_url
        self._issuers = {issuer, issuer.removeprefix("https://")}
        self._redirect_uri = redirect_uri
        self._http = http

    def authorization_url(
        self, *, state: str, code_challenge: str, nonce: str, login_hint: str | None
    ) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        if login_hint:
            params["login_hint"] = login_hint
        return f"{self._auth_url}?{urlencode(params, quote_via=quote)}"

    async def exchange(self, *, code: str, code_verifier: str, nonce: str) -> OidcIdentity:
        body = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._redirect_uri,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code_verifier": code_verifier,
        }
        try:
            response = await self._http.post(self._token_url, data=body, timeout=TOKEN_TIMEOUT_S)
        except httpx.HTTPError as exc:
            logger.warning("OIDC : point token injoignable (%s)", type(exc).__name__)
            raise OidcError("google_unavailable") from exc
        if response.status_code >= 500:
            logger.warning("OIDC : point token en erreur (HTTP %d)", response.status_code)
            raise OidcError("google_unavailable")
        if response.status_code >= 400:
            logger.warning("OIDC : code refusé (HTTP %d)", response.status_code)
            raise OidcError("token_invalid")
        return self._identity(response, nonce)

    def _identity(self, response: httpx.Response, nonce: str) -> OidcIdentity:
        try:
            payload = response.json()
        except ValueError as exc:
            raise OidcError("token_invalid") from exc
        claims = _claims(payload.get("id_token") if isinstance(payload, dict) else None)
        exp = claims.get("exp")
        valid = (
            claims.get("iss") in self._issuers
            and _audience_ok(claims.get("aud"), self._client_id)
            and isinstance(exp, int | float)
            and not isinstance(exp, bool)
            and exp > time.time()
            and _same(claims.get("nonce"), nonce)
            and _filled(claims.get("email"))
            and _filled(claims.get("sub"))
        )
        if not valid:
            logger.warning("OIDC : jeton d'identité refusé")
            raise OidcError("token_invalid")
        name = claims.get("name")
        return OidcIdentity(
            sub=str(claims["sub"]),
            email=str(claims["email"]),
            email_verified=_verified(claims.get("email_verified")),
            name=name if isinstance(name, str) and name else str(claims["email"]),
        )
