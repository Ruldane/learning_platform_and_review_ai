"""Download of `bge-m3` by Ollama and its progress (P13, 15.5): if the model is missing, the
back end launches **a single** streaming `POST /api/pull` at a time and keeps the last
percentage in memory. `GET /health/embedding` reads it (public, like `/health`).

Ollama's stream is one JSON per line; the lines of a file carry `digest`, `total` and
`completed`. The biggest file (the model itself) gives the percentage: the small files
(licence, parameters) end in an instant and must not make the bar jump to 100.
Nothing from the stream is logged (only the class of an exception).

A pull that fails (`error` line, non-200 status, connection cut, stream closed without the
`success` line) is relaunched after a growing delay (30 s, 60 s, 120 s... capped at 5 min); a
"successful" pull whose model is still not listed is relaunched after 30 s. `aclose` stops it."""

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

PULL_TIMEOUT = httpx.Timeout(10.0, read=120.0)  # the stream of a big file can keep us waiting
RETRY_AFTER_FAILURE_S = 30.0  # first delay; doubles at each failure in a row
MAX_RETRY_DELAY_S = 300.0
DOWN_DETAIL = "Ollama is not responding."


class _PullFailed(Exception):
    """Ollama answered with an error in the stream (the message is never repeated)."""


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
        self._layers: dict[str, tuple[int, int]] = {}  # digest -> (completed, total)
        self._ended_at: float | None = None  # end of the last pull (successful or not)
        self._ended_ok = False  # this pull went all the way to the `success` line
        self._failures = 0  # failures in a row

    def _data(self, *, present: bool, percent: int | None, detail: str) -> EmbeddingProgressData:
        return EmbeddingProgressData(self._model, present, percent, detail)

    async def _present(self) -> bool:
        response = await self._http.get(f"{self._url}/api/tags")
        if response.status_code != 200:
            raise httpx.HTTPError("unexpected status")
        models = response.json().get("models")
        if not isinstance(models, list):
            if models:  # an unexpected type is not an empty list: Ollama answered something else
                raise ValueError("unexpected model list")
            models = []
        names = [m.get("name") for m in models if isinstance(m, dict)]
        return any(isinstance(n, str) and self._model in (n, n.split(":", 1)[0]) for n in names)

    async def progress(self) -> EmbeddingProgressData:
        try:
            if await self._present():
                return self._data(present=True, percent=100, detail=f"{self._model} is ready.")
        except (httpx.HTTPError, ValueError, AttributeError, TypeError, RecursionError):
            return self._data(present=False, percent=None, detail=DOWN_DETAIL)
        return self._missing()

    def _missing(self) -> EmbeddingProgressData:
        """The model is missing: the download is running, has just finished, or has just failed."""
        if self._task is not None and not self._task.done():
            return self._running()
        if self._ended_at is not None:
            remaining = self._retry_delay() - (self._clock() - self._ended_at)
            if remaining > 0:
                return self._ended(remaining)
        # No `await` between the check and the creation: two calls only launch one.
        self._layers.clear()
        self._ended_at = None
        self._task = asyncio.create_task(self._pull())
        return self._running()

    def _retry_delay(self) -> float:
        if self._ended_ok or self._failures < 1:
            return RETRY_AFTER_FAILURE_S
        return float(min(RETRY_AFTER_FAILURE_S * 2 ** (self._failures - 1), MAX_RETRY_DELAY_S))

    def _ended(self, remaining: float) -> EmbeddingProgressData:
        """The last pull ended a short while ago: successful (the model is not listed yet) or
        failed (we wait before relaunching)."""
        if self._ended_ok:
            return self._data(
                present=False,
                percent=99,
                detail=f"{self._model} has downloaded. Verifying it now.",
            )
        return self._data(
            present=False,
            percent=None,
            detail=(
                f"The {self._model} download failed. Retrying in {math.ceil(remaining)} s. "
                "Check that Ollama is running (`docker compose ps ollama`) "
                "and that the disk has free space."
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
        suffix = f" ({percent}%)" if percent is not None else ""
        return self._data(
            present=False,
            percent=percent,
            detail=f"Downloading {self._model}{suffix}.",
        )

    def _read(self, line: str) -> bool:
        """Reads a line of the stream; true for the `success` line that ends the download."""
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
                if not succeeded:  # stream closed before the end: a cut, not a success
                    raise _PullFailed
            self._end(ok=True)
            logger.info("embeddings model download finished")
        except Exception as exc:  # never the message: it could quote an address
            self._end(ok=False)
            logger.warning("embeddings download failed: %s", type(exc).__name__)

    def _end(self, *, ok: bool) -> None:
        self._ended_at = self._clock()
        self._ended_ok = ok
        self._failures = 0 if ok else self._failures + 1

    async def aclose(self) -> None:
        """When the back end stops: cancels the download in progress and waits for it to end
        (nothing is logged as a failure)."""
        task, self._task = self._task, None
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
