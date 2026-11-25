"""Embeddings through Ollama: `POST {base_url}/api/embed {"model", "input": [...]}`.

Called by httpx and not by an SDK (D26, D62). Any failure becomes `EmbeddingsUnavailable`;
neither the text sent nor the response body enters the message or the log."""

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
    """The vectors of an `/api/embed` response, or `ValueError` if it is inconsistent."""
    embeddings = body.get("embeddings") if isinstance(body, dict) else None
    if not isinstance(embeddings, list) or len(embeddings) != expected:
        raise ValueError("embeddings missing or in an unexpected number")
    vectors: list[list[float]] = []
    for vector in embeddings:
        if not isinstance(vector, list) or not all(
            isinstance(x, int | float) and not isinstance(x, bool) for x in vector
        ):
            raise ValueError("malformed vector")
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

    async def _fetch(self, batch: list[str]) -> list[list[float]]:
        try:
            response = await self._http.post(self._url, json={"model": self._model, "input": batch})
        except httpx.ReadTimeout:
            # A batch of long fragments may exceed the timeout on CPU.
            if len(batch) == 1:
                raise
            middle = len(batch) // 2
            return await self._fetch(batch[:middle]) + await self._fetch(batch[middle:])
        response.raise_for_status()
        return _vectors(response.json(), len(batch))

    async def _embed(self, batch: list[str]) -> list[list[float]]:
        try:
            return await self._fetch(batch)
        except (httpx.HTTPError, ValueError) as exc:
            # HTTP status or type only: never the exception's text or the body.
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
            logger.warning(
                "Ollama embeddings unavailable: %s (status %s)", type(exc).__name__, status
            )
            raise EmbeddingsUnavailable() from None
