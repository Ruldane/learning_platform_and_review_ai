# ruff: noqa: E501
"""Les programmes « hostiles » des tests d'évasion : chacun est soumis tel quel comme code
utilisateur au vrai conteneur `sandbox`, et imprime une ligne JSON que le test relit."""

IDENTITY = """
import json, os
status = dict(l.split(":\\t", 1) for l in open("/proc/self/status").read().splitlines() if ":" in l)
tries = {}
for name, call in {"setuid0": lambda: os.setuid(0), "setgid12345": lambda: os.setgid(12345),
                   "chroot": lambda: os.chroot("/")}.items():
    try:
        call(); tries[name] = "ok"
    except OSError as exc:
        tries[name] = type(exc).__name__
print(json.dumps({"uid": [os.getuid(), os.geteuid()], "gid": [os.getgid(), os.getegid()],
  "groups": os.getgroups(), "cap": {k: status[k].strip() for k in
  ("CapInh", "CapPrm", "CapEff", "CapAmb")}, "tries": tries}))
"""

NETWORK = """
import json, socket
out = {}
def attempt(label, fn):
    try:
        fn(); out[label] = "ok"
    except OSError as exc:
        out[label] = type(exc).__name__ + ":" + str(exc.errno)
def tcp(host, port):
    s = socket.socket(); s.settimeout(2); s.connect((host, port)); s.close()
attempt("public_ip", lambda: tcp("1.1.1.1", 443))
attempt("public_ip2", lambda: tcp("8.8.8.8", 53))
attempt("host_docker_internal", lambda: tcp("host.docker.internal", 80))
attempt("dns", lambda: socket.getaddrinfo("example.org", 80))
attempt("dns_host", lambda: socket.getaddrinfo("host.docker.internal", 80))
attempt("udp", lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b"x", ("8.8.8.8", 53)))
for gateway in ("172.17.0.1", "172.18.0.1", "192.168.65.254", "192.168.65.2", "10.0.0.1"):
    attempt("gw_" + gateway, lambda g=gateway: tcp(g, 80))
routes = open("/proc/net/route").read().splitlines()[1:]
ifaces = sorted(l.split(":")[0].strip() for l in open("/proc/net/dev").read().splitlines()[2:])
print(json.dumps({"out": out, "default_routes": [r for r in routes if r.split()[1] == "00000000"],
                  "ifaces": ifaces}))
"""

SOCKETS = """
import json, os, stat
found = []
skip = {"/proc", "/sys", "/usr", "/lib", "/lib64", "/bin", "/sbin"}
for top, dirs, files in os.walk("/"):
    dirs[:] = [d for d in dirs if os.path.join(top, d) not in skip]
    for name in dirs + files:
        path = os.path.join(top, name)
        try:
            if stat.S_ISSOCK(os.lstat(path).st_mode):
                found.append(path)
        except OSError:
            pass
print(json.dumps({"sockets": found, "docker": [p for p in ("/var/run/docker.sock",
    "/run/docker.sock", "/docker.sock") if os.path.exists(p)]}))
"""

ENVIRONMENT = """
import json, os
print(json.dumps(dict(os.environ)))
"""

READ_ONLY_ROOT = """
import errno, json, os
bad = {}
for path in ["/x", "/etc/x", "/usr/x", "/usr/local/x", "/opt/x", "/opt/sandbox/x", "/var/x",
             "/root/x", "/home/x", "/run/x", "/bin/x", "/lib/x", "/sys/x", "/proc/x", "/mnt/x"]:
    try:
        open(path, "w").close(); os.remove(path); bad[path] = "WRITABLE"
    except OSError as exc:
        bad[path] = errno.errorcode.get(exc.errno, str(exc.errno))
for path in ["/opt/sandbox/runner.py", "/opt/sandbox/runner_exec.py", "/etc/passwd"]:
    try:
        open(path, "a").close(); bad[path] = "WRITABLE"
    except OSError as exc:
        bad[path] = errno.errorcode.get(exc.errno, str(exc.errno))
mounts = {l.split()[1]: l.split()[3].split(",") for l in open("/proc/mounts")}
print(json.dumps({"results": bad, "mounts": mounts}))
"""

WRITABLE_PLACES = """
import json, os
writable = []
def probe(directory):
    path = os.path.join(directory, ".probe")
    try:
        open(path, "w").close(); os.remove(path); return True
    except OSError:
        return False
skip = {"/proc", "/sys"}
for top, dirs, _ in os.walk("/"):
    dirs[:] = [d for d in dirs if os.path.join(top, d) not in skip and top.count("/") < 3]
    if probe(top):
        writable.append(top)
print(json.dumps({"writable": writable, "cwd": os.getcwd()}))
"""

