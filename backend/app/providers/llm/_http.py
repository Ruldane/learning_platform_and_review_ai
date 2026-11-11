"""Appels HTTP de vérification de clé et de liste de modèles, communs aux fournisseurs.

Volontairement en `httpx` simple (et non via les SDK des fournisseurs, qui s'appuient sur
`httpx2` et échappent à `respx`) : ces appels sont triviaux et restent testables sans réseau.
"""

from typing import Any

import httpx

from app.core.errors import AppError
from app.providers.llm.base import KeyTestResult

_TIMEOUT = httpx.Timeout(15.0)
_INVALID_KEY = "La clé contient des caractères invalides."


def _headers_are_valid(headers: dict[str, str]) -> bool:
    """Les valeurs d'en-tête doivent être de l'ASCII imprimable (httpx les encode en ASCII)."""
    return all(v.isascii() and v.isprintable() for v in headers.values())


async def check_key(
    label: str, method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None = None
) -> KeyTestResult:
    """Envoie la requête de vérification. Ne lève jamais, ne reprend jamais la clé du retour."""
    if not _headers_are_valid(headers):
        return KeyTestResult(ok=False, message=_INVALID_KEY)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.request(method, url, headers=headers, json=body)
    except (httpx.HTTPError, httpx.InvalidURL, UnicodeError, ValueError):
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


def _unavailable(label: str) -> AppError:
    return AppError(
        "llm_models_unavailable",
        f"Impossible de récupérer la liste des modèles {label}.",
        502,
        {"provider": label},
    )


async def get_model_page(
    label: str, url: str, headers: dict[str, str], params: dict[str, Any]
) -> tuple[list[str], str | None]:
    """Une page de `GET /models` : (identifiants, curseur suivant ou `None`).

    Toute erreur (clé invalide, réseau, statut, corps inattendu) devient une `AppError`
    française qui ne contient jamais la clé.
    """
    if not _headers_are_valid(headers):
        raise _unavailable(label)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        page = response.json()
        ids = [m["id"] for m in page["data"]]
        if not all(isinstance(i, str) for i in ids):
            raise TypeError("identifiant de modèle invalide")
        more = page.get("has_more") and page.get("last_id")
        return ids, str(more) if more else None
    except (
        httpx.HTTPError,
        httpx.InvalidURL,
        UnicodeError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
    ) as exc:
        raise _unavailable(label) from exc
