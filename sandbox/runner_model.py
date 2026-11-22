"""Relais borné entre le descripteur du code et le socket protégé de Tremplin."""

import contextlib
import json
import socket
import threading
from collections.abc import Iterator
from pathlib import Path

from runner_job import Job, Unsafe

MAX_REQUEST_BYTES = 16_384
MAX_REPLY_BYTES = 100_000
MAX_CALLS = 3
_DENIED = b'{"error":"gateway_unavailable"}\n'


class ModelRelay:
    def __init__(self, job: Job, spool: Path) -> None:
        self._path = spool / "ide-model.sock"
        self._job = job
        self._sockets = socket.socketpair() if job.model_user and self._path.is_socket() else None
        self._stopped = threading.Event()
        self._remote_lock = threading.Lock()
        self._remote: socket.socket | None = None

    def fds(self) -> tuple[int, ...]:
        return (self._sockets[1].fileno(),) if self._sockets is not None else ()

    def environment(self) -> dict[str, str]:
        fds = self.fds()
        return {"TREMPLIN_MODEL_FD": str(fds[0])} if fds else {}

    def _forward(self, raw: bytes) -> bytes:
        if not raw.endswith(b"\n") or len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("trame trop longue")
        try:
            json.loads(raw)
        except (ValueError, RecursionError):
            return b'{"error":"gateway_request_invalid"}\n'
        envelope = json.dumps({"user_id": self._job.model_user, "run_id": self._job.run_id})
        stream = envelope[:-1].encode() + b',"request":' + raw.rstrip(b"\r\n") + b"}\n"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as target:
            target.settimeout(9)
            with self._remote_lock:
                if self._stopped.is_set():
                    return _DENIED
                self._remote = target
            try:
                target.connect(str(self._path))
                target.sendall(stream)
                with target.makefile("rb") as source:
                    result = source.readline(MAX_REPLY_BYTES + 1)
            finally:
                with self._remote_lock:
                    self._remote = None
        return result if len(result) <= MAX_REPLY_BYTES and result.endswith(b"\n") else _DENIED

    def _serve(self, side: socket.socket) -> None:
        try:
            with side.makefile("rb") as source:
                for _ in range(MAX_CALLS):
                    raw = source.readline(MAX_REQUEST_BYTES + 1)
                    if not raw or self._stopped.is_set():
                        return
                    try:
                        reply = self._forward(raw)
                    except OSError:
                        reply = _DENIED
                    side.sendall(reply)
                if source.readline(MAX_REQUEST_BYTES + 1) and not self._stopped.is_set():
                    side.sendall(b'{"error":"gateway_run_limit"}\n')
        except (OSError, ValueError):
            pass
        finally:
            side.close()

    @contextlib.contextmanager
    def serve(self) -> Iterator[None]:
        if self._sockets is None:
            yield
            return
        side, child = self._sockets
        child.close()
        worker = threading.Thread(target=self._serve, args=(side,), daemon=True)
        worker.start()
        try:
            yield
        finally:
            self._stopped.set()
            with self._remote_lock:
                if self._remote is not None:
                    with contextlib.suppress(OSError):
                        self._remote.shutdown(socket.SHUT_RDWR)
            with contextlib.suppress(OSError):
                side.shutdown(socket.SHUT_RDWR)
            worker.join(timeout=1)
            if worker.is_alive():
                raise Unsafe("le canal modèle ne s’arrête pas")

    def close(self) -> None:
        if self._sockets is not None:
            for side in self._sockets:
                side.close()
