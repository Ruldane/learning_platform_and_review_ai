"""PDF extraction in a subprocess (D72, lifts risk M6 of D63): a booby-trapped PDF (endless Flate
stream, pdfminer loop) can neither block the back end beyond the timeout, nor exhaust its memory.

Each call launches `app.providers.pdf.worker` with the current interpreter; real timeout (the
process is killed), address space capped by the worker (POSIX), at most `concurrency` workers at a
time. stderr is thrown away (never logged: it could quote the content)."""

import asyncio
import contextlib
import logging
import os
import sys
from pathlib import Path

from app.providers.pdf import base
from app.providers.pdf.base import (
    PDF_MAX_MEMORY_BYTES,
    PDF_TIMEOUT_MESSAGE,
    PDF_TIMEOUT_S,
    PdfUnreadable,
)

logger = logging.getLogger(__name__)

# Back-end root (parent of the `app` package): the worker's working directory,
# from where `-m` imports it.
BACKEND_ROOT = Path(__file__).resolve().parents[3]
WORKER_MODULE = "app.providers.pdf.worker"
# Variables passed to the worker: it has no business seeing the rest (API keys...).
_ENV_KEPT = ("PATH", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL")
# A character takes at most 4 UTF-8 bytes.
_BYTES_PER_CHAR = 4


def worker_command(max_pages: int, max_chars: int, max_memory_bytes: int) -> list[str]:
    limits = (max_pages, max_chars, max_memory_bytes)
    return [sys.executable, "-m", WORKER_MODULE, *(str(value) for value in limits)]


async def spawn_worker(command: list[str]) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        cwd=BACKEND_ROOT,
        env={key: os.environ[key] for key in _ENV_KEPT if key in os.environ},
    )


class SubprocessPdfExtractor:
    """`PdfTextExtractor` of the composition. The page and character caps are read at
    each call in `base` and passed to the worker."""

    def __init__(
        self,
        *,
        timeout_s: float = PDF_TIMEOUT_S,
        max_memory_bytes: int = PDF_MAX_MEMORY_BYTES,
        concurrency: int = 2,
    ) -> None:
        self._timeout_s = timeout_s
        self._max_memory_bytes = max_memory_bytes
        self._slots = asyncio.Semaphore(concurrency)

    async def extract_text(self, data: bytes) -> str:
        max_chars = base.MAX_TEXT_CHARS
        command = worker_command(base.MAX_PDF_PAGES, max_chars, self._max_memory_bytes)
        async with self._slots:
            try:
                process = await spawn_worker(command)
            except OSError as exc:
                # EAGAIN, ENOMEM, missing interpreter: unreadable PDF, never the path.
                logger.info("PDF extraction: worker not launched (%s)", type(exc).__name__)
                raise PdfUnreadable() from None
            try:
                async with asyncio.timeout(self._timeout_s):
                    output = await exchange_with_worker(process, data, max_chars * _BYTES_PER_CHAR)
            except TimeoutError:
                logger.info("PDF extraction interrupted: timeout exceeded")
                raise PdfUnreadable(PDF_TIMEOUT_MESSAGE) from None
            finally:
                # Timeout, cancellation or error: the worker never outlives the call.
                await reap_worker(process)
        if output is None or process.returncode != 0:
            logger.info("PDF extraction: worker failed (code %s)", process.returncode)
            raise PdfUnreadable() from None
        return output.decode("utf-8", errors="replace")


async def exchange_with_worker(
    process: asyncio.subprocess.Process, data: bytes, limit: int
) -> bytes | None:
    """Sends the PDF, reads at most `limit` bytes of text and waits for the worker to end. `None`:
    worker dead before having read everything, or output beyond the cap."""
    assert process.stdin is not None and process.stdout is not None
    try:
        process.stdin.write(data)
        await process.stdin.drain()
        process.stdin.close()
    except OSError:  # pipe closed: the worker is already dead (memory, crash)
        return None
    try:
        await process.stdout.readexactly(limit + 1)
    except asyncio.IncompleteReadError as short:
        output = short.partial  # end of stream before the cap: normal case
    else:
        return None
    await process.wait()
    return output


async def reap_worker(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        with contextlib.suppress(ProcessLookupError):  # died meanwhile
            process.kill()
    await process.wait()
