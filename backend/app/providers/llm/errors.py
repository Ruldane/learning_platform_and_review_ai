"""Erreurs d'appel LLM : lesquelles valent la peine d'être retentées, et leur message lisible.

Un seul endroit traduit les erreurs des fournisseurs (SDK Anthropic et OpenAI, httpx) en messages
français : jamais le message brut du SDK ni le corps de réponse (une clé masquée y figure parfois).
"""

from collections.abc import Mapping

import anthropic
import httpx
import openai

from app.core.errors import AppError

_TRANSIENT_STATUSES = frozenset({408, 409, 429})

# Messages par code d'erreur du corps de réponse (`{"error": {"code": ...}}`), par fournisseur.
PROVIDER_ERROR_CODES: Mapping[str, Mapping[str, str]] = {
    "glm": {  # Z.ai, codes renvoyés avec un statut 429
        "1113": "Crédit Z.ai insuffisant pour ce modèle.",
        "1305": "Service Z.ai surchargé, réessaie plus tard.",
    },
    "openai": {
        "insufficient_quota": "Crédit OpenAI épuisé : recharge le compte ou change de modèle.",
    },
}
# Crédit épuisé : un nouvel essai échouerait de même, inutile d'attendre.
_CREDIT_CODES = frozenset({"1113", "insufficient_quota"})
# Surcharge du service renvoyée en 429 (Z.ai 1305) : retentée comme tout 429, mais rendue en
# `llm_unavailable` (panne passagère), pas en `llm_rate_limited` (limite ou quota).
_OVERLOAD_CODES = frozenset({"1305"})

_TIMEOUTS = (
    anthropic.APITimeoutError,
    openai.APITimeoutError,
    httpx.TimeoutException,
    TimeoutError,
)
_CONNECTION = (
    anthropic.APIConnectionError,
    openai.APIConnectionError,
    httpx.TransportError,
    ConnectionError,
)


def _transient_status(status: int) -> bool:
    return status in _TRANSIENT_STATUSES or status >= 500


def _status(exc: BaseException) -> int | None:
    if isinstance(exc, anthropic.APIStatusError | openai.APIStatusError):
        return exc.status_code
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return None


def _as_code(code: object) -> str | None:
    """Un code d'erreur est une chaîne, quel que soit le type donné par le SDK ou le serveur."""
    if isinstance(code, bool) or not isinstance(code, str | int):
        return None
    return str(code)


def _body_code(exc: BaseException) -> str | None:
    """Code d'erreur du corps de réponse (`error.code`) en chaîne, jamais son message.

    Ne lève jamais : un corps non lu (réponse en flux), illisible ou d'une autre forme donne `None`.
    """
    if isinstance(exc, openai.APIStatusError):
        return _as_code(exc.code)  # le SDK l'extrait de `{"error": {...}}`
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            return _as_code(exc.response.json()["error"]["code"])
        except (ValueError, KeyError, TypeError, httpx.ResponseNotRead):
            return None
    return None


def is_transient(exc: BaseException) -> bool:
    """Délai réseau, connexion coupée, 429 (limite), 408/409 ou 5xx : le même appel peut réussir
    plus tard. Une clé refusée, un crédit épuisé, une requête invalide ou une erreur de
    programmation ne le peuvent pas, on ne les retente pas."""
    if isinstance(exc, anthropic.APIConnectionError | openai.APIConnectionError):
        return True  # inclut les délais dépassés (APITimeoutError en est une sous-classe)
    status = _status(exc)
    if status is not None:
        return _transient_status(status) and _body_code(exc) not in _CREDIT_CODES
    return isinstance(
        exc, httpx.TimeoutException | httpx.TransportError | ConnectionError | TimeoutError
    )


def _by_status(status: int, label: str, known: str | None, code: str | None) -> AppError:
    details = {"provider": label, "status": status}
    if status in (401, 403):
        message = f"Clé refusée par {label} : vérifie-la dans les réglages des modèles."
        return AppError("llm_key_rejected", message, 502, details)
    if status == 429:
        if code in _OVERLOAD_CODES:  # surcharge passagère, pas une limite : D115 n° 17
            message = known or f"{label} est surchargé, réessaie plus tard."
            return AppError("llm_unavailable", message, 502, details)
        if code in _CREDIT_CODES:
            message = known or f"Crédit épuisé chez {label}."
            return AppError("llm_credit_exhausted", message, 502, details)
        message = known or f"Limite de requêtes ou crédit épuisé chez {label}, réessaie plus tard."
        return AppError("llm_rate_limited", message, 502, details)
    if status >= 500:
        message = (
            known or f"{label} est indisponible pour le moment ({status}), réessaie plus tard."
        )
        return AppError("llm_unavailable", message, 502, details)
    message = known or f"{label} a refusé la requête ({status})."
    return AppError("llm_request_rejected", message, 502, details)


def describe_provider_error(
    exc: BaseException, *, provider: str | None, label: str
) -> AppError | None:
    """Erreur lisible pour une panne du fournisseur `provider` (nom, ex. « glm ») affiché `label` ;
    `None` si `exc` n'est pas une erreur de fournisseur (elle suit alors son chemin habituel).

    Le message ne reprend ni le texte de l'exception ni le corps de réponse : seuls le statut HTTP
    et le code d'erreur servent à choisir un message connu.
    """
    if isinstance(exc, _TIMEOUTS):  # avant la connexion : les délais du SDK en sont un cas
        message = f"{label} n'a pas répondu à temps, réessaie plus tard."
        return AppError("llm_timeout", message, 504, {"provider": label})
    if isinstance(exc, _CONNECTION):
        message = f"Impossible de joindre {label}. Vérifie ta connexion."
        return AppError("llm_unavailable", message, 502, {"provider": label})
    status = _status(exc)
    if status is None:
        return None
    code = _body_code(exc)
    known = PROVIDER_ERROR_CODES.get(provider or "", {}).get(code or "")
    return _by_status(status, label, known, code)
