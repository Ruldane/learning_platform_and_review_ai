"""Sandbox implementation through an exchange volume (phase 10, P5 and P6): the back end drops
`<spool>/jobs/<run_id>.json`; the `sandbox` container's launcher (`sandbox/runner.py`, without
network or socket) runs it and returns `<spool>/out/<run_id>.log` (the output, 64 KiB at most) then
`<run_id>.done.json` (the end). Cancellation: a file `<spool>/cancel/<run_id>`. Heartbeat:
`<spool>/heartbeat` (its age says whether the sandbox runs).

Only the composition (`app.bootstrap_ide`) imports this module: the features only know the
`CodeSandbox` port (import contract 3). The exchange folder is `2770 root:12345`; the back end
accesses it through `group_add: ["12345"]`. If the sandbox is stopped, `submit` raises `OSError`."""

import asyncio
import json
import os
import secrets
import stat
import threading
import time
from pathlib import Path
from typing import Literal

from app.providers.sandbox.base import (
    MAX_INPUT_BYTES,
    MAX_INPUT_CHUNK_BYTES,
    MAX_OUTPUT_BYTES,
    SandboxJob,
    SandboxProgress,
    SandboxResult,
    UnknownRun,
    check_job_limits,
    check_run_id,
)

HEARTBEAT_MAX_AGE_S = 5.0
# The launcher bounds the log to `MAX_OUTPUT_BYTES`: the back end never reads more (plus four bytes
# for a cut character), even if the volume held a huge file.
MAX_READ_BYTES = MAX_OUTPUT_BYTES + 4
# Size of a submitted job: the launcher refuses more (200,000 bytes of control characters
# make 1.2 MB once escaped in JSON; same value as the launcher's `MAX_JOB_BYTES`).
MAX_JOB_BYTES = 1_500_000
# A job left in the queue longer while the launcher no longer beats: the sandbox is down.
QUEUE_DEAD_S = 60.0
_STATUSES: tuple[Literal["done", "timeout", "killed", "error"], ...] = (
    "done",
    "timeout",
    "killed",
    "error",
)


def _utf8_complete(data: bytes) -> bytes:
    """`data` without a UTF-8 character possibly cut at the end (read at the next call)."""
    for cut in range(len(data), max(len(data) - 4, -1), -1):
        try:
            data[:cut].decode("utf-8")
            return data[:cut]
        except UnicodeDecodeError as exc:
            if exc.reason != "unexpected end of data":
                return data
    return data


def _read_result(path: Path) -> SandboxResult | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        status = raw["status"]
        code = raw["exit_code"]
        return SandboxResult(
            status=status if status in _STATUSES else "error",
            exit_code=code if isinstance(code, int) and not isinstance(code, bool) else None,
            duration_ms=int(raw["duration_ms"]),
            truncated=bool(raw["truncated"]),
        )
    except FileNotFoundError:
        return None
    except (ValueError, KeyError, TypeError, OSError):
        return SandboxResult(status="error", exit_code=None, duration_ms=0, truncated=False)


