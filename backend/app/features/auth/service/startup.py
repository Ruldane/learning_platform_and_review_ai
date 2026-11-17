"""Refus de démarrer en mode Google quand la configuration ne permet pas de se connecter en
sécurité (P11, arbitrage `ALLOWED_EMAILS`) : message clair, comme la base non migrée. Aucune valeur
de configuration n'est citée."""

from urllib.parse import urlsplit

from app.config import Settings
from app.features.auth.service.allowlist import entries

_LOOPBACK = ("localhost", "127.0.0.1", "::1")


def check_google_config(settings: Settings) -> None:
    """Sans effet en mode local ; en mode Google, lève `RuntimeError` si les identifiants Google
    manquent, si `ALLOWED_EMAILS` est vide, ou si le point `token` n'est pas en `https`."""
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
            f"Mode Google : {' et '.join(missing)} manque(nt). Renseigne-les dans `.env` "
            "(console Google Cloud, identifiants OAuth) ou repasse en AUTH_MODE=local."
        )
    if not entries(settings.allowed_emails):
        raise RuntimeError(
            "Mode Google : ALLOWED_EMAILS est vide. Liste les adresses autorisées, séparées par "
            "des virgules, ou mets `*` pour accepter tous les comptes Google."
        )
    token_url = urlsplit(settings.google_token_url)
    if token_url.scheme != "https" and not (
        token_url.scheme == "http" and token_url.hostname in _LOOPBACK
    ):
        raise RuntimeError(
            "Mode Google : GOOGLE_TOKEN_URL doit être en https (seule la boucle locale, "
            "`localhost` ou `127.0.0.1`, peut rester en http, pour le faux fournisseur d'essai)."
        )
