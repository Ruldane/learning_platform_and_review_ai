import asyncio
import subprocess
import sys
from typing import Any

import pytest

from app.providers.pdf import subprocess as pdf_subprocess
from app.providers.pdf import worker
from app.providers.pdf.base import (
    PDF_MAX_MEMORY_BYTES,
    PDF_TIMEOUT_MESSAGE,
    PDF_TIMEOUT_S,
    PdfUnreadable,
)
from app.providers.pdf.subprocess import BACKEND_ROOT, SubprocessPdfExtractor, worker_command
from scripts.sample_pdf import make_pdf

_DEFAULT_MESSAGE = "PDF illisible (protégé par mot de passe ou endommagé)."


class _Spawned:
    """Espion de `_spawn` : garde chaque processus lancé et le nombre maximal de vivants."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.processes: list[asyncio.subprocess.Process] = []
        self.max_alive = 0
        real = pdf_subprocess._spawn

        async def spy(command: list[str]) -> asyncio.subprocess.Process:
            process = await real(command)
            self.processes.append(process)
            alive = sum(p.returncode is None for p in self.processes)
            self.max_alive = max(self.max_alive, alive)
            return process

        monkeypatch.setattr(pdf_subprocess, "_spawn", spy)


def _fake_worker(monkeypatch: pytest.MonkeyPatch, code: str) -> None:
    monkeypatch.setattr(
        pdf_subprocess, "worker_command", lambda *_args: [sys.executable, "-c", code]
    )


async def test_subprocess_extracts_generated_pdf() -> None:
    text = await SubprocessPdfExtractor().extract_text(make_pdf(["Bonjour Tremplin"]))
    assert "Bonjour Tremplin" in text


async def test_subprocess_keeps_non_ascii_text() -> None:
    text = await SubprocessPdfExtractor().extract_text(make_pdf(["Déjà là, ça marche"]))
    assert "Déjà là, ça marche" in text


async def test_subprocess_garbage_is_unreadable() -> None:
    with pytest.raises(PdfUnreadable) as caught:
        await SubprocessPdfExtractor().extract_text(b"pas un pdf")
    assert caught.value.message == _DEFAULT_MESSAGE and caught.value.status_code == 422
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


async def test_subprocess_timeout_kills_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_worker(monkeypatch, "import time; time.sleep(30)")
    spawned = _Spawned(monkeypatch)
    extractor = SubprocessPdfExtractor(timeout_s=0.5)
    with pytest.raises(PdfUnreadable) as caught:
        await extractor.extract_text(b"%PDF-")
    assert caught.value.message == PDF_TIMEOUT_MESSAGE
    assert caught.value.__cause__ is None and caught.value.__suppress_context__
    assert len(spawned.processes) == 1 and spawned.processes[0].returncode is not None


async def test_cancelled_call_kills_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_worker(monkeypatch, "import time; time.sleep(30)")
    spawned = _Spawned(monkeypatch)
    task = asyncio.create_task(SubprocessPdfExtractor().extract_text(b"%PDF-"))
    while not spawned.processes:
        await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert spawned.processes[0].returncode is not None


async def test_subprocess_limits_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_worker(monkeypatch, "import sys, time; sys.stdin.buffer.read(); time.sleep(0.3)")
    spawned = _Spawned(monkeypatch)
    extractor = SubprocessPdfExtractor(concurrency=1)
    await asyncio.gather(extractor.extract_text(b"a"), extractor.extract_text(b"b"))
    assert len(spawned.processes) == 2 and spawned.max_alive == 1


async def test_nonzero_exit_is_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_worker(monkeypatch, "import sys; sys.stdout.write('texte'); sys.exit(1)")
    with pytest.raises(PdfUnreadable) as caught:
        await SubprocessPdfExtractor().extract_text(b"%PDF-")
    assert caught.value.message == _DEFAULT_MESSAGE


async def test_spawn_failure_is_unreadable_without_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """Lancement impossible (interpréteur absent, EAGAIN, ENOMEM) : page illisible, pas une
    erreur interne ; ni le chemin ni l'exception d'origine dans le message (revue phase 3, m6)."""
    missing = str(tmp_path / "secret-dir" / "python-absent")
    monkeypatch.setattr(pdf_subprocess, "worker_command", lambda *_args: [missing, "-c", ""])
    with pytest.raises(PdfUnreadable) as caught:
        await SubprocessPdfExtractor().extract_text(b"%PDF-")
    assert caught.value.message == _DEFAULT_MESSAGE
    assert caught.value.__cause__ is None and caught.value.__suppress_context__
    assert "secret-dir" not in caught.value.message
    assert "secret-dir" not in caplog.text


async def test_oversized_output_is_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.pdf.base.MAX_TEXT_CHARS", 10)
    _fake_worker(monkeypatch, "import sys; sys.stdout.write('x' * 41)")
    spawned = _Spawned(monkeypatch)
    with pytest.raises(PdfUnreadable):
        await SubprocessPdfExtractor().extract_text(b"%PDF-")
    assert spawned.processes[0].returncode is not None


@pytest.mark.skipif(sys.platform == "win32", reason="RLIMIT_AS POSIX seulement")
async def test_worker_sets_memory_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    limit = 256 * 1024 * 1024
    code = (
        "from app.providers.pdf.worker import limit_memory; "
        f"limit_memory({limit}); bytearray(2 * 1024 ** 3)"
    )
    _fake_worker(monkeypatch, code)
    with pytest.raises(PdfUnreadable):
        await SubprocessPdfExtractor(max_memory_bytes=limit).extract_text(b"%PDF-")


def test_limit_memory_is_skipped_off_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "resource", calls)  # toute utilisation lèverait
    worker.limit_memory(1024)
    assert calls == []


def test_defaults_and_worker_command() -> None:
    assert PDF_TIMEOUT_S == 60.0 and PDF_MAX_MEMORY_BYTES == 1024 * 1024 * 1024
    command = worker_command(500, 2_000_000, PDF_MAX_MEMORY_BYTES)
    assert command == [
        sys.executable,
        "-m",
        "app.providers.pdf.worker",
        "500",
        "2000000",
        str(PDF_MAX_MEMORY_BYTES),
    ]
    assert (BACKEND_ROOT / "app" / "providers" / "pdf" / "worker.py").is_file()


def test_worker_imports_neither_fastapi_nor_the_database() -> None:
    probe = (
        "import sys, app.providers.pdf.worker; "
        "print(sorted(m for m in ('fastapi', 'sqlalchemy', 'app.db', 'app.core.errors') "
        "if m in sys.modules))"
    )
    done = subprocess.run(
        [sys.executable, "-c", probe], cwd=BACKEND_ROOT, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[]"


def test_worker_exit_codes() -> None:
    command = worker_command(500, 2_000_000, PDF_MAX_MEMORY_BYTES)
    ok = subprocess.run(command, input=make_pdf(["Bonjour"]), cwd=BACKEND_ROOT, capture_output=True)
    bad = subprocess.run(command, input=b"pas un pdf", cwd=BACKEND_ROOT, capture_output=True)
    assert ok.returncode == 0 and b"Bonjour" in ok.stdout, ok.stderr
    assert bad.returncode == worker.EXIT_UNREADABLE and bad.stdout == b"", bad.stderr