class SpoolSandbox:
    """`CodeSandbox` through an exchange volume. The disk accesses are small files, done in
    a thread (`asyncio.to_thread`) so as never to block the event loop."""

    def __init__(self, spool_dir: Path) -> None:
        self._dir = Path(spool_dir)
        self._input_lock = threading.Lock()

    def _job(self, run_id: str) -> Path:
        return self._dir / "jobs" / f"{run_id}.json"

    def _log(self, run_id: str) -> Path:
        return self._dir / "out" / f"{run_id}.log"

    def _done(self, run_id: str) -> Path:
        return self._dir / "out" / f"{run_id}.done.json"

    async def submit(self, job: SandboxJob) -> None:
        check_job_limits(job)
        await asyncio.to_thread(self._write_job, job)

    def _write_job(self, job: SandboxJob) -> None:
        if self._log(job.run_id).exists():
            raise ValueError("job already submitted")
        body = {
            "run_id": job.run_id,
            "files": job.files,
            "entry": job.entry,
            "kind": job.kind,
            "timeout_s": job.timeout_s,
            "source": job.source,
            "model_user": job.model_user,
        }
        try:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError:  # an orphan surrogate is not text
            raise ValueError("invalid text in the files") from None
        if len(payload) > MAX_JOB_BYTES:
            raise ValueError("job too large")
        tmp = self._dir / "jobs" / f".{job.run_id}.{secrets.token_hex(4)}.tmp"  # per submission
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o660)
        try:
            os.fchmod(fd, 0o660)  # the back end's umask (022) would remove group write
            os.write(fd, payload)
        finally:
            os.close(fd)
        try:
            os.link(tmp, self._job(job.run_id))  # fails if present: no overwrite
        except FileExistsError:
            raise ValueError("job already submitted") from None
        finally:
            os.unlink(tmp)

    async def poll(self, run_id: str, offset: int) -> SandboxProgress:
        try:
            check_run_id(run_id)
        except ValueError:
            raise UnknownRun(run_id) from None
        return await asyncio.to_thread(self._poll, run_id, max(offset, 0))

    def _poll(self, run_id: str, offset: int, retry: bool = True) -> SandboxProgress:
        result = _read_result(self._done(run_id))  # before the log: end => complete log
        try:
            with open(self._log(run_id), "rb") as handle:
                handle.seek(offset)
                data = handle.read(MAX_READ_BYTES)
        except FileNotFoundError:
            data = None
        if data is None:
            if result is not None:
                return SandboxProgress(output="", next_offset=offset, result=result)
            return self._queued(run_id, offset, retry)
        if result is None:
            data = _utf8_complete(data)
        return SandboxProgress(
            output=data.decode("utf-8", errors="replace"),
            next_offset=offset + len(data),
            result=result,
        )

    def _queued(self, run_id: str, offset: int, retry: bool) -> SandboxProgress:
        try:
            age = time.time() - self._job(run_id).stat().st_mtime
        except FileNotFoundError:
            if retry:  # the launcher took the job between the two reads: its log exists
                return self._poll(run_id, offset, retry=False)
            raise UnknownRun(run_id) from None
        if age > QUEUE_DEAD_S and not self._beating():
            dead = SandboxResult(status="error", exit_code=None, duration_ms=0, truncated=False)
            return SandboxProgress(output="", next_offset=offset, result=dead)
        return SandboxProgress(output="", next_offset=offset, result=None)

    async def cancel(self, run_id: str) -> None:
        try:
            check_run_id(run_id)
        except ValueError:
            return
        await asyncio.to_thread(self._cancel, run_id)

    def _cancel(self, run_id: str) -> None:
        if self._done(run_id).exists():
            return
        if not (self._job(run_id).exists() or self._log(run_id).exists()):
            return
        marker = self._dir / "cancel" / run_id
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT, 0o660)
        os.fchmod(fd, 0o660)
        os.close(fd)

    async def write_input(self, run_id: str, data: bytes) -> None:
        check_run_id(run_id)
        if not 0 < len(data) <= MAX_INPUT_CHUNK_BYTES:
            raise ValueError("input too large")
        await asyncio.to_thread(self._append_input, run_id, data)

    def _append_input(self, run_id: str, data: bytes) -> None:
        with self._input_lock:
            if self._done(run_id).exists() or not (
                self._job(run_id).exists() or self._log(run_id).exists()
            ):
                raise UnknownRun(run_id)
            path = self._dir / "input" / f"{run_id}.in"
            flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
            fd = os.open(path, flags, 0o660)
            with os.fdopen(fd, "ab") as handle:
                current = os.fstat(fd)
                if (
                    not stat.S_ISREG(current.st_mode)
                    or current.st_size + len(data) > MAX_INPUT_BYTES
                ):
                    raise ValueError("input too large")
                os.fchmod(fd, 0o660)
                handle.write(data)

    def _beating(self) -> bool:
        try:
            age = time.time() - (self._dir / "heartbeat").stat().st_mtime
        except OSError:
            return False
        return age < HEARTBEAT_MAX_AGE_S

    async def healthy(self) -> bool:
        try:
            return await asyncio.to_thread(self._beating)
        except Exception:
            return False
