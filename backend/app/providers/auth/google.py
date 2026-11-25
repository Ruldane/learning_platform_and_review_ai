"""Google sign-in through OpenID Connect, authorization code with PKCE, hand-written with httpx.

The identity token comes straight from the `token` endpoint over TLS: OIDC Core 3.1.3.7 no. 6
allows skipping the signature check. We check `iss`, `aud`, `exp` and `nonce`, and return
`email_verified` as is. The addresses and the issuer come from the configuration, so that the
fake provider (`scripts/fake_oidc.py`) is served by the same code.

Nothing that goes through here (code, verifier, token, claims) is logged or quoted
in an error: only the `OidcError` code comes out."""

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
# Timeout (408) and rate limiting (429): a temporary incident, not an invalid code.
TEMPORARY_REFUSALS = (408, 429)
SCOPE = "openid email profile"


def _claims(id_token: object) -> dict[str, object]:
    """The payload of a JWT (its second part), without checking the signature (see the header)."""
    parts = id_token.split(".") if isinstance(id_token, str) else []
    if len(parts) != 3:
        raise OidcError("token_invalid")
    try:
        raw = base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
        claims = json.loads(raw)
    except (ValueError, RecursionError) as exc:  # invalid base64, UTF-8 or JSON (or too nested)
        raise OidcError("token_invalid") from exc
    if not isinstance(claims, dict):
        raise OidcError("token_invalid")
    return claims


def _same(left: object, right: str) -> bool:
    # `surrogatepass`: a lone surrogate (accepted by `json.loads`) must not raise an error.
    return isinstance(left, str) and hmac.compare_digest(
        left.encode("utf-8", "surrogatepass"), right.encode("utf-8", "surrogatepass")
    )


def _audience_ok(aud: object, client_id: str) -> bool:
    """Our `client_id` alone: a list is only accepted with a single element."""
    if isinstance(aud, list):
        return len(aud) == 1 and _same(aud[0], client_id)
    return _same(aud, client_id)


def _verified(value: object) -> bool:
    """Google returns a boolean in the identity token: the string "true" is not accepted."""
    return value is True


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
            logger.warning("OIDC: token endpoint unreachable (%s)", type(exc).__name__)
            raise OidcError("google_unavailable") from exc
        if response.status_code >= 500 or response.status_code in TEMPORARY_REFUSALS:
            logger.warning("OIDC: token endpoint error (HTTP %d)", response.status_code)
            raise OidcError("google_unavailable")
        if response.status_code >= 400:
            logger.warning("OIDC: code refused (HTTP %d)", response.status_code)
            raise OidcError("token_invalid")
        return self._identity(response, nonce)

    def _identity(self, response: httpx.Response, nonce: str) -> OidcIdentity:
        try:
            payload = response.json()
        except (ValueError, RecursionError) as exc:  # unreadable or endlessly nested body
            raise OidcError("token_invalid") from exc
        claims = _claims(payload.get("id_token") if isinstance(payload, dict) else None)
        exp = claims.get("exp")
        iss = claims.get("iss")
        valid = (
            bool(nonce)
            and isinstance(iss, str)
            and iss in self._issuers
            and _audience_ok(claims.get("aud"), self._client_id)
            and isinstance(exp, int | float)
            and not isinstance(exp, bool)
            and exp > time.time()
            and _same(claims.get("nonce"), nonce)
            and _filled(claims.get("email"))
            and _filled(claims.get("sub"))
        )
        if not valid:
            logger.warning("OIDC: identity token refused")
            raise OidcError("token_invalid")
        name = claims.get("name")
        return OidcIdentity(
            sub=str(claims["sub"]),
            email=str(claims["email"]),
            email_verified=_verified(claims.get("email_verified")),
            name=name if isinstance(name, str) and name else str(claims["email"]),
        )
