"""Erreurs de la recherche web. Aucun message ne cite une requête ni une URL (SPEC 17.2)."""

from typing import Literal

from app.core.errors import AppError

QUOTA_CODE = "web_quota_reached"
# Requêtes Brave par mois civil UTC et par clé, tous utilisateurs confondus (SPEC 11.3).
BRAVE_MONTHLY_CAP = 900

_QUOTA_MESSAGES = {
    "queries": "Plafond de {cap} requêtes atteint pour cette session.",
    "pages": "Plafond de {cap} pages lues atteint pour cette session.",
}


class WebQuotaReached(AppError):
    """Plafond de la session atteint (SPEC 10.4) : `kind` dit lequel."""

    def __init__(self, cap: int, kind: Literal["queries", "pages"]) -> None:
        message = _QUOTA_MESSAGES[kind].format(cap=cap)
        super().__init__(QUOTA_CODE, message, 429, {"cap": cap, "kind": kind})
        self.cap = cap
        self.kind = kind


class NoSearchProvider(AppError):
    """Tous les fournisseurs de l'ordre de repli ont échoué, ou aucun n'a trouvé de résultat."""

    def __init__(self) -> None:
        super().__init__("search_unavailable", "Aucun moteur de recherche n'a répondu.", 503)


def empty_query() -> AppError:
    """Requête vide, ou vide une fois nettoyée de toute donnée personnelle : message fixe."""
    return AppError(
        "search_query_empty", "Requête vide une fois les données personnelles retirées.", 422
    )


def source_not_found() -> AppError:
    return AppError("source_not_found", "Source introuvable.", 404)
