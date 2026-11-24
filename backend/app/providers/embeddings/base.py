"""Port des embeddings : sous-ensemble asynchrone de `langchain_core.embeddings.Embeddings`, pour
qu'une implémentation LangChain reste substituable sans que les features en dépendent."""

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
    """Ce que `GET /health/embedding` lit : l'état du modèle, et le téléchargement s'il manque."""

    async def progress(self) -> EmbeddingProgressData: ...

    async def aclose(self) -> None:
        """À l'arrêt du back : arrête le téléchargement en cours, s'il y en a un."""
