"""Composition de la sécurité et de la connexion : secret et chiffreur, utilisateur du mode local,
puis le client HTTP du point `token` et `GoogleOidc` (mode Google seulement). Le lifespan les
appelle au démarrage, `app.bootstrap` en reçoit le résultat."""

import logging
from contextlib import AsyncExitStack

import httpx
from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.core.logging import configure_logging
from app.core.security import Cipher, KnownSecrets, load_or_create_secret
from app.features.auth.service import AuthService
from app.providers.auth.base import OidcProvider
from app.providers.auth.google import GoogleOidc
from app.providers.web.fetch import refuse_all_cookies

logger = logging.getLogger(__name__)
_TOKEN_TIMEOUT_SECONDS = 10.0
_LOG_LEVEL = "INFO"


async def ensure_local_user(app: FastAPI) -> None:
    """Mode `local` : crée l'utilisateur unique s'il manque et mémorise son id."""
    try:
        async with app.state.session_factory() as session:
            user = await AuthService(session).ensure_local_user()
            await session.commit()
            app.state.local_user_id = user.id
    except OperationalError as exc:
        if "no such table" not in str(exc.orig):
            raise
        message = (
            "Base de données non initialisée : lance `alembic upgrade head` avant de démarrer."
        )
        logger.error(message)
        raise RuntimeError(message) from exc


def setup_security(app: FastAPI) -> None:
    """Secret de l'application, chiffreur, et masquage des clés dans les journaux."""
    settings: Settings = app.state.settings
    app.state.cipher = Cipher(load_or_create_secret(settings.secret_path))
    for key in (
        settings.anthropic_api_key,
        settings.openai_api_key,
        settings.zai_api_key,
        settings.brave_api_key,
        settings.google_client_secret,
        (
            settings.calendar_google_client_secret.get_secret_value()
            if settings.calendar_google_client_secret
            else None
        ),
    ):
        if key:
            KnownSecrets.add(key)
    configure_logging(_LOG_LEVEL, KnownSecrets.values)


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
