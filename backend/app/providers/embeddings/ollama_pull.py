"""Téléchargement de `bge-m3` par Ollama et sa progression (P13, 15.5) : si le modèle manque, le
back lance **un seul** `POST /api/pull` en flux à la fois et garde en mémoire le dernier
pourcentage. `GET /health/embedding` le lit (public, comme `/health`).

Le flux d'Ollama est un JSON par ligne ; les lignes d'un fichier portent `digest`, `total` et
`completed`. Le plus gros fichier (le modèle lui-même) donne le pourcentage : les petits fichiers
(licence, paramètres) se terminent en un instant et ne doivent pas faire sauter la barre à 100.
Rien du flux n'est journalisé (seulement la classe d'une exception)."""

import asyncio
import json
import logging
import time
from collections.abc import Callable

import httpx

from app.providers.embeddings.base import EmbeddingProgressData

logger = logging.getLogger(__name__)

PULL_TIMEOUT = httpx.Timeout(10.0, read=120.0)  # le flux d'un gros fichier peut se faire attendre
RETRY_AFTER_FAILURE_S = 30.0
DOWN_DETAIL = "Ollama ne répond pas."


class _PullFailed(Exception):
    """Ollama a répondu une erreur dans le flux (le message n'est jamais repris)."""


class OllamaPullWatcher:
    def __init__(
        self,
        url: str,
        model: str,
        http: httpx.AsyncClient,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = url.rstrip("/")
        self._model = model
        self._http = http
        self._clock = clock
        self._task: asyncio.Task[None] | None = None
        self._layers: dict[str, tuple[int, int]] = {}  # digest -> (terminé, total)
        self._finished = False  # le flux est allé au bout
        self._failed_at: float | None = None

    def _data(self, *, present: bool, percent: int | None, detail: str) -> EmbeddingProgressData:
        return EmbeddingProgressData(self._model, present, percent, detail)

    async def _present(self) -> bool:
        response = await self._http.get(f"{self._url}/api/tags")
        if response.status_code != 200:
            raise httpx.HTTPError("statut inattendu")
        models = response.json().get("models")
        names = [m.get("name") for m in models if isinstance(m, dict)] if models else []
        return any(isinstance(n, str) and self._model in (n, n.split(":", 1)[0]) for n in names)

    async def progress(self) -> EmbeddingProgressData:
        try:
            if await self._present():
                return self._data(
                    present=True, percent=100, detail=f"Le modèle {self._model} est prêt."
                )
        except (httpx.HTTPError, ValueError, AttributeError):
            return self._data(present=False, percent=None, detail=DOWN_DETAIL)
        return self._missing()

    def _missing(self) -> EmbeddingProgressData:
        """Le modèle manque : le téléchargement tourne, vient de finir, ou vient d'échouer."""
        if self._task is not None and not self._task.done():
            return self._running()
        if self._finished:
            return self._data(
                present=False,
                percent=99,
                detail=f"Téléchargement de {self._model} terminé, vérification en cours.",
            )
        if self._failed_at is not None and self._clock() - self._failed_at < RETRY_AFTER_FAILURE_S:
            return self._data(
                present=False,
                percent=None,
                detail=f"Le téléchargement de {self._model} a échoué ; nouvel essai bientôt.",
            )
        # Aucun `await` entre le contrôle et la création : deux appels n'en lancent qu'un.
        self._layers.clear()
        self._failed_at = None
        self._task = asyncio.create_task(self._pull())
        return self._running()

    def _percent(self) -> int | None:
        sized = [(total, done) for done, total in self._layers.values() if total > 0]
        if not sized:
            return None
        total, done = max(sized)
        return max(0, min(99, round(100 * done / total)))

    def _running(self) -> EmbeddingProgressData:
        percent = self._percent()
        suffix = f" ({percent} %)" if percent is not None else ""
        return self._data(
            present=False,
            percent=percent,
            detail=f"Téléchargement de {self._model} en cours{suffix}.",
        )

    def _read(self, line: str) -> None:
        payload = json.loads(line)
        if not isinstance(payload, dict):
            return
        if "error" in payload:
            raise _PullFailed
        total, done, digest = payload.get("total"), payload.get("completed"), payload.get("digest")
        if isinstance(total, int) and isinstance(digest, str) and total > 0:
            self._layers[digest] = (done if isinstance(done, int) else 0, total)

    async def _pull(self) -> None:
        try:
            async with self._http.stream(
                "POST",
                f"{self._url}/api/pull",
                json={"name": self._model, "stream": True},
                timeout=PULL_TIMEOUT,
            ) as response:
                if response.status_code != 200:
                    raise _PullFailed
                async for line in response.aiter_lines():
                    if line.strip():
                        self._read(line)
            self._finished = True
            logger.info("téléchargement du modèle d'embeddings terminé")
        except Exception as exc:  # jamais le message : il pourrait citer une adresse
            self._failed_at = self._clock()
            logger.warning("téléchargement d'embeddings en échec : %s", type(exc).__name__)
