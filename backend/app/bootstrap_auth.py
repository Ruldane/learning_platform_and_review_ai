"""Composition de la connexion Google : le client HTTP du point `token` et `GoogleOidc` (mode
Google seulement). Le lifespan l'appelle au démarrage, `app.bootstrap` en reçoit le résultat."""

from contextlib import AsyncExitStack

import httpx

from app.config import Settings
from app.providers.auth.base import OidcProvider
from app.providers.auth.google import GoogleOidc
from app.providers.web.fetch import refuse_all_cookies

_TOKEN_TIMEOUT_SECONDS = 10.0


def oidc_http() -> httpx.AsyncClient:
    """Client du point `token` : ni redirection, ni proxy ni réglage de l'environnement, aucun
    cookie retenu ; ouvert et fermé par le lifespan."""
    return httpx.AsyncClient(
        follow_redirects=False,
        trust_env=False,
        timeout=httpx.Timeout(_TOKEN_TIMEOUT_SECONDS),
        cookies=refuse_all_cookies(),
    )


async def open_oidc(settings: Settings, stack: AsyncExitStack) -> OidcProvider | None:
    """La connexion Google, avec son client HTTP fermé par `stack` ; en mode local rien n'est
    ouvert (aucun client inutile) et le résultat est `None`."""
    if settings.auth_mode != "google":
        return None
    return build_oidc(settings, await stack.enter_async_context(oidc_http()))


def build_oidc(settings: Settings, http: httpx.AsyncClient) -> OidcProvider | None:
    """`GoogleOidc` en mode Google (identifiants contrôlés au démarrage par `check_google_config`),
    `None` en mode local. Les adresses et l'émetteur viennent de la configuration (P5)."""
    if settings.auth_mode != "google":
        return None
    return GoogleOidc(
        client_id=settings.google_client_id or "",
        client_secret=settings.google_client_secret or "",
        auth_url=settings.google_auth_url,
        token_url=settings.google_token_url,
        issuer=settings.google_issuer,
        redirect_uri=settings.google_redirect_uri,
        http=http,
    )
