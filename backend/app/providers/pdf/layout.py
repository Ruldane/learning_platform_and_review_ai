"""Mise en page d'un CV en sous-processus (D119, mêmes gardes que D72) : un PDF piégé ne peut ni
bloquer le back au-delà du délai, ni épuiser sa mémoire.

Chaque appel lance `app.providers.pdf.layout_worker` avec l'interpréteur courant ; délai réel (le
processus est tué), espace d'adressage plafonné (POSIX), `concurrency` workers au plus à la fois,
environnement réduit (aucune clé d'API), sortie JSON bornée à `LAYOUT_MAX_OUTPUT_BYTES`. stderr
est jeté ; le journal ne garde que le code de sortie et le nombre de pages.

`LocalPdfLayoutExtractor` fait le même travail dans un thread, sans délai réel ni plafond de
mémoire : extracteur réel mais local des tests (aucun processus lancé)."""

import asyncio
import base64
import binascii
import json
import logging
import sys
import threading
from typing import Any

from app.providers.pdf import base
from app.providers.pdf.base import (
    CV_TOO_LONG_MESSAGE,
    LAYOUT_MAX_OUTPUT_BYTES,
    LAYOUT_TIMEOUT_S,
    PDF_MAX_MEMORY_BYTES,
    PDF_TIMEOUT_MESSAGE,
    PageLayout,
    PdfLayout,
    PdfUnreadable,
    TextBlock,
)
from app.providers.pdf.subprocess import exchange_with_worker, reap_worker, spawn_worker

logger = logging.getLogger(__name__)

WORKER_MODULE = "app.providers.pdf.layout_worker"
# Code de sortie du worker pour « trop de pages » (`layout_worker.EXIT_TOO_MANY_PAGES`, qui n'est
# pas importé ici : le parent ne charge ni pdfplumber ni PDFium).
EXIT_TOO_MANY_PAGES = 4
_BLOCK_FIELDS = 10


def worker_command(max_memory_bytes: int) -> list[str]:
    """Plafonds lus à chaque appel dans `base` (pages, résolution, côté de page)."""
    limits = (base.MAX_CV_PAGES, max_memory_bytes, base.LAYOUT_DPI, base.MAX_PAGE_SIDE_PT)
    return [sys.executable, "-m", WORKER_MODULE, *(str(value) for value in limits)]


class SubprocessPdfLayoutExtractor:
    """`PdfLayoutExtractor` de la composition."""

    def __init__(
        self,
        *,
        timeout_s: float = LAYOUT_TIMEOUT_S,
        max_memory_bytes: int = PDF_MAX_MEMORY_BYTES,
        concurrency: int = 2,
    ) -> None:
        self._timeout_s = timeout_s
        self._max_memory_bytes = max_memory_bytes
        self._slots = asyncio.Semaphore(concurrency)

    async def extract_layout(self, data: bytes) -> PdfLayout:
        command = worker_command(self._max_memory_bytes)
        async with self._slots:
            try:
                process = await spawn_worker(command)
            except OSError as exc:
                logger.info("Mise en page PDF : worker non lancé (%s)", type(exc).__name__)
                raise PdfUnreadable() from None
            try:
                async with asyncio.timeout(self._timeout_s):
                    output = await exchange_with_worker(process, data, LAYOUT_MAX_OUTPUT_BYTES)
            except TimeoutError:
                logger.info("Mise en page PDF interrompue : délai dépassé")
                raise PdfUnreadable(PDF_TIMEOUT_MESSAGE) from None
            finally:
                # Délai, annulation ou erreur : le worker ne survit jamais à l'appel.
                await reap_worker(process)
        code = process.returncode
        if code == EXIT_TOO_MANY_PAGES:
            logger.info("Mise en page PDF refusée : trop de pages (code %s)", code)
            raise PdfUnreadable(CV_TOO_LONG_MESSAGE) from None
        if output is None or code != 0:
            logger.info("Mise en page PDF : worker en échec (code %s)", code)
            raise PdfUnreadable() from None
        layout = parse_layout(output)
        logger.info("Mise en page PDF extraite (code %s, %s pages)", code, len(layout.pages))
        return layout


# PDFium n'accepte pas deux appels à la fois dans un même processus.
_PDFIUM_LOCK = threading.Lock()


def _extract_locally(data: bytes) -> bytes:
    from app.providers.pdf.layout_extract import extract_layout_payload

    with _PDFIUM_LOCK:
        payload = extract_layout_payload(
            data, base.MAX_CV_PAGES, base.LAYOUT_DPI, base.MAX_PAGE_SIDE_PT
        )
    return json.dumps(payload, ensure_ascii=True).encode("ascii")


class LocalPdfLayoutExtractor:
    """`PdfLayoutExtractor` dans un thread (tests) : même extraction et même relecture que le
    worker, mêmes refus."""

    async def extract_layout(self, data: bytes) -> PdfLayout:
        from app.providers.pdf.layout_extract import TooManyPages

        try:
            output = await asyncio.to_thread(_extract_locally, data)
        except TooManyPages:
            raise PdfUnreadable(CV_TOO_LONG_MESSAGE) from None
        except Exception as exc:
            logger.info("Mise en page PDF illisible (%s)", type(exc).__name__)
            raise PdfUnreadable() from None
        return parse_layout(output)


def _block(raw: Any) -> TextBlock:
    if not isinstance(raw, list) or len(raw) != _BLOCK_FIELDS:
        raise ValueError("bloc mal formé")
    text, x0, top, x1, bottom, font, size, color, bold, invisible = raw
    if not all(isinstance(value, str) for value in (text, font, color)):
        raise ValueError("bloc mal formé")
    if not isinstance(bold, bool) or not isinstance(invisible, bool):
        raise ValueError("bloc mal formé")
    return TextBlock(
        text,
        float(x0),
        float(top),
        float(x1),
        float(bottom),
        font,
        float(size),
        color,
        bold,
        invisible,
    )


def _page(raw: Any) -> PageLayout:
    if not isinstance(raw["stream"], str) or not isinstance(raw["blocks"], list):
        raise ValueError("page mal formée")
    return PageLayout(
        width_pt=float(raw["width"]),
        height_pt=float(raw["height"]),
        blocks=[_block(block) for block in raw["blocks"]],
        image_png=_png_bytes(raw["png"]),
        stream_text=raw["stream"],
    )


def _png_bytes(value: Any) -> bytes:
    if not isinstance(value, str):
        raise ValueError("image mal formée")
    return base64.b64decode(value, validate=True)


def parse_layout(output: bytes) -> PdfLayout:
    """Sortie JSON du worker relue en `PdfLayout` ; toute forme inattendue (sortie tronquée,
    worker remplacé) donne `PdfUnreadable`, jamais une erreur interne."""
    try:
        payload = json.loads(output)
        pages = [_page(page) for page in payload["pages"]]
        fonts = payload["fonts"]
        selectable = payload["selectable"]
        if not isinstance(fonts, list) or not all(isinstance(name, str) for name in fonts):
            raise ValueError("polices mal formées")
        if not isinstance(selectable, bool) or not 1 <= len(pages) <= base.MAX_CV_PAGES:
            raise ValueError("mise en page mal formée")
    except (ValueError, KeyError, TypeError, binascii.Error) as exc:
        logger.info("Mise en page PDF : sortie du worker illisible (%s)", type(exc).__name__)
        raise PdfUnreadable() from None
    return PdfLayout(pages=pages, fonts=list(fonts), selectable=selectable)
