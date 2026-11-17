"""Téléchargement de `bge-m3` par Ollama et sa progression (P13, 15.5) : si le modèle manque, le
back lance **un seul** `POST /api/pull` en flux à la fois et garde en mémoire le dernier
pourcentage. `GET /health/embedding` le lit (public, comme `/health`).

Le flux d'Ollama est un JSON par ligne ; les lignes d'un fichier portent `digest`, `total` et
`completed`. Le plus gros fichier (le modèle lui-même) donne le pourcentage : les petits fichiers
(licence, paramètres) se terminent en un instant et ne doivent pas faire sauter la barre à 100.
Rien du flux n'est journalisé (seulement la classe d'une exception).

Un tirage qui échoue (ligne `error`, statut non 200, connexion coupée, flux fermé sans la ligne
`success`) est relancé après un délai qui croît (30 s, 60 s, 120 s... plafonné à 5 min) ; un
tirage « réussi » dont le modèle n'est toujours pas listé l'est après 30 s. `aclose` l'arrête."""

import asyncio
import contextlib
import json
import logging
import math
import time
from collections.abc import Callable

import httpx

from app.providers.embeddings.base import EmbeddingProgressData

logger = logging.getLogger(__name__)

PULL_TIMEOUT = httpx.Timeout(10.0, read=120.0)  # le flux d'un gros fichier peut se faire attendre
RETRY_AFTER_FAILURE_S = 30.0  # premier délai ; double à chaque échec de suite
MAX_RETRY_DELAY_S = 300.0
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
        self._ended_at: float | None = None  # fin du dernier tirage (réussi ou non)
        self._ended_ok = False  # ce tirage est allé jusqu'à la ligne `success`
        self._failures = 0  # échecs de suite

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
        if self._ended_at is not None:
            remaining = self._retry_delay() - (self._clock() - self._ended_at)
            if remaining > 0:
                return self._ended(remaining)
        # Aucun `await` entre le contrôle et la création : deux appels n'en lancent qu'un.
        self._layers.clear()
        self._ended_at = None
        self._task = asyncio.create_task(self._pull())
        return self._running()

    def _retry_delay(self) -> float:
        if self._ended_ok or self._failures < 1:
            return RETRY_AFTER_FAILURE_S
        return float(min(RETRY_AFTER_FAILURE_S * 2 ** (self._failures - 1), MAX_RETRY_DELAY_S))

    def _ended(self, remaining: float) -> EmbeddingProgressData:
        """Le dernier tirage est fini depuis peu : réussi (le modèle n'est pas encore listé) ou en
        échec (on attend avant de relancer)."""
        if self._ended_ok:
            return self._data(
                present=False,
                percent=99,
                detail=f"Téléchargement de {self._model} terminé, vérification en cours.",
            )
        return self._data(
            present=False,
            percent=None,
            detail=(
                f"Le téléchargement de {self._model} a échoué ; nouvel essai dans "
                f"{math.ceil(remaining)} s. Vérifie qu'Ollama tourne "
                "(`docker compose ps ollama`) et qu'il reste de la place sur le disque."
            ),
        )

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

    def _read(self, line: str) -> bool:
        """Lit une ligne du flux ; vrai pour la ligne `success` qui clôt le téléchargement."""
        payload = json.loads(line)
        if not isinstance(payload, dict):
            return False
        if "error" in payload:
            raise _PullFailed
        total, done, digest = payload.get("total"), payload.get("completed"), payload.get("digest")
        if isinstance(total, int) and isinstance(digest, str) and total > 0:
            self._layers[digest] = (done if isinstance(done, int) else 0, total)
        return payload.get("status") == "success"

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
                succeeded = False
                async for line in response.aiter_lines():
                    if line.strip():
                        succeeded = self._read(line) or succeeded
                if not succeeded:  # flux fermé avant la fin : une coupure, pas un succès
                    raise _PullFailed
            self._end(ok=True)
            logger.info("téléchargement du modèle d'embeddings terminé")
        except Exception as exc:  # jamais le message : il pourrait citer une adresse
            self._end(ok=False)
            logger.warning("téléchargement d'embeddings en échec : %s", type(exc).__name__)

    def _end(self, *, ok: bool) -> None:
        self._ended_at = self._clock()
        self._ended_ok = ok
        self._failures = 0 if ok else self._failures + 1

    async def aclose(self) -> None:
        """À l'arrêt du back : annule le téléchargement en cours et attend sa fin (rien n'est
        journalisé comme un échec)."""
        task, self._task = self._task, None
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
