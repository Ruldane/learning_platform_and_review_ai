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


def parse_status(raw: bytes) -> tuple[set[int], str, int] | None:
    """`(uid réels et effectifs, état, mémoire résidente en octets)` d'un `/proc/<pid>/status`.
    Le nom du processus (`Name:`, première ligne) est fixé par le code (`prctl(PR_SET_NAME)`) :
    on ne coupe que sur le saut de ligne (le noyau l'échappe dans le nom), on ignore la première
    ligne et on garde la première occurrence de chaque clé après elle. `None` si l'uid reste
    illisible ; une mémoire illisible vaut 0. Jamais d'exception."""
    fields: dict[bytes, list[bytes]] = {}
    for line in raw.split(b"\n")[1:]:
        key, sep, value = line.partition(b":")
        if sep and key not in fields:
            fields[key] = value.split()
    try:
        uids = {int(x) for x in fields[b"Uid"][:2]}
    except (KeyError, ValueError):
        return None
    state = fields.get(b"State", [b"?"])[0].decode("ascii", "replace")
    try:
        rss = int(fields[b"VmRSS"][0]) * 1024
    except (KeyError, IndexError, ValueError):
        rss = 0
    return uids, state, rss


def user_processes(uid: int) -> list[tuple[int, int]]:
    """Processus vivants (zombies exclus) d'uid `uid` : (pid, mémoire résidente en octets)."""
    found: list[tuple[int, int]] = []
    for name in os.listdir(PROC):
        if not name.isdigit():
            continue
        try:
            raw = (PROC / name / "status").read_bytes()
        except OSError:
            continue
        parsed = parse_status(raw)
        if parsed is not None and uid in parsed[0] and parsed[1] != "Z":
            found.append((int(name), parsed[2]))
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


def _wipe_dir(path: str, uid: int) -> bool:
    """Vide `path` (sans le retirer) de tout ce qui appartient à `uid`, sans récursion : un
    arbre très profond ne doit pas faire échouer le nettoyage. Descripteurs de dossier, jamais
    de suivi de lien symbolique. `False` si une entrée à nous n'a pas pu partir. Le retrait d'un
    dossier directement sous la racine n'est pas tenté s'il est refusé (`/work` n'est pas
    inscriptible par le code : le lanceur retire ce dossier lui-même, une fois vide)."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open(path, flags)
    stack: list[tuple[int, int | None, str, list[str]]] = [(root, None, "", os.listdir(root))]
    clean = True
    while stack:
        fd, parent, name, pending = stack[-1]
        if not pending:
            stack.pop()
            os.close(fd)
            if parent is not None:
                try:
                    os.rmdir(name, dir_fd=parent)
                except OSError:
                    top = len(stack) == 1  # enfant direct de la racine
                    clean = clean and top
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
            clean = False
    return clean


def sysv_ids(table: str, uid: int, id_column: str) -> list[int]:
    """Les identifiants des objets System V d'un tableau de `/proc/sysvipc` que `uid` possède
    **ou a créé** : le propriétaire d'un objet peut le transférer (`IPC_SET`), le créateur
    (`cuid`) le retire quand même."""
    lines = table.splitlines()
    if not lines:
        return []
    header = lines[0].split()
    found: list[int] = []
    for line in lines[1:]:
        cols = line.split()
        if len(cols) < len(header):
            continue
        if uid in (int(cols[header.index("uid")]), int(cols[header.index("cuid")])):
            found.append(int(cols[header.index(id_column)]))
    return found


def _remove_sysv_ipc(uid: int) -> None:
    """Retire les objets IPC System V du code (ils survivent à leur processus)."""
    libc = ctypes.CDLL(None, use_errno=True)
    for table, id_column, func in _SYSV:
        try:
            text = Path(f"/proc/sysvipc/{table}").read_text()
        except OSError:
            continue
        for ident in sysv_ids(text, uid, id_column):
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
                    code = code if _wipe_dir(root, uid) else 1
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
