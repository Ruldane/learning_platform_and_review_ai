"""Layout of a CV in a subprocess (D119, same guards as D72): a booby-trapped PDF can neither
block the back end beyond the timeout, nor exhaust its memory.

Each call launches `app.providers.pdf.layout_worker` with the current interpreter; real timeout
(the process is killed), capped address space (POSIX), at most `concurrency` workers at a time,
reduced environment (no API key), JSON output bounded to `LAYOUT_MAX_OUTPUT_BYTES`. stderr
is thrown away; the log only keeps the exit code and the page count.

`LocalPdfLayoutExtractor` does the same work in a thread, without a real timeout or memory
cap: a real but local extractor for the tests (no process launched)."""

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
    ROTATED_PAGE_MESSAGE,
    PageLayout,
    PdfLayout,
    PdfUnreadable,
    TextBlock,
)
from app.providers.pdf.subprocess import exchange_with_worker, reap_worker, spawn_worker

logger = logging.getLogger(__name__)

WORKER_MODULE = "app.providers.pdf.layout_worker"
# Worker exit codes (`layout_worker.EXIT_*`, not imported here: the parent loads neither
# pdfplumber nor PDFium): too many pages, rotated page with text.
EXIT_TOO_MANY_PAGES = 4
EXIT_ROTATED_PAGE = 5
_BLOCK_FIELDS = 10


def worker_command(max_memory_bytes: int, max_pages: int = base.MAX_CV_PAGES) -> list[str]:
    """Limits read at each call in `base` (pages, resolution, page side)."""
    limits = (max_pages, max_memory_bytes, base.LAYOUT_DPI, base.MAX_PAGE_SIDE_PT)
    return [sys.executable, "-m", WORKER_MODULE, *(str(value) for value in limits)]


class SubprocessPdfLayoutExtractor:
    """`PdfLayoutExtractor` of the composition."""

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

    async def extract_layout(self, data: bytes, *, max_pages: int = base.MAX_CV_PAGES) -> PdfLayout:
        command = worker_command(self._max_memory_bytes, max_pages)
        async with self._slots:
            try:
                process = await spawn_worker(command)
            except OSError as exc:
                logger.info("PDF layout: worker not launched (%s)", type(exc).__name__)
                raise PdfUnreadable() from None
            try:
                async with asyncio.timeout(self._timeout_s):
                    output = await exchange_with_worker(process, data, LAYOUT_MAX_OUTPUT_BYTES)
            except TimeoutError:
                logger.info("PDF layout interrupted: timeout exceeded")
                raise PdfUnreadable(PDF_TIMEOUT_MESSAGE) from None
            finally:
                # Timeout, cancellation or error: the worker never outlives the call.
                await reap_worker(process)
        code = process.returncode
        if code == EXIT_TOO_MANY_PAGES:
            logger.info("PDF layout refused: too many pages (code %s)", code)
            raise PdfUnreadable(CV_TOO_LONG_MESSAGE) from None
        if code == EXIT_ROTATED_PAGE:
            logger.info("PDF layout refused: rotated page (code %s)", code)
            raise PdfUnreadable(ROTATED_PAGE_MESSAGE) from None
        if output is None or code != 0:
            logger.info("PDF layout: worker failed (code %s)", code)
            raise PdfUnreadable() from None
        # Outside the event loop: re-reading 40 MB of JSON blocks it (review 6.3, I4).
        layout = await asyncio.to_thread(parse_layout, output, max_pages)
        logger.info("PDF layout extracted (code %s, %s pages)", code, len(layout.pages))
        return layout


# PDFium does not accept two calls at a time in the same process.
_PDFIUM_LOCK = threading.Lock()


def _extract_locally(data: bytes, max_pages: int) -> bytes:
    from app.providers.pdf.layout_extract import extract_layout_payload

    with _PDFIUM_LOCK:
        payload = extract_layout_payload(data, max_pages, base.LAYOUT_DPI, base.MAX_PAGE_SIDE_PT)
    return json.dumps(payload, ensure_ascii=True).encode("ascii")


class LocalPdfLayoutExtractor:
    """`PdfLayoutExtractor` in a thread (tests): same extraction and same re-reading as the
    worker, same refusals."""

    async def extract_layout(self, data: bytes, *, max_pages: int = base.MAX_CV_PAGES) -> PdfLayout:
        from app.providers.pdf.layout_extract import RotatedPage, TooManyPages

        try:
            output = await asyncio.to_thread(_extract_locally, data, max_pages)
        except TooManyPages:
            raise PdfUnreadable(CV_TOO_LONG_MESSAGE) from None
        except RotatedPage:
            raise PdfUnreadable(ROTATED_PAGE_MESSAGE) from None
        except Exception as exc:
            logger.info("PDF layout unreadable (%s)", type(exc).__name__)
            raise PdfUnreadable() from None
        return await asyncio.to_thread(parse_layout, output)


def _block(raw: Any) -> TextBlock:
    if not isinstance(raw, list) or len(raw) != _BLOCK_FIELDS:
        raise ValueError("malformed block")
    text, x0, top, x1, bottom, font, size, color, bold, invisible = raw
    if not all(isinstance(value, str) for value in (text, font, color)):
        raise ValueError("malformed block")
    if not isinstance(bold, bool) or not isinstance(invisible, bool):
        raise ValueError("malformed block")
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
        raise ValueError("malformed page")
    return PageLayout(
        width_pt=float(raw["width"]),
        height_pt=float(raw["height"]),
        blocks=[_block(block) for block in raw["blocks"]],
        image_png=_png_bytes(raw["png"]),
        stream_text=raw["stream"],
    )


def _png_bytes(value: Any) -> bytes:
    if not isinstance(value, str):
        raise ValueError("malformed image")
    return base64.b64decode(value, validate=True)


def parse_layout(output: bytes, max_pages: int = base.MAX_CV_PAGES) -> PdfLayout:
    """JSON output of the worker read back into a `PdfLayout`; any unexpected shape (truncated
    output, replaced worker) gives `PdfUnreadable`, never an internal error."""
    try:
        payload = json.loads(output)
        pages = [_page(page) for page in payload["pages"]]
        fonts = payload["fonts"]
        selectable = payload["selectable"]
        if not isinstance(fonts, list) or not all(isinstance(name, str) for name in fonts):
            raise ValueError("malformed fonts")
        if not isinstance(selectable, bool) or not 1 <= len(pages) <= max_pages:
            raise ValueError("malformed layout")
    except (ValueError, KeyError, TypeError, binascii.Error) as exc:
        logger.info("PDF layout: worker output unreadable (%s)", type(exc).__name__)
        raise PdfUnreadable() from None
    return PdfLayout(pages=pages, fonts=list(fonts), selectable=selectable)
