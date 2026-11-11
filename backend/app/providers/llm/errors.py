"""Classement des erreurs d'appel LLM : lesquelles valent la peine d'être retentées."""

import anthropic
import httpx
import openai

_TRANSIENT_STATUSES = frozenset({408, 409, 429})


def _transient_status(status: int) -> bool:
    return status in _TRANSIENT_STATUSES or status >= 500


def is_transient(exc: BaseException) -> bool:
    """Délai réseau, connexion coupée, 429 (limite), 408/409 ou 5xx : le même appel peut réussir
    plus tard. Une clé refusée, une requête invalide ou une erreur de programmation ne le peuvent
    pas, on ne les retente pas."""
    if isinstance(exc, anthropic.APIConnectionError | openai.APIConnectionError):
        return True  # inclut les délais dépassés (APITimeoutError en est une sous-classe)
    if isinstance(exc, anthropic.APIStatusError | openai.APIStatusError):
        return _transient_status(exc.status_code)
    if isinstance(exc, httpx.HTTPStatusError):
        return _transient_status(exc.response.status_code)
    return isinstance(
        exc, httpx.TimeoutException | httpx.TransportError | ConnectionError | TimeoutError
    )
