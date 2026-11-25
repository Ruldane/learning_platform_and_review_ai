"""Worker de mise en page (D119) : mêmes gardes que l'extraction du texte (D72), délai, mémoire,
environnement réduit, sortie bornée et relue strictement."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.providers.pdf import layout as pdf_layout
from app.providers.pdf import layout_worker
from app.providers.pdf.base import (
    LAYOUT_MAX_OUTPUT_BYTES,
    LAYOUT_TIMEOUT_S,
    MAX_PAGE_SIDE_PT,
    PDF_MAX_MEMORY_BYTES,
    PDF_TIMEOUT_MESSAGE,
    PdfUnreadable,
)
from app.providers.pdf.layout import SubprocessPdfLayoutExtractor, parse_layout, worker_command
from app.providers.pdf.subprocess import BACKEND_ROOT
from scripts.sample_cv import SampleCv, make_cv_pdf

_UNREADABLE = "The PDF is unreadable (password-protected or damaged)."
_EMPTY_PAGE = {"width": 1, "height": 1, "blocks": [], "png": "", "stream": ""}


def _payload(**page: object) -> str:
    return json.dumps({"pages": [{**_EMPTY_PAGE, **page}], "fonts": [], "selectable": False})


class _Spawned:
    """Espion de `spawn_worker` (vu depuis `layout`) : processus lancés, vivants au plus."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.processes: list[asyncio.subprocess.Process] = []
        self.max_alive = 0
        real = pdf_layout.spawn_worker

        async def spy(command: list[str]) -> asyncio.subprocess.Process:
            process = await real(command)
            self.processes.append(process)
            alive = sum(p.returncode is None for p in self.processes)
            self.max_alive = max(self.max_alive, alive)
            return process

        monkeypatch.setattr(pdf_layout, "spawn_worker", spy)


def _fake_worker(monkeypatch: pytest.MonkeyPatch, code: str) -> None:
    monkeypatch.setattr(pdf_layout, "worker_command", lambda *_args: [sys.executable, "-c", code])


def test_defaults_and_worker_command() -> None:
    assert LAYOUT_TIMEOUT_S == 60.0 and LAYOUT_MAX_OUTPUT_BYTES == 40 * 1024 * 1024
    assert worker_command(PDF_MAX_MEMORY_BYTES) == [
        sys.executable,
        "-m",
        "app.providers.pdf.layout_worker",
        "4",
        str(PDF_MAX_MEMORY_BYTES),
        "72",
        str(MAX_PAGE_SIDE_PT),
    ]
    assert pdf_layout.EXIT_TOO_MANY_PAGES == layout_worker.EXIT_TOO_MANY_PAGES


async def test_worker_is_killed_at_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_worker(monkeypatch, "while True: pass")
    spawned = _Spawned(monkeypatch)
    with pytest.raises(PdfUnreadable) as caught:
        await SubprocessPdfLayoutExtractor(timeout_s=0.5).extract_layout(make_cv_pdf())
    assert caught.value.message == PDF_TIMEOUT_MESSAGE and caught.value.__cause__ is None
    assert len(spawned.processes) == 1 and spawned.processes[0].returncode is not None


async def test_cancelled_call_kills_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_worker(monkeypatch, "import time; time.sleep(30)")
    spawned = _Spawned(monkeypatch)
    task = asyncio.create_task(SubprocessPdfLayoutExtractor().extract_layout(b"%PDF-"))
    while not spawned.processes:
        await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert spawned.processes[0].returncode is not None


async def test_worker_gets_no_api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZAI_API_KEY", "cle-secrete")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-secrete")
    code = (
        "import json, os, sys; sys.stdin.buffer.read(); "
        "page = {'width': 1, 'height': 1, 'blocks': [], 'png': '', "
        "'stream': ','.join(sorted(os.environ))}; "
        "sys.stdout.write(json.dumps({'pages': [page], 'fonts': [], 'selectable': False}))"
    )
    _fake_worker(monkeypatch, code)
    layout = await SubprocessPdfLayoutExtractor().extract_layout(b"%PDF-")
    names = layout.pages[0].stream_text.split(",")
    assert "ZAI_API_KEY" not in names and "ANTHROPIC_API_KEY" not in names
    assert "cle-secrete" not in layout.pages[0].stream_text


