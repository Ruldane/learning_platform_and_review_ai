"""Exécution d'un travail dans le bac (phase 10, 10.A1) : processus du code sous l'uid 20000,
surveillance (durée, mémoire, annulation, sortie) et résultat. Stdlib seule. Le travail et ses
plafonds sont dans `runner_job` (réexportés ici : `Limits`, `RunEnv`, `SandboxResult`...)."""

import contextlib
import errno
import os
import resource
import select
import shutil
import signal
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import runner_proc
from runner_job import (
    RUN_ID,
    Job,
    JobRefused,
    Limits,
    RunEnv,
    SandboxResult,
    Unsafe,
    build_command,
    build_env,
    job_from_json,
    materialize,
    validate_job,
)

__all__ = ["JobRefused", "Limits", "RunEnv", "SandboxResult", "Unsafe", "job_from_json", "run_job"]

WAIT_S = 5.0  # attente du processus principal après SIGKILL ; au-delà, le bac n'est plus sûr


def child_setup(limits: Limits, drop: bool, workdir: Path) -> Callable[[], None]:
    """Ce que le fils fait avant `exec` : limites, priorité, puis perte de toute identité du
    lanceur (`setgroups([])`, `setgid`, `setuid`). Rien n'est lu dans le travail."""

    def setup() -> None:
        pairs = [
            (resource.RLIMIT_CPU, (limits.cpu_s, limits.cpu_s + 1)),
            (resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes)),
            (resource.RLIMIT_NPROC, (limits.processes, limits.processes)),
            (resource.RLIMIT_FSIZE, (limits.file_bytes, limits.file_bytes)),
            (resource.RLIMIT_NOFILE, (limits.open_files, limits.open_files)),
            (resource.RLIMIT_CORE, (0, 0)),  # jamais de core : `core_pattern` est celui de l'hôte
            (resource.RLIMIT_MEMLOCK, (0, 0)),
            (resource.RLIMIT_MSGQUEUE, (0, 0)),
        ]
        for which, value in pairs:
            resource.setrlimit(which, value)
        try:  # le noyau tue ce code avant le lanceur en cas de manque de mémoire
            with open("/proc/self/oom_score_adj", "w") as handle:
                handle.write("1000")
        except OSError:
            pass
        os.nice(5)
        os.umask(0o022)
        if drop:
            os.setgroups([])
            os.setgid(limits.gid)
            os.setuid(limits.uid)
        os.chdir(workdir)

    return setup


def utf8_prefix(data: bytes) -> bytes:
    """Le plus long début de `data` qui ne coupe pas un caractère UTF-8 en deux."""
    for cut in range(len(data), max(len(data) - 4, -1), -1):
        try:
            data[:cut].decode("utf-8")
            return data[:cut]
        except UnicodeDecodeError as exc:
            if exc.reason != "unexpected end of data":
                return data
    return data


class LogSink:
    """Le journal de sortie `out/<id>.log` : 64 Kio au plus, le reste est jeté (`truncated`). Le
    lanceur le crée (vide) dès qu'il prend le travail (`Runner.claim`) : il est rouvert ici."""

    def __init__(self, path: Path, cap: int) -> None:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o660)
        os.fchmod(fd, 0o660)
        self._file = os.fdopen(fd, "wb", buffering=0)
        self._cap, self.size, self.truncated = cap, 0, False

    def write(self, chunk: bytes) -> None:
        room = self._cap - self.size
        if len(chunk) > room:
            self.truncated = True
            chunk = utf8_prefix(chunk[: max(room, 0)])
        if chunk:
            self._file.write(chunk)
            self.size += len(chunk)

    def close(self) -> None:
        self._file.close()


@dataclass
class Outcome:
    status: Literal["done", "timeout", "killed", "error"]
    exit_code: int | None


def _after_exit(code: int | None, forced: str | None) -> Outcome:
    if forced is not None:
        return Outcome(forced, None)  # type: ignore[arg-type]
    if code is not None and code < 0:
        sig = -code
        if sig == signal.SIGXCPU:
            return Outcome("timeout", None)
        if sig == signal.SIGKILL:  # tué par le noyau (manque de mémoire) ou par la limite de CPU
            return Outcome("killed", None)
        return Outcome("done", 128 + sig)
    return Outcome("done", code)


def stop_run(proc: subprocess.Popen[bytes], limits: Limits) -> None:
    """Fin de course : tout le groupe, puis tout processus resté sous l'uid du code."""
    with contextlib.suppress(OSError):
        os.killpg(proc.pid, signal.SIGKILL)
    runner_proc.kill_user_processes(limits.uid)


def _pump(fd: int, sink: LogSink, eof: bool) -> bool:
    """Lit ce qui est disponible (50 ms au plus d'attente) ; rend `True` à la fin du flux."""
    if eof:
        time.sleep(0.05)
        return True
    if not select.select([fd], [], [], 0.05)[0]:
        return False
    try:
        chunk = os.read(fd, 65_536)
    except BlockingIOError:
        return False
    except OSError as exc:
        if exc.errno == errno.EIO:
            return True
        raise
    if not chunk:
        return True
    sink.write(chunk)
    return False


