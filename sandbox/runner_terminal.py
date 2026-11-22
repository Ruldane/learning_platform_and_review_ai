"""Pseudo-terminal de la séance, supervisé par le lanceur normal du bac."""

import contextlib
import fcntl
import os
import pty
import signal
import stat
import subprocess
import termios
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from runner_job import Unsafe, build_env

MAX_INPUT_BYTES = 65_536
READ_BYTES = 4_096


@dataclass
class TerminalProcess:
    proc: subprocess.Popen[bytes]
    fd: int
    input_path: Path
    offset: int = 0

    def feed(self) -> None:
        if self.offset >= MAX_INPUT_BYTES:
            return
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            source = os.open(self.input_path, flags)
        except OSError:
            return
        try:
            if stat.S_ISREG(os.fstat(source).st_mode):
                chunk = os.pread(
                    source, min(READ_BYTES, MAX_INPUT_BYTES - self.offset), self.offset
                )
                if chunk:
                    self.offset += os.write(self.fd, chunk)
        except OSError:
            pass  # Le PTY est plein ou vient de fermer. Le superviseur contrôle sa fin.
        finally:
            os.close(source)


@contextlib.contextmanager
def open_terminal(
    workdir: Path,
    input_path: Path,
    lower_privileges: Callable[[], None],
    model_env: dict[str, str],
    model_fds: tuple[int, ...],
) -> Iterator[TerminalProcess]:
    master, slave = pty.openpty()

    def setup() -> None:
        os.setsid()
        fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
        lower_privileges()

    try:
        try:
            proc = subprocess.Popen(  # noqa: S603 (commande fixe, jamais reçue du travail)
                ["/bin/sh", "-i"],
                env={**build_env(workdir), "TERM": "dumb", **model_env},
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
                pass_fds=model_fds,
                preexec_fn=setup,
            )
        finally:
            os.close(slave)
        try:
            yield TerminalProcess(proc, master, input_path)
        finally:
            if proc.poll() is None:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(proc.pid, signal.SIGKILL)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    raise Unsafe("le terminal ne s’arrête pas") from None
    finally:
        os.close(master)
