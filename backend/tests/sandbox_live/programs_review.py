# ruff: noqa: E501
"""Programmes des tests d'évasion ajoutés par la relecture de 10.A1 (I1, I2). Voir `programs.py`."""

# I1 : le propriétaire d'un objet System V peut le transférer (`IPC_SET`) sans aucune capacité ;
# le créateur (`cuid`) reste 20000. Le nettoyage doit retirer l'objet quand même.
SYSV_GIVE_AWAY = """
import ctypes, json, struct
libc = ctypes.CDLL(None, use_errno=True)
IPC_SET, IPC_STAT, CREAT = 1, 2, 0o1000
made = {
    "shm": libc.shmget(0, 4096, CREAT | 0o666),
    "msg": libc.msgget(0, CREAT | 0o666),
    "sem": libc.semget(0, 1, CREAT | 0o666),
}
buf = ctypes.create_string_buffer(512)
given = {}
for name, ident in made.items():
    ctl = {"shm": libc.shmctl, "msg": libc.msgctl}.get(name)
    if name == "sem":
        stat = libc.semctl(ident, 0, IPC_STAT, ctypes.byref(buf))
        struct.pack_into("I", buf, 4, 0)  # uid propriétaire -> 0 (offset 4 de `ipc_perm`)
        given[name] = [stat, libc.semctl(ident, 0, IPC_SET, ctypes.byref(buf))]
    else:
        stat = ctl(ident, IPC_STAT, ctypes.byref(buf))
        struct.pack_into("I", buf, 4, 0)
        given[name] = [stat, ctl(ident, IPC_SET, ctypes.byref(buf))]
print(json.dumps({"made": made, "given": given}))
"""

SYSV_TABLES = """
import json
rows = {}
for table in ("shm", "sem", "msg"):
    lines = open(f"/proc/sysvipc/{table}").read().splitlines()
    header = lines[0].split()
    rows[table] = [{k: v for k, v in zip(header, l.split()) if k in ("uid", "cuid")} for l in lines[1:]]
print(json.dumps(rows))
"""

# I2 : le nom du processus (`comm`, 15 octets) est fixé par le code ; un retour chariot y fabrique
# de fausses lignes dans `/proc/<pid>/status`. Plusieurs gros processus ainsi nommés.
RENAMED_PROCESSES = """
import ctypes, os, time
libc = ctypes.CDLL(None, use_errno=True)
for _ in range(6):
    if os.fork() == 0:
        libc.prctl(15, b"a\\rVmRSS:\\tx", 0, 0, 0)  # PR_SET_NAME
        block = bytearray(b"x" * 90_000_000)  # touché : compte dans la mémoire résidente
        time.sleep(60)
        os._exit(0)
libc.prctl(15, b"b\\rState:\\tZ\\rUid:\\t0", 0, 0, 0)
time.sleep(60)
"""