NO_EXEC = """
import json, os, shutil, stat, subprocess, mmap
results = {}
for where in (os.getcwd(), "/tmp"):
    binary = os.path.join(where, "prog")
    shutil.copy("/bin/true", binary); os.chmod(binary, 0o755)
    script = os.path.join(where, "prog.sh")
    open(script, "w").write("#!/bin/sh\\necho pwned\\n"); os.chmod(script, 0o755)
    for label, path in (("binary", binary), ("script", script)):
        try:
            subprocess.run([path], check=False, capture_output=True)
            results[where + ":" + label] = "EXECUTED"
        except OSError as exc:
            results[where + ":" + label] = type(exc).__name__
    fd = os.open(binary, os.O_RDONLY)
    try:
        mmap.mmap(fd, 0, prot=mmap.PROT_READ | mmap.PROT_EXEC); results[where + ":mmap"] = "MAPPED"
    except (OSError, ValueError) as exc:
        results[where + ":mmap"] = type(exc).__name__
print(json.dumps(results))
"""

SPOOL_AND_PROC = """
import json, os
out = {"spool": [], "procs": {}}
for call in (lambda: os.listdir("/spool"), lambda: open("/spool/heartbeat").read(),
             lambda: os.listdir("/spool/jobs"), lambda: open("/spool/out/x", "w")):
    try:
        call(); out["spool"].append("ACCESSIBLE")
    except OSError as exc:
        out["spool"].append(type(exc).__name__)
me = os.getpid()
for pid in sorted(int(n) for n in os.listdir("/proc") if n.isdigit()):
    if pid == me:
        continue
    try:
        owner = os.stat(f"/proc/{pid}").st_uid
    except OSError:
        continue
    if owner == 20000:
        continue
    seen = []
    for what in ("environ", "mem", "maps", "cwd", "root", "exe", "fd", "mountinfo"):
        path = f"/proc/{pid}/{what}"
        try:
            if what in ("cwd", "root", "exe"):
                os.readlink(path)
            elif what == "fd":
                os.listdir(path)
            else:
                open(path, "rb").read(16)
            seen.append(what)
        except OSError:
            pass
    out["procs"][str(pid)] = seen
print(json.dumps(out))
"""

KILL_RUNNER = """
import json, os, signal
results = {}
for pid in sorted(int(n) for n in os.listdir("/proc") if n.isdigit()):
    if pid == os.getpid():
        continue
    for sig in (signal.SIGKILL, signal.SIGSTOP, signal.SIGTERM):
        try:
            os.kill(pid, sig); results[f"{pid}:{int(sig)}"] = "DELIVERED"
        except OSError as exc:
            results[f"{pid}:{int(sig)}"] = type(exc).__name__
try:
    os.kill(os.getppid(), signal.SIGKILL); results["parent"] = "DELIVERED"
except OSError as exc:
    results["parent"] = type(exc).__name__
print(json.dumps(results))
"""

PRIVILEGED_CALLS = """
import ctypes, json, os, platform
libc = ctypes.CDLL(None, use_errno=True)
out = {}
def call(label, fn):
    ctypes.set_errno(0)
    ret = fn()
    out[label] = [ret, ctypes.get_errno()]
call("mount", lambda: libc.mount(b"none", b"/tmp", b"tmpfs", 0, None))
call("umount", lambda: libc.umount(b"/tmp"))
call("unshare_user", lambda: libc.unshare(0x10000000))
call("unshare_mount", lambda: libc.unshare(0x00020000))
call("unshare_net", lambda: libc.unshare(0x40000000))
call("ptrace_init", lambda: libc.ptrace(16, 1, 0, 0))
call("ptrace_parent", lambda: libc.ptrace(16, os.getppid(), 0, 0))
call("chroot", lambda: libc.chroot(b"/tmp"))
call("sethostname", lambda: libc.sethostname(b"pwned", 5))
call("reboot", lambda: libc.reboot(0x1234567))
call("setns", lambda: libc.setns(os.open("/proc/1/ns/mnt", os.O_RDONLY) if os.access("/proc/1/ns/mnt", os.R_OK) else -1, 0))
if platform.machine() == "x86_64":
    call("add_key", lambda: libc.syscall(248, b"user", b"k", b"v", 1, -3))
    call("bpf", lambda: libc.syscall(321, 0, 0, 0))
    call("perf_event_open", lambda: libc.syscall(298, 0, 0, -1, -1, 0))
    call("kexec_load", lambda: libc.syscall(246, 0, 0, 0, 0))
try:
    os.mknod("/tmp/node", 0o600 | 0o020000, os.makedev(1, 3)); out["mknod"] = "CREATED"
except OSError as exc:
    out["mknod"] = type(exc).__name__
print(json.dumps(out))
"""

SECCOMP = """
import json
status = dict(l.split(":\\t", 1) for l in open("/proc/self/status").read().splitlines() if ":" in l)
print(json.dumps({k: status[k].strip() for k in ("Seccomp", "NoNewPrivs", "CapBnd")}))
"""
