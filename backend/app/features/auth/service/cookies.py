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


def clear_session_cookie(response: Response) -> None:
    """Efface le cookie de session : même `Path=/` (et mêmes attributs) que la pose, sans quoi le
    navigateur garderait l'ancien."""
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")
