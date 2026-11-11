"""Extraction PDF en sous-processus (D72, lève le risque M6 de D63) : un PDF piégé (flux Flate
sans fin, boucle de pdfminer) ne peut ni bloquer le back au-delà du délai, ni épuiser sa mémoire.

Chaque appel lance `app.providers.pdf.worker` avec l'interpréteur courant ; délai réel (le
processus est tué), espace d'adressage plafonné par le worker (POSIX), `concurrency` workers au
plus à la fois. stderr est jeté (jamais journalisé : il pourrait citer le contenu)."""

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

# Racine du back (parent du paquet `app`) : répertoire de travail du worker, d'où `-m` l'importe.
BACKEND_ROOT = Path(__file__).resolve().parents[3]
WORKER_MODULE = "app.providers.pdf.worker"
# Variables transmises au worker : le reste de l'environnement (clés d'API...) ne le regarde pas.
_ENV_KEPT = ("PATH", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL")
# Un caractère tient en 4 octets UTF-8 au plus.
_BYTES_PER_CHAR = 4


def worker_command(max_pages: int, max_chars: int, max_memory_bytes: int) -> list[str]:
    limits = (max_pages, max_chars, max_memory_bytes)
    return [sys.executable, "-m", WORKER_MODULE, *(str(value) for value in limits)]


async def _spawn(command: list[str]) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        cwd=BACKEND_ROOT,
        env={key: os.environ[key] for key in _ENV_KEPT if key in os.environ},
    )


class SubprocessPdfExtractor:
    """`PdfTextExtractor` de la composition. Les plafonds de pages et de caractères sont lus à
    chaque appel dans `base` et passés au worker."""

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
            process = await _spawn(command)
            try:
                async with asyncio.timeout(self._timeout_s):
                    output = await _exchange(process, data, max_chars * _BYTES_PER_CHAR)
            except TimeoutError:
                logger.info("Extraction PDF interrompue : délai dépassé")
                raise PdfUnreadable(PDF_TIMEOUT_MESSAGE) from None
            finally:
                # Délai, annulation ou erreur : le worker ne survit jamais à l'appel.
                await _reap(process)
        if output is None or process.returncode != 0:
            logger.info("Extraction PDF : worker en échec (code %s)", process.returncode)
            raise PdfUnreadable() from None
        return output.decode("utf-8", errors="replace")


async def _exchange(process: asyncio.subprocess.Process, data: bytes, limit: int) -> bytes | None:
    """Envoie le PDF, lit au plus `limit` octets de texte et attend la fin du worker. `None` :
    worker mort avant d'avoir tout lu, ou sortie au-delà du plafond."""
    assert process.stdin is not None and process.stdout is not None
    try:
        process.stdin.write(data)
        await process.stdin.drain()
        process.stdin.close()
    except OSError:  # tube fermé : le worker est déjà mort (mémoire, plantage)
        return None
    try:
        await process.stdout.readexactly(limit + 1)
    except asyncio.IncompleteReadError as short:
        output = short.partial  # fin de flux avant le plafond : cas normal
    else:
        return None
    await process.wait()
    return output


async def _reap(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        with contextlib.suppress(ProcessLookupError):  # mort entre-temps
            process.kill()
    await process.wait()
