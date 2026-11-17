"""Processus et fichiers du code utilisateur (phase 10, 10.A1) : repérer et tuer tout ce qui
tourne sous l'uid du code, puis effacer ce qu'il a laissé. Stdlib seule.

Le lanceur n'a que `CHOWN`, `SETUID`, `SETGID` et `KILL` : sans `DAC_OVERRIDE` ni `FOWNER`, il ne
peut ni entrer dans un dossier du code ni effacer ses fichiers d'un dossier collant (`/tmp`). Le
nettoyage se fait donc **sous l'uid du code** (processus fils), le lanceur ne retirant que le
dossier de travail devenu vide."""

import contextlib
import ctypes
import os
import signal
import stat
import sys
import time
from collections.abc import Iterable
from pathlib import Path

PROC = Path("/proc")
_SYSV = (("shm", "shmid", "shmctl"), ("sem", "semid", "semctl"), ("msg", "msqid", "msgctl"))


def user_processes(uid: int) -> list[tuple[int, int]]:
    """Processus vivants (zombies exclus) d'uid `uid` : (pid, mémoire résidente en octets)."""
    found: list[tuple[int, int]] = []
    for name in os.listdir(PROC):
        if not name.isdigit():
            continue
        try:
            text = (PROC / name / "status").read_text(errors="replace")
        except OSError:
            continue
        fields = {
            line.split(":", 1)[0]: line.split(":", 1)[1].split()
            for line in text.splitlines()
            if ":" in line
        }
        owners = fields.get("Uid", [])
        state = fields.get("State", ["?"])
        if uid in {int(x) for x in owners[:2]} and state[0] != "Z":
            rss = int(fields["VmRSS"][0]) * 1024 if fields.get("VmRSS") else 0
            found.append((int(name), rss))
    return found


def reap_children() -> None:
    """Récolte les zombies (le lanceur est le processus 1 : il hérite des orphelins)."""
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return


def kill_user_processes(uid: int, rounds: int = 100) -> bool:
    """Tue tout processus d'uid `uid` (SIGKILL) jusqu'à ce qu'il n'en reste aucun ; `True` si
    le balayage a réussi. Plusieurs tours : une bombe à processus peut en créer pendant le tour."""
    for _ in range(rounds):
        victims = user_processes(uid)
        if not victims:
            reap_children()
            return True
        for pid, _ in victims:
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGKILL)
        reap_children()
        time.sleep(0.01)
    return not user_processes(uid)


def user_rss(uid: int) -> int:
    """Mémoire résidente totale, en octets, des processus d'uid `uid`."""
    return sum(rss for _, rss in user_processes(uid))


def _drop_to(uid: int, gid: int) -> None:
    os.setgroups([])
    os.setgid(gid)
    os.setuid(uid)


def _wipe_dir(path: str, uid: int) -> None:
    """Vide `path` (sans le retirer) de tout ce qui appartient à `uid`, sans récursion : un
    arbre très profond ne doit pas faire échouer le nettoyage. Descripteurs de dossier, jamais
    de suivi de lien symbolique."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open(path, flags)
    stack: list[tuple[int, int | None, str, list[str]]] = [(root, None, "", os.listdir(root))]
    while stack:
        fd, parent, name, pending = stack[-1]
        if not pending:
            stack.pop()
            os.close(fd)
            if parent is not None:
                os.rmdir(name, dir_fd=parent)
            continue
        entry = pending.pop()
        try:
            info = os.stat(entry, dir_fd=fd, follow_symlinks=False)
            if info.st_uid != uid:
                continue
            if stat.S_ISDIR(info.st_mode):
                os.chmod(entry, 0o700, dir_fd=fd)  # un dossier en 000 ne s'ouvrirait pas
                child = os.open(entry, flags, dir_fd=fd)
                stack.append((child, fd, entry, os.listdir(child)))
            else:
                os.unlink(entry, dir_fd=fd)
        except OSError:
            continue


def _remove_sysv_ipc(uid: int) -> None:
    """Retire les objets IPC System V créés par `uid` (ils survivent à leur processus)."""
    libc = ctypes.CDLL(None, use_errno=True)
    for table, id_column, func in _SYSV:
        try:
            lines = Path(f"/proc/sysvipc/{table}").read_text().splitlines()
        except OSError:
            continue
        header = lines[0].split()
        for line in lines[1:]:
            cols = line.split()
            if int(cols[header.index("uid")]) != uid:
                continue
            ident = int(cols[header.index(id_column)])
            getattr(libc, func)(ident, 0, 0 if table == "sem" else None)


def purge_user_files(uid: int, gid: int, roots: Iterable[str]) -> bool:
    """Efface, sous l'identité `uid`, tout ce que le code a laissé dans `roots`, plus ses objets
    IPC. `True` si le fils a fini sans erreur. Le fils ne rend jamais la main à l'appelant."""
    pid = os.fork()
    if pid == 0:
        code = 0
        try:
            _drop_to(uid, gid)
            for root in roots:
                try:
                    _wipe_dir(root, uid)
                except OSError:
                    code = 1
            _remove_sysv_ipc(uid)
        except BaseException:
            code = 2
        finally:
            sys.stdout.flush()
            os._exit(code)
    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status) == 0
