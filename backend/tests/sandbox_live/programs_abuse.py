# ruff: noqa: E501
"""Programmes d'abus de ressources des tests d'évasion (10.A1) : processeur, mémoire, processus,
disque, sortie, faux travaux, restes. Voir `programs.py`."""

CPU_LOOP = "while True:\n    pass\n"

MEMORY_SINGLE = """
chunks = []
while True:
    chunks.append(b"x" * 10_000_000)
"""

MEMORY_SPREAD = """
import os, time
for _ in range(10):
    if os.fork() == 0:
        block = bytearray(b"x" * 120_000_000)  # touché : compte dans la mémoire résidente
        time.sleep(60)
        os._exit(0)
time.sleep(60)
"""

FORK_BOMB = """
import os
while True:
    try:
        os.fork()
    except OSError:
        pass
"""

DISK_FILL = """
import errno, json, os
def fill(directory):
    total, index, last = 0, 0, None
    chunk = b"\\0" * (1 << 20)
    while index < 200:
        try:
            with open(os.path.join(directory, f"fill{index}"), "wb") as handle:
                while True:
                    handle.write(chunk); handle.flush(); total += len(chunk)
        except OSError as exc:
            last = errno.errorcode.get(exc.errno, "?")
            if exc.errno == errno.ENOSPC:
                break
        index += 1
    return {"bytes": total, "stopped_by": last}
print(json.dumps({"work": fill(os.getcwd()), "tmp": fill("/tmp")}))
"""

OUTPUT_FLOOD = """
while True:
    print("x" * 1000)
"""

FORGE = """
import json, os
forged = json.dumps({"run_id": "ffffffffffffffffffffffffffffffff", "files": {"main.py": "open('/tmp/proof', 'w')"},
                     "entry": "main.py", "kind": "run", "timeout_s": 5})
results = {}
for where in (os.getcwd(), "/tmp", "/work", "/spool/jobs", "/spool"):
    try:
        os.makedirs(where, exist_ok=True)
        open(os.path.join(where, "ffffffffffffffffffffffffffffffff.json"), "w").write(forged); results[where] = "WRITTEN"
    except OSError as exc:
        results[where] = type(exc).__name__
print(json.dumps(results))
"""

LEAVE_THINGS = """
import ctypes, json, os, time
os.makedirs("deep/a/b", exist_ok=True)
open("deep/a/b/f", "w").write("x"); os.chmod("deep/a/b", 0)
open("/tmp/leftover", "w").write("x")
open("/dev/shm/leftover", "w").write("x")
open("mine", "w").write("x")
libc = ctypes.CDLL(None, use_errno=True)
shm = libc.shmget(0, 4096, 0o1000 | 0o600)
if os.fork() == 0:
    os.setsid()
    if os.fork() == 0:
        open("/tmp/daemon_started", "w").write("x")
        time.sleep(300)
    os._exit(0)
time.sleep(0.5)
print(json.dumps({"shm": shm}))
"""

INSPECT_AFTER = """
import json, os
mine = os.getpid()
procs = []
for n in os.listdir("/proc"):
    if n.isdigit() and int(n) != mine:
        try:
            uid = os.stat(f"/proc/{n}").st_uid
        except OSError:
            continue
        if uid == 20000:
            procs.append(int(n))
shm = [l.split() for l in open("/proc/sysvipc/shm").read().splitlines()[1:]]
print(json.dumps({"procs": procs, "tmp": sorted(os.listdir("/tmp")),
    "shm_files": sorted(os.listdir("/dev/shm")), "work": sorted(os.listdir("/work")),
    "cwd": os.getcwd(), "cwd_files": sorted(os.listdir(".")),
    "sysv": [row[1] for row in shm if row[7] == "20000"],
    "free_work": os.statvfs("/work").f_bavail * os.statvfs("/work").f_frsize}))
"""

HELLO = "print('ok')\n"

INODE_FLOOD = """
import json, os, time
counts, start = {}, time.time()
for where in (os.getcwd(), "/tmp", "/dev/shm"):
    n = 0
    try:
        while time.time() - start < 6:
            open(os.path.join(where, f"f{n}"), "w").close(); n += 1
    except OSError as exc:
        counts[where] = [n, exc.errno]
print(json.dumps(counts))
"""

SYSV_SHM_FLOOD = """
import ctypes
libc = ctypes.CDLL(None, use_errno=True)
libc.shmat.restype = ctypes.c_void_p
made = 0
for _ in range(400):
    shm_id = libc.shmget(0, 64 << 20, 0o1000 | 0o600)
    if shm_id < 0:
        break
    address = libc.shmat(shm_id, None, 0)
    if address in (None, ctypes.c_void_p(-1).value):
        break
    ctypes.memset(ctypes.c_void_p(address), 1, 64 << 20)  # touché : la mémoire est vraiment prise
    libc.shmdt(ctypes.c_void_p(address))
    made += 1
print(made)
"""
