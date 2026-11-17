"""Outils des tests de la connexion Google : un faux point `token` de Google (`MockTransport`),
le départ et le retour de la connexion. Aucun réseau."""

import base64
import json
import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import FastAPI

from app.bootstrap_auth import build_oidc
from app.config import Settings

API = "/api/v1/auth"
LOGIN = f"{API}/google/login"
CALLBACK = f"{API}/google/callback"
CAMILLE = "camille.exemple@example.org"
DOMINIQUE = "dominique.exemple@example.org"
FRONT = "http://localhost:5173"


def jwt(claims: dict[str, object]) -> str:
    def part(data: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    return f"{part({'alg': 'none'})}.{part(claims)}."


class FakeGoogle:
    """Le point `token` de Google : rend un jeton d'identité pour l'identité réglée, avec le
    `nonce` de la dernière connexion commencée ; `claims` écrase des revendications."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.nonce = ""
        self.email = CAMILLE
        self.sub = "sub-camille"
        self.name = "Camille Exemple"
        self.verified = True
        self.claims: dict[str, object] = {}
        self.down = False
        self.forms: list[dict[str, str]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            return httpx.Response(503, text="en panne")
        self.forms.append({k: v[0] for k, v in parse_qs(request.content.decode()).items()})
        claims: dict[str, object] = {
            "iss": self._settings.google_issuer,
            "aud": self._settings.google_client_id,
            "exp": int(time.time()) + 3600,
            "nonce": self.nonce,
            "sub": self.sub,
            "email": self.email,
            "email_verified": self.verified,
            "name": self.name,
        }
        claims.update(self.claims)
        return httpx.Response(200, json={"id_token": jwt(claims)})

    def plug_into(self, app: FastAPI) -> httpx.AsyncClient:
        """Remplace la connexion de l'application par `GoogleOidc` sur ce faux point `token`."""
        http = httpx.AsyncClient(transport=httpx.MockTransport(self.handler))
        app.state.providers.oidc = build_oidc(app.state.settings, http)
        return http


def set_cookie(response: httpx.Response, name: str) -> str | None:
    """L'en-tête `Set-Cookie` du cookie `name`, tel que reçu (attributs compris)."""
    for header in response.headers.get_list("set-cookie"):
        if header.startswith(f"{name}="):
            return header
    return None


def failed(code: str) -> str:
    """Où le callback renvoie une connexion refusée."""
    return f"{FRONT}/connexion?erreur={code}"


def cookie_value(response: httpx.Response, name: str) -> str:
    return (set_cookie(response, name) or "").split(";")[0].split("=", 1)[1]


def location_query(response: httpx.Response) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(response.headers["location"]).query).items()}


async def start(client: httpx.AsyncClient, hint: str | None = None) -> httpx.Response:
    return await client.get(LOGIN, params={"login_hint": hint} if hint else None)


async def come_back(client: httpx.AsyncClient, **params: Any) -> httpx.Response:
    return await client.get(CALLBACK, params={k: v for k, v in params.items() if v is not None})


async def sign_in(
    client: httpx.AsyncClient,
    google: FakeGoogle,
    email: str = CAMILLE,
    *,
    sub: str | None = None,
    name: str | None = None,
) -> httpx.Response:
    """Un tour de connexion complet : départ, puis retour de Google avec le bon `state`."""
    google.email = email
    google.sub = sub or f"sub-{email.split('@')[0]}"
    google.name = name or google.name
    started = await start(client)
    query = location_query(started)
    google.nonce = query["nonce"]
    return await come_back(client, code="code-1", state=query["state"])
