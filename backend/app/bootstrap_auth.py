"""Composition of security and sign-in: secret and cipher, local-mode user, then the
HTTP client of the `token` endpoint and `GoogleOidc` (Google mode only). The lifespan calls
them at startup, `app.bootstrap` receives the result."""

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
    """`local` mode: creates the single user if missing and remembers its id."""
    try:
        async with app.state.session_factory() as session:
            user = await AuthService(session).ensure_local_user()
            await session.commit()
            app.state.local_user_id = user.id
    except OperationalError as exc:
        if "no such table" not in str(exc.orig):
            raise
        message = "Database not initialised: run `alembic upgrade head` before starting."
        logger.error(message)
        raise RuntimeError(message) from exc


def setup_security(app: FastAPI) -> None:
    """The application secret, the cipher, and the masking of keys in the logs."""
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
    """Client of the `token` endpoint: no redirect, no proxy or environment setting, no
    cookie kept; opened and closed by the lifespan."""
    return httpx.AsyncClient(
        follow_redirects=False,
        trust_env=False,
        timeout=httpx.Timeout(_TOKEN_TIMEOUT_SECONDS),
        cookies=refuse_all_cookies(),
    )


async def open_oidc(settings: Settings, stack: AsyncExitStack) -> OidcProvider | None:
    """Google sign-in, with its HTTP client closed by `stack`; in local mode nothing is
    opened (no useless client) and the result is `None`."""
    if settings.auth_mode != "google":
        return None
    return build_oidc(settings, await stack.enter_async_context(oidc_http()))


def build_oidc(settings: Settings, http: httpx.AsyncClient) -> OidcProvider | None:
    """`GoogleOidc` in Google mode (credentials checked at startup by `check_google_config`),
    `None` in local mode. The addresses and the issuer come from the configuration (P5)."""
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
