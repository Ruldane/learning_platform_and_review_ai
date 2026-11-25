"""Embeddings port: an async subset of `langchain_core.embeddings.Embeddings`, so that a LangChain
implementation stays swappable without the features depending on it."""

from dataclasses import dataclass
from typing import Protocol

from app.core.errors import AppError


class Embedder(Protocol):
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def aembed_query(self, text: str) -> list[float]: ...


class EmbeddingsUnavailable(AppError):
    """Ollama is unreachable, too slow, missing the model, or returned an invalid reply."""

    def __init__(self) -> None:
        super().__init__(
            "embeddings_unavailable",
            "The embedding service (Ollama) is unavailable or the bge-m3 model "
            "has not been downloaded yet.",
            status_code=503,
        )


@dataclass(frozen=True)
class EmbeddingProgressData:
    """Embedding model download status with an English, privacy-safe status detail.

    Percent is 0 to 99 during the download, 100 when ready, or None until the size is known.
    """

    model: str
    present: bool
    percent: int | None
    detail: str


class EmbeddingProgressSource(Protocol):
    """What `GET /health/embedding` reads: the state of the model, and the download if it is
    missing."""

    async def progress(self) -> EmbeddingProgressData: ...

    async def aclose(self) -> None:
        """On backend shutdown: stops the current download, if there is one."""
