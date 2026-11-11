"""Embeddings par Ollama : `POST {base_url}/api/embed {"model", "input": [...]}`.

Appelé par httpx et non par un SDK (D26, D62). Toute défaillance devient `EmbeddingsUnavailable` ;
ni le texte envoyé ni le corps de réponse n'entrent dans le message ou le journal."""

import logging
from collections.abc import Iterator

import httpx

from app.providers.embeddings.base import EmbeddingsUnavailable

logger = logging.getLogger(__name__)

BATCH_SIZE = 16


def _batches(texts: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(texts), size):
        yield texts[start : start + size]


def _vectors(body: object, expected: int) -> list[list[float]]:
    """Les vecteurs d'une réponse `/api/embed`, ou `ValueError` si elle est incohérente."""
    embeddings = body.get("embeddings") if isinstance(body, dict) else None
    if not isinstance(embeddings, list) or len(embeddings) != expected:
        raise ValueError("embeddings absents ou en nombre inattendu")
    vectors: list[list[float]] = []
    for vector in embeddings:
        if not isinstance(vector, list) or not all(
            isinstance(x, int | float) and not isinstance(x, bool) for x in vector
        ):
            raise ValueError("vecteur mal formé")
        vectors.append([float(x) for x in vector])
    return vectors


class OllamaEmbedder:
    def __init__(
        self, base_url: str, model: str, http: httpx.AsyncClient, *, batch_size: int = BATCH_SIZE
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/api/embed"
        self._model = model
        self._http = http
        self._batch_size = batch_size

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for batch in _batches(texts, self._batch_size):
            out.extend(await self._embed(batch))
        return out

    async def aembed_query(self, text: str) -> list[float]:
        return (await self._embed([text]))[0]

    async def _embed(self, batch: list[str]) -> list[list[float]]:
        try:
            response = await self._http.post(self._url, json={"model": self._model, "input": batch})
            response.raise_for_status()
            return _vectors(response.json(), len(batch))
        except (httpx.HTTPError, ValueError) as exc:
            # Statut HTTP ou type seulement : jamais le texte de l'exception ni le corps.
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
            logger.warning(
                "Embeddings Ollama indisponibles : %s (statut %s)", type(exc).__name__, status
            )
            raise EmbeddingsUnavailable() from None