def supervise(
    proc: subprocess.Popen[bytes], sink: LogSink, job: Job, limits: Limits, env: RunEnv
) -> Outcome:
    """Surveille jusqu'à la fin : sortie, durée réelle, annulation, mémoire de tous les
    processus du code. Un contrôle toutes les 50 ms ; aucun cas ne laisse la boucle sans fin."""
    assert proc.stdout is not None
    fd = proc.stdout.fileno()
    os.set_blocking(fd, False)
    deadline = time.monotonic() + job.wall_s
    cancel = env.spool / "cancel" / job.run_id
    forced: str | None = None
    forced_at = 0.0
    eof, exited_at, ticks, next_check = False, None, 0, 0.0
    while True:
        eof = _pump(fd, sink, eof)
        now = time.monotonic()
        if now < next_check:
            continue
        next_check, ticks = now + 0.05, ticks + 1
        env.tick()
        if proc.poll() is not None:
            exited_at = exited_at or now
            if eof or now - exited_at > 1.0:
                break
        elif forced is None:
            forced = _verdict(deadline, cancel, ticks, limits, env)
            if forced is not None:
                forced_at = now
                stop_run(proc, limits)
        elif now - forced_at > WAIT_S:  # SIGKILL envoyé et le processus principal ne meurt pas
            raise Unsafe("un processus du code ne meurt pas")
    stop_run(proc, limits)
    _drain(fd, sink)
    try:
        code = proc.wait(timeout=WAIT_S)
    except subprocess.TimeoutExpired:
        raise Unsafe("un processus du code ne meurt pas") from None
    return _after_exit(code, forced)


def _drain(fd: int, sink: LogSink) -> None:
    """Ce qui reste dans le tube une fois tout le monde arrêté."""
    while True:
        try:
            chunk = os.read(fd, 65_536)
        except OSError:
            return
        if not chunk:
            return
        sink.write(chunk)


def _verdict(deadline: float, cancel: Path, ticks: int, limits: Limits, env: RunEnv) -> str | None:
    if time.monotonic() >= deadline:
        return "timeout"
    if env.stop() or cancel.exists():
        return "killed"
    if ticks % 2 == 0 and runner_proc.user_rss(limits.uid) > limits.memory_bytes:
        return "killed"
    return None


def _spawn(job: Job, workdir: Path, limits: Limits, env: RunEnv) -> subprocess.Popen[bytes]:
    return subprocess.Popen(  # noqa: S603 (arguments construits ici, jamais par le travail)
        build_command(job, env.python),
        env=build_env(workdir),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        start_new_session=True,
        preexec_fn=child_setup(limits, env.drop, workdir),
        bufsize=0,
    )


def run_job(job: dict[str, object], limits: Limits, env: RunEnv | None = None) -> SandboxResult:
    """Exécute un travail du début à la fin et rend son résultat. Le journal est écrit au fil
    de l'eau dans `out/<id>.log`. Ne lève jamais : un refus ou un incident devient `error`
    (message en français dans le journal). Après coup, plus aucun processus ni fichier du code."""
    env = env or RunEnv()
    started = time.monotonic()
    clean = False
    sink: LogSink | None = None
    workdir: Path | None = None
    try:
        run_id = job.get("run_id")
        if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            raise JobRefused("identifiant de travail refusé")
        sink = LogSink(env.spool / "out" / f"{run_id}.log", limits.output_bytes)
        valid = validate_job(job, limits)
        workdir = env.work / valid.run_id
        runner_proc.kill_user_processes(limits.uid)
        materialize(valid, workdir, limits, env)
        outcome = supervise(_spawn(valid, workdir, limits, env), sink, valid, limits, env)
    except Exception as exc:  # un incident ne fait jamais tomber le lanceur
        message = _describe(exc)
        outcome = Outcome("error", None)
        if sink is not None:
            sink.write(f"{message}\n".encode())
    finally:
        clean = _verified(lambda: runner_proc.kill_user_processes(limits.uid))
        clean = _cleanup(workdir, limits, env) and clean
        truncated = sink.truncated if sink else False
        if sink is not None:
            sink.close()
    if not clean:
        raise Unsafe("un reste du code n'a pas pu être retiré")
    return SandboxResult(
        outcome.status, outcome.exit_code, int((time.monotonic() - started) * 1000), truncated
    )


def _describe(exc: Exception) -> str:
    if isinstance(exc, JobRefused):
        return str(exc)
    return f"Le bac n'a pas pu lancer ce travail ({type(exc).__name__})."


def _verified(action: Callable[[], bool]) -> bool:
    """Le retour d'un nettoyage ; une exception (`fork` refusé, mémoire…) vaut « pas propre » : elle
    mène à `Unsafe`, jamais à un « travail illisible » après lequel le lanceur continuerait."""
    try:
        return action()
    except OSError:
        return False


def _cleanup(workdir: Path | None, limits: Limits, env: RunEnv) -> bool:
    """Efface ce que le code a laissé. Avec changement d'identité, sous l'uid du code (le lanceur
    ne peut pas entrer chez lui) ; le lanceur ne retire que le dossier devenu vide. Sans (tests
    unitaires), le dossier appartient à l'appelant : retrait direct. Rend `False` si le nettoyage
    a échoué (le lanceur ne sert alors plus de travail)."""
    clean = True
    if env.drop:
        roots = [str(env.work), *env.clean_roots]
        present = [r for r in roots if os.path.isdir(r)]
        clean = _verified(lambda: runner_proc.purge_user_files(limits.uid, limits.gid, present))
    elif workdir is not None:
        shutil.rmtree(workdir, ignore_errors=True)
    if workdir is not None and workdir.is_dir():
        try:
            os.rmdir(workdir)
        except OSError:
            clean = False
    return clean
