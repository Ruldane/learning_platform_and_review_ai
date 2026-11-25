"""The three Google sign-in cookies (P6): names, paths, durations.

- `tremplin_session`: opaque session token, `Path=/`, 30 days (`HttpOnly`, `SameSite=Lax`).
- `tremplin_oauth`: `{state, verifier, nonce}` encrypted, 10 minutes, limited to
  `/api/v1/auth/google`.
- `tremplin_claim`: `{sub, email, name}` encrypted (the takeover choice), same duration and path.

Never logged, neither their value nor their content.
"""

from fastapi import Response

SESSION_COOKIE = "tremplin_session"
OAUTH_COOKIE = "tremplin_oauth"
CLAIM_COOKIE = "tremplin_claim"
OAUTH_COOKIE_PATH = "/api/v1/auth/google"
OAUTH_COOKIE_SECONDS = 600


def clear_session_cookie(response: Response, *, secure: bool = False) -> None:
    """Clears the session cookie: same `Path=/` (and same attributes) as when it was set,
    otherwise the browser would keep the old one."""
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=secure)


def set_session_cookie(response: Response, token: str, *, days: int, secure: bool) -> None:
    """Sets the session cookie: `Path=/`, `HttpOnly`, `SameSite=Lax`, fixed duration in days,
    `Secure` when the return address is `https`."""
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=days * 86400,
        path="/",
        httponly=True,
        samesite="lax",
        secure=secure,
    )


def set_oauth_cookie(response: Response, value: str, *, secure: bool) -> None:
    _set_short_cookie(response, OAUTH_COOKIE, value, secure)


def set_claim_cookie(response: Response, value: str, *, secure: bool) -> None:
    _set_short_cookie(response, CLAIM_COOKIE, value, secure)


def clear_oauth_cookie(response: Response, *, secure: bool) -> None:
    """Clears `tremplin_oauth` (same path as when set): it is used only once."""
    response.delete_cookie(
        OAUTH_COOKIE, path=OAUTH_COOKIE_PATH, httponly=True, samesite="lax", secure=secure
    )


def clear_claim_cookie(response: Response, *, secure: bool) -> None:
    """Clears `tremplin_claim` (same path as when set): the choice is made only once."""
    response.delete_cookie(
        CLAIM_COOKIE, path=OAUTH_COOKIE_PATH, httponly=True, samesite="lax", secure=secure
    )


def _set_short_cookie(response: Response, name: str, value: str, secure: bool) -> None:
    response.set_cookie(
        name,
        value,
        max_age=OAUTH_COOKIE_SECONDS,
        path=OAUTH_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=secure,
    )
