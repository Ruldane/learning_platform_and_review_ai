"""Faux fournisseur OpenID Connect pour les essais et les parcours de bout en bout (phase 9, P5).

Il parle comme Google sur les deux points que le back utilise (`/authorize` et `/token`), sans
réseau : l'e-mail vient de `login_hint` (sinon d'une valeur par défaut), il n'y a ni mot de passe
ni écran. Le jeton d'identité n'est pas signé (`alg: none`) : le back ne vérifie pas la signature
d'un jeton reçu du point `token` (OIDC Core 3.1.3.7 n° 6). Outil de test : jamais en production.

Usage, depuis backend/ :
    python -m scripts.fake_oidc --port 8099 --issuer http://127.0.0.1:8099 --client-id fake-client
"""

import argparse
import base64
import hashlib
import json
import secrets
import time
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlencode

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

DEFAULT_EMAIL = "camille.exemple@example.org"
ID_TOKEN_SECONDS = 3600


@dataclass(frozen=True)
class _Grant:
    email: str
    challenge: str
    nonce: str
    redirect_uri: str


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _s256(verifier: str) -> str:
    return _b64(hashlib.sha256(verifier.encode("ascii", "replace")).digest())


def _display_name(email: str) -> str:
    return " ".join(part.capitalize() for part in email.split("@")[0].split("."))


def _id_token(*, issuer: str, client_id: str, grant: _Grant) -> str:
    email = grant.email
    claims = {
        "iss": issuer,
        "aud": client_id,
        "exp": int(time.time()) + ID_TOKEN_SECONDS,
        "nonce": grant.nonce,
        "sub": "fake-" + hashlib.sha256(email.encode()).hexdigest()[:16],
        "email": email,
        "email_verified": not email.startswith("unverified"),
        "name": _display_name(email),
    }
    header = _b64(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    return f"{header}.{_b64(json.dumps(claims).encode())}."


def _bad(error: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": error}, status_code=status)


def create_fake_oidc_app(
    *, issuer: str, client_id: str, default_email: str = DEFAULT_EMAIL
) -> FastAPI:
    app = FastAPI(title="Faux fournisseur OIDC", docs_url=None, redoc_url=None, openapi_url=None)
    grants: dict[str, _Grant] = {}

    @app.get("/authorize")
    async def authorize(request: Request) -> Response:
        query = request.query_params
        redirect_uri, state = query.get("redirect_uri", ""), query.get("state", "")
        if query.get("client_id") != client_id or not redirect_uri:
            return _bad("invalid_request")
        if query.get("code_challenge_method") != "S256" or not query.get("code_challenge"):
            return _bad("invalid_request")
        if query.get("deny") == "1":
            return RedirectResponse(
                f"{redirect_uri}?{urlencode({'error': 'access_denied', 'state': state})}", 302
            )
        code = secrets.token_urlsafe(24)
        grants[code] = _Grant(
            email=query.get("login_hint") or default_email,
            challenge=query["code_challenge"],
            nonce=query.get("nonce", ""),
            redirect_uri=redirect_uri,
        )
        return RedirectResponse(f"{redirect_uri}?{urlencode({'code': code, 'state': state})}", 302)

    @app.post("/token")
    async def token(request: Request) -> Response:
        form = await request.form()
        grant = grants.pop(str(form.get("code", "")), None)  # à usage unique, même refusé
        if grant is None or form.get("client_id") != client_id:
            return _bad("invalid_grant")
        if form.get("redirect_uri") != grant.redirect_uri:
            return _bad("invalid_grant")
        if _s256(str(form.get("code_verifier", ""))) != grant.challenge:
            return _bad("invalid_grant")
        body = {
            "access_token": secrets.token_urlsafe(16),
            "token_type": "Bearer",
            "expires_in": ID_TOKEN_SECONDS,
            "id_token": _id_token(issuer=issuer, client_id=client_id, grant=grant),
        }
        return JSONResponse(body)

    return app


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Faux fournisseur OpenID Connect (essais).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--issuer", default="http://127.0.0.1:8099")
    parser.add_argument("--client-id", default="fake-client")
    args = parser.parse_args(argv)
    app = create_fake_oidc_app(issuer=args.issuer, client_id=args.client_id)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
