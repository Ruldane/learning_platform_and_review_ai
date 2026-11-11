"""Appels HTTP de vérification de clé et de liste de modèles, communs aux fournisseurs.

Volontairement en `httpx` simple (et non via les SDK des fournisseurs, qui s'appuient sur
`httpx2` et échappent à `respx`) : ces appels sont triviaux et restent testables sans réseau.
"""

from typing import Any

import httpx

from app.core.errors import AppError
from app.providers.llm.base import KeyTestResult

_TIMEOUT = httpx.Timeout(15.0)


async def check_key(
    label: str, method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None = None
) -> KeyTestResult:
    """Envoie la requête de vérification. Ne lève jamais, ne reprend jamais la clé du retour."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.request(method, url, headers=headers, json=body)
    except (httpx.HTTPError, httpx.InvalidURL):
        return KeyTestResult(
            ok=False, message=f"Impossible de joindre {label}. Vérifie ta connexion."
        )
    if response.status_code in (401, 403):
        return KeyTestResult(ok=False, message=f"Clé refusée par {label}.")
    if not response.is_success:
        return KeyTestResult(
            ok=False, message=f"{label} a répondu par une erreur ({response.status_code})."
        )
    return KeyTestResult(ok=True, message="Clé valide.")


async def get_json(label: str, url: str, headers: dict[str, str], params: dict[str, Any]) -> Any:
    """GET JSON ; toute erreur devient une `AppError` française (sans la clé)."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
        raise AppError(
            "llm_models_unavailable",
            f"Impossible de récupérer la liste des modèles {label}.",
            502,
            {"provider": label},
        ) from exc
