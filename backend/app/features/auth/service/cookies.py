"""Les trois cookies de la connexion Google (P6) : noms, chemins, durées.

- `tremplin_session` : jeton opaque de la session, `Path=/`, 30 jours (`HttpOnly`, `SameSite=Lax`).
- `tremplin_oauth` : `{state, verifier, nonce}` chiffré, 10 minutes, limité à `/api/v1/auth/google`.
- `tremplin_claim` : `{sub, email, name}` chiffré (le choix de reprise), même durée et même chemin.

Jamais journalisés, ni leur valeur ni leur contenu.
"""

from fastapi import Response

SESSION_COOKIE = "tremplin_session"
OAUTH_COOKIE = "tremplin_oauth"
CLAIM_COOKIE = "tremplin_claim"
OAUTH_COOKIE_PATH = "/api/v1/auth/google"
OAUTH_COOKIE_SECONDS = 600


def clear_session_cookie(response: Response, *, secure: bool = False) -> None:
    """Efface le cookie de session : même `Path=/` (et mêmes attributs) que la pose, sans quoi le
    navigateur garderait l'ancien."""
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=secure)


def set_session_cookie(response: Response, token: str, *, days: int, secure: bool) -> None:
    """Pose le cookie de session : `Path=/`, `HttpOnly`, `SameSite=Lax`, durée fixe en jours,
    `Secure` quand l'adresse de retour est en `https`."""
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
    """Efface `tremplin_oauth` (même chemin que la pose) : il ne sert qu'une fois."""
    response.delete_cookie(
        OAUTH_COOKIE, path=OAUTH_COOKIE_PATH, httponly=True, samesite="lax", secure=secure
    )


def clear_claim_cookie(response: Response, *, secure: bool) -> None:
    """Efface `tremplin_claim` (même chemin que la pose) : le choix ne se fait qu'une fois."""
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
