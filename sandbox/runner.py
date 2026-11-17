"""Lanceur du bac à sable (phase 10, 10.A1) : tourne en uid 0 **sans autre capacité** que
`CHOWN`, `SETUID`, `SETGID` et `KILL`, gid 12345, dans un conteneur sans réseau ni socket. Il prend
les travaux déposés par le back dans `/spool/jobs/<id>.json`, les exécute un à un (une exécution à
la fois), écrit `/spool/out/<id>.log` puis `/spool/out/<id>.done.json`, et bat le coeur dans
`/spool/heartbeat` (le contrôle de santé de Compose en lit l'âge). Stdlib seule."""

import contextlib
import json
import os
import signal
import sys
import time
from pathlib import Path

import runner_exec
import runner_job
import runner_proc
from runner_job import JobRefused, Limits, RunEnv, SandboxResult

MAX_JOB_BYTES = 1_000_000
RETENTION_S = 1800
TMP_RETENTION_S = 60
POLL_S = 0.1
BEAT_EVERY_S = 1.0
PURGE_EVERY_S = 60.0
SPOOL_GID = 12345
SUBDIRS = ("jobs", "out", "cancel")


class Runner:
    def __init__(self, env: RunEnv, limits: Limits | None = None) -> None:
        self.limits = limits or Limits()
        self.spool, self.work = env.spool, env.work
        self._last_beat = 0.0
        self.stopping = False
        self.env = RunEnv(
            spool=env.spool,
            work=env.work,
            python=env.python,
            drop=env.drop,
            clean_roots=env.clean_roots,
            tick=self.beat,
            stop=lambda: self.stopping,
        )

    def beat(self) -> None:
        """Le battement de coeur, au plus une fois par seconde (seul son âge compte)."""
        now = time.monotonic()
        if now - self._last_beat < BEAT_EVERY_S:
            return
        self._last_beat = now
        fd = os.open(self.spool / "heartbeat", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o660)
        try:
            os.fchmod(fd, 0o660)
            os.write(fd, str(time.time()).encode())
        finally:
            os.close(fd)

    def prepare(self) -> None:
        """Droits du volume d'échange (le copy-up de Docker ne suffit pas à s'y fier), dossiers,
        travaux orphelins d'un lanceur arrêté en route, restes dans `/work`."""
        os.umask(0o007)
        self.spool.mkdir(parents=True, exist_ok=True)
        if self.env.drop:
            os.chown(self.spool, 0, SPOOL_GID)
        os.chmod(self.spool, 0o2770)
        for name in SUBDIRS:
            sub = self.spool / name
            sub.mkdir(exist_ok=True)
            if self.env.drop:
                os.chown(sub, 0, SPOOL_GID)
            os.chmod(sub, 0o2770)
        if self.env.drop:
            os.chmod(self.work, 0o755)  # le code n'écrit que dans son propre dossier
        runner_proc.kill_user_processes(self.limits.uid)
        self.fail_orphans()
        self.clean_work()

    def clean_work(self) -> None:
        if self.env.drop:
            runner_proc.purge_user_files(self.limits.uid, self.limits.gid, [str(self.work)])
        for child in self.work.iterdir() if self.work.is_dir() else []:
            if child.is_dir():
                with contextlib.suppress(OSError):
                    os.rmdir(child)

    def fail_orphans(self) -> None:
        """Un journal sans fin (lanceur redémarré en pleine exécution) reçoit une fin `error`."""
        for log in (self.spool / "out").glob("*.log"):
            if not log.with_suffix(".done.json").exists():
                self.write_done(log.stem, SandboxResult("error", None, 0, False))

    def write_done(self, run_id: str, result: SandboxResult) -> None:
        """`<id>.done.json`, écrit en dernier et d'un coup (fichier temporaire puis `rename`)."""
        out = self.spool / "out"
        final = out / f"{run_id}.done.json"
        tmp = out / f".{run_id}.done.tmp"
        payload = {
            "status": result.status,
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
            "truncated": result.truncated,
        }
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o660)
        with os.fdopen(fd, "w") as handle:
            os.fchmod(handle.fileno(), 0o660)
            json.dump(payload, handle)
        os.replace(tmp, final)

    def next_job(self) -> Path | None:
        names = []
        for path in (self.spool / "jobs").iterdir():
            if path.suffix == ".json" and runner_job.RUN_ID.fullmatch(path.stem):
                names.append((path.stat().st_mtime, path))
            elif not path.name.startswith("."):  # un nom qu'on ne sert pas : jeté
                _unlink(path)
        return min(names)[1] if names else None

    def read_job(self, path: Path) -> bytes:
        """Lit puis retire le fichier du travail (même s'il est illisible) ; jamais de lien."""
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as handle:
                data = handle.read(MAX_JOB_BYTES + 1)
        finally:
            _unlink(path)
        if len(data) > MAX_JOB_BYTES:
            raise JobRefused("travail trop gros")
        return data

    def process(self, path: Path) -> None:
        run_id = path.name.removesuffix(".json")
        cancel = self.spool / "cancel" / run_id
        try:
            job = runner_exec.job_from_json(self.read_job(path))
            if job.get("run_id") != run_id:
                raise JobRefused("identifiant de travail incohérent")
            if cancel.exists():
                result = self.refuse(run_id, "Annulé avant le départ.", "killed")
            else:
                result = runner_exec.run_job(job, self.limits, self.env)
        except (JobRefused, OSError) as exc:
            result = self.refuse(
                run_id, str(exc) if isinstance(exc, JobRefused) else "travail illisible"
            )
        _unlink(cancel)
        self.write_done(run_id, result)

    def refuse(self, run_id: str, message: str, status: str = "error") -> SandboxResult:
        log = self.spool / "out" / f"{run_id}.log"
        if not log.exists():
            fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o660)
            os.fchmod(fd, 0o660)
            os.write(fd, f"{message}\n".encode())
            os.close(fd)
        return SandboxResult(status, None, 0, False)  # type: ignore[arg-type]

    def purge_stale(self, now: float | None = None) -> None:
        purge_stale(self.spool, time.time() if now is None else now)

    def serve(self) -> None:
        last_purge = 0.0
        while not self.stopping:
            self.beat()
            if time.monotonic() - last_purge > PURGE_EVERY_S:
                last_purge = time.monotonic()
                self.purge_stale()
            path = self.next_job()
            if path is None:
                time.sleep(POLL_S)
            else:
                self.process(path)


def _unlink(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.unlink()


def purge_stale(spool: Path, now: float) -> int:
    """Retire du volume d'échange ce qui est plus vieux que la conservation (30 min ; 1 min pour
    les fichiers temporaires), travail par travail : le journal et sa fin partent ensemble.
    Rend le nombre de fichiers retirés."""
    groups: dict[tuple[str, str], list[Path]] = {}
    for sub in SUBDIRS:
        for path in (spool / sub).iterdir():
            if path.is_file():
                groups.setdefault((sub, path.name.lstrip(".").split(".")[0]), []).append(path)
    removed = 0
    for paths in groups.values():
        try:
            age = now - max(p.stat().st_mtime for p in paths)
        except OSError:
            continue
        limit = TMP_RETENTION_S if all(p.name.startswith(".") for p in paths) else RETENTION_S
        if age > limit:
            for path in paths:
                _unlink(path)
            removed += len(paths)
    return removed


def main() -> int:
    runner = Runner(RunEnv())
    signal.signal(signal.SIGTERM, lambda *_: setattr(runner, "stopping", True))
    signal.signal(signal.SIGINT, lambda *_: setattr(runner, "stopping", True))
    runner.prepare()
    runner.serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
