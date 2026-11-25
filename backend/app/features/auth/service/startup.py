"""Refusing to start in Google mode when the configuration does not allow signing in safely
(P11, `ALLOWED_EMAILS` arbitration): a clear message, like the unmigrated database. No
configuration value is quoted."""

from urllib.parse import urlsplit

from app.config import Settings
from app.features.auth.service.allowlist import entries

_LOOPBACK = ("localhost", "127.0.0.1", "::1")


def check_google_config(settings: Settings) -> None:
    """No effect in local mode; in Google mode, raises `RuntimeError` if the Google credentials
    are missing, if `ALLOWED_EMAILS` is empty, or if the `token` endpoint is not `https`."""
    if settings.auth_mode != "google":
        return
    missing = [
        name
        for name, value in (
            ("GOOGLE_CLIENT_ID", settings.google_client_id),
            ("GOOGLE_CLIENT_SECRET", settings.google_client_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Google mode: {' and '.join(missing)} missing. Set them in `.env` "
            "(Google Cloud console, OAuth credentials) or switch back to AUTH_MODE=local."
        )
    if not entries(settings.allowed_emails):
        raise RuntimeError(
            "Google mode: ALLOWED_EMAILS is empty. List the allowed addresses, separated by "
            "commas, or put `*` to accept all Google accounts."
        )
    token_url = urlsplit(settings.google_token_url)
    if token_url.scheme != "https" and not (
        token_url.scheme == "http" and token_url.hostname in _LOOPBACK
    ):
        raise RuntimeError(
            "Google mode: GOOGLE_TOKEN_URL must be https (only the loopback, "
            "`localhost` or `127.0.0.1`, may stay http, for the test fake provider)."
        )