async def test_oversized_output_is_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_layout, "LAYOUT_MAX_OUTPUT_BYTES", 100)
    _fake_worker(monkeypatch, "import sys; sys.stdout.write('x' * 101)")
    spawned = _Spawned(monkeypatch)
    with pytest.raises(PdfUnreadable) as caught:
        await SubprocessPdfLayoutExtractor().extract_layout(b"%PDF-")
    assert caught.value.message == _UNREADABLE
    assert spawned.processes[0].returncode is not None


@pytest.mark.parametrize(
    "output",
    [
        "pas du json",
        "[]",
        json.dumps({"pages": [], "fonts": [], "selectable": False}),
        _payload(png="pas-du-base64!"),
        _payload(blocks=[["texte", 1, 2, 3]]),
        _payload(blocks=[["t", 1, 2, 3, 4, "F", 9, "#000000", "oui", False]]),
        json.dumps({"pages": [_EMPTY_PAGE] * 5, "fonts": [], "selectable": False}),
        json.dumps({"pages": [_EMPTY_PAGE], "fonts": [1], "selectable": False}),
    ],
)
def test_malformed_output_is_unreadable(output: str) -> None:
    with pytest.raises(PdfUnreadable) as caught:
        parse_layout(output.encode())
    assert caught.value.message == _UNREADABLE and caught.value.__cause__ is None


async def test_nonzero_exit_is_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_worker(monkeypatch, f"import sys; sys.stdout.write({_payload()!r}); sys.exit(1)")
    with pytest.raises(PdfUnreadable) as caught:
        await SubprocessPdfLayoutExtractor().extract_layout(b"%PDF-")
    assert caught.value.message == _UNREADABLE


async def test_spawn_failure_is_unreadable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = str(tmp_path / "secret-dir" / "python-absent")
    monkeypatch.setattr(pdf_layout, "worker_command", lambda *_args: [missing, "-c", ""])
    with pytest.raises(PdfUnreadable) as caught:
        await SubprocessPdfLayoutExtractor().extract_layout(b"%PDF-")
    assert caught.value.message == _UNREADABLE and caught.value.__cause__ is None
    assert "secret-dir" not in caplog.text


@pytest.mark.skipif(sys.platform == "win32", reason="RLIMIT_AS POSIX seulement")
async def test_worker_sets_memory_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    limit = 256 * 1024 * 1024
    code = (
        "from app.providers.pdf.worker import limit_memory; "
        f"limit_memory({limit}); bytearray(2 * 1024 ** 3)"
    )
    _fake_worker(monkeypatch, code)
    with pytest.raises(PdfUnreadable):
        await SubprocessPdfLayoutExtractor(max_memory_bytes=limit).extract_layout(b"%PDF-")


async def test_concurrency_is_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    code = (
        "import sys, time; sys.stdin.buffer.read(); time.sleep(0.3); "
        f"sys.stdout.write({_payload()!r})"
    )
    _fake_worker(monkeypatch, code)
    spawned = _Spawned(monkeypatch)
    extractor = SubprocessPdfLayoutExtractor(concurrency=1)
    await asyncio.gather(extractor.extract_layout(b"a"), extractor.extract_layout(b"b"))
    assert len(spawned.processes) == 2 and spawned.max_alive == 1


def test_worker_imports_neither_fastapi_nor_the_database() -> None:
    probe = (
        "import sys, app.providers.pdf.layout_worker; "
        "print(sorted(m for m in ('fastapi', 'sqlalchemy', 'app.db', 'app.core.errors') "
        "if m in sys.modules))"
    )
    done = subprocess.run(
        [sys.executable, "-c", probe], cwd=BACKEND_ROOT, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[]"


def test_worker_exit_codes() -> None:
    command = worker_command(PDF_MAX_MEMORY_BYTES)

    def run(data: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(command, input=data, cwd=BACKEND_ROOT, capture_output=True)

    ok, bad, long = run(make_cv_pdf()), run(b"pas un pdf"), run(make_cv_pdf(SampleCv(pages=5)))
    assert ok.returncode == layout_worker.EXIT_OK, ok.stderr
    assert json.loads(ok.stdout)["pages"][0]["width"] == 595
    assert bad.returncode == layout_worker.EXIT_UNREADABLE and bad.stdout == b""
    assert long.returncode == layout_worker.EXIT_TOO_MANY_PAGES and long.stdout == b""
