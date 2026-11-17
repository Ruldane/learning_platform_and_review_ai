"""Tests d'évasion (10.A1) : chaque propriété d'isolation du bac a son test, qui soumet un petit
programme hostile COMME CODE UTILISATEUR au vrai conteneur. Un échec = la tâche n'est pas finie."""

import asyncio
import stat
import time
import uuid

import pytest

from app.providers.sandbox.base import SandboxJob, UnknownRun
from tests.sandbox_live import programs as P
from tests.sandbox_live import programs_abuse as A
from tests.sandbox_live.conftest import Bac

pytestmark = pytest.mark.sandbox_live
MIB = 1 << 20
FORGED = "f" * 32


async def test_runs_as_uid_20000_without_capabilities(bac: Bac) -> None:
    data = (await bac.run(P.IDENTITY)).json()
    assert data["uid"] == [20000, 20000] and data["gid"] == [20000, 20000]
    assert data["groups"] == []  # pas même le groupe 12345 du volume d'échange
    zero = "0000000000000000"
    assert [data["cap"][k] for k in ("CapEff", "CapPrm", "CapAmb", "CapInh")] == [zero] * 4
    assert data["tries"] == {
        "setuid0": "PermissionError",
        "setgid12345": "PermissionError",
        "chroot": "PermissionError",
    }


async def test_no_network_at_all(bac: Bac) -> None:
    data = (await bac.run(P.NETWORK)).json()
    assert not any(v == "ok" for v in data["out"].values()), data["out"]
    assert len(data["out"]) == 11  # publique, hôte, DNS, UDP, cinq passerelles possibles
    assert data["default_routes"] == []  # ni passerelle ni route par défaut
    assert data["ifaces"] == ["lo"]  # que la boucle locale


async def test_no_docker_socket(bac: Bac) -> None:
    data = (await bac.run(P.SOCKETS)).json()
    assert data["docker"] == [] and data["sockets"] == []


async def test_environment_has_no_secrets(bac: Bac) -> None:
    env = (await bac.run(P.ENVIRONMENT)).json()
    allowed = {"PATH", "HOME", "PYTHONDONTWRITEBYTECODE", "LC_CTYPE"}
    assert {"PATH", "HOME", "PYTHONDONTWRITEBYTECODE"} <= set(env) <= allowed, set(env)
    blob = " ".join(env).upper()
    assert not any(word in blob for word in ("KEY", "TOKEN", "SECRET", "PASSWORD", "GPG"))
    assert env["HOME"].startswith("/work/") and len(env["HOME"]) == 6 + 32


async def test_rootfs_read_only(bac: Bac) -> None:
    data = (await bac.run(P.READ_ONLY_ROOT)).json()
    assert "WRITABLE" not in data["results"].values(), data["results"]
    assert "ro" in data["mounts"]["/"]


async def test_write_only_in_work_and_tmp(bac: Bac) -> None:
    data = (await bac.run(P.WRITABLE_PLACES)).json()
    # `/dev/shm` : le tmpfs de mémoire partagée que Docker monte toujours ; vidé après chaque
    # exécution (voir `test_leftovers_cleaned_after_run`).
    own = data["cwd"]
    extra = [d for d in data["writable"] if d not in {own, "/tmp", "/dev/shm"}]
    assert extra == [] and {own, "/tmp"} <= set(data["writable"]), data["writable"]
    mounts = (await bac.run(P.READ_ONLY_ROOT)).json()["mounts"]
    for place in ("/work", "/tmp"):
        assert {"noexec", "nosuid", "nodev"} <= set(mounts[place]), (place, mounts[place])


async def test_no_exec_from_work(bac: Bac) -> None:
    data = (await bac.run(P.NO_EXEC)).json()
    assert "EXECUTED" not in data.values() and "MAPPED" not in data.values(), data
    assert len(data) == 6


async def test_cannot_read_spool_or_runner_proc(bac: Bac) -> None:
    data = (await bac.run(P.SPOOL_AND_PROC)).json()
    assert data["spool"] == ["PermissionError"] * 4
    assert data["procs"], "le lanceur doit être visible dans /proc (sinon le test ne prouve rien)"
    for pid, seen in data["procs"].items():
        assert seen == [] or seen == ["mountinfo"], (pid, seen)  # `mountinfo` : public, sans secret


async def test_cannot_kill_runner(bac: Bac) -> None:
    data = (await bac.run(P.KILL_RUNNER)).json()
    assert "DELIVERED" not in data.values(), data
    assert await bac.sandbox.healthy()
    await bac.hello()  # le lanceur répond encore


async def test_cannot_mount_ptrace_or_unshare(bac: Bac) -> None:
    data = (await bac.run(P.PRIVILEGED_CALLS)).json()
    assert data.pop("mknod") == "PermissionError"
    for label, (ret, errno) in data.items():
        assert ret == -1 and errno in {1, 9, 13, 38}, (
            label,
            ret,
            errno,
        )  # EPERM EBADF EACCES ENOSYS
    for label in ("mount", "unshare_user", "unshare_mount", "unshare_net", "ptrace_init", "chroot"):
        assert data[label][1] in {1, 13}, (label, data[label])


async def test_seccomp_is_active(bac: Bac) -> None:
    data = (await bac.run(P.SECCOMP)).json()
    assert data["Seccomp"] == "2"  # mode filtre : le profil par défaut de Docker
    assert data["NoNewPrivs"] == "1"
    calls = (await bac.run(P.PRIVILEGED_CALLS)).json()
    for name in ("add_key", "bpf", "kexec_load"):
        if name in calls:
            assert calls[name][1] in {1, 13, 38}, (name, calls[name])


async def test_cpu_loop_times_out(bac: Bac) -> None:
    started = time.monotonic()
    run = await bac.run(A.CPU_LOOP, timeout_s=3)
    assert run.result.status == "timeout"
    assert 2.5 < time.monotonic() - started < 10
    await bac.hello()


async def test_memory_bomb_killed(bac: Bac) -> None:
    single = await bac.run(A.MEMORY_SINGLE)
    assert single.result.status == "killed" or (
        single.result.status == "done" and "MemoryError" in single.output
    ), (single.result, single.output[-200:])
    spread = await bac.run(A.MEMORY_SPREAD, timeout_s=15)
    assert spread.result.status == "killed", spread.result  # 10 x 120 Mo : plus que 256 Mio
    await bac.hello()


async def test_fork_bomb_contained(bac: Bac) -> None:
    bomb = uuid.uuid4().hex
    await bac.sandbox.submit(SandboxJob(bomb, {"main.py": A.FORK_BOMB}, "main.py", "run", 5))
    await asyncio.sleep(2.5)
    assert await bac.sandbox.healthy()  # le lanceur bat encore en pleine bombe
    for _ in range(100):
        progress = await bac.sandbox.poll(bomb, 0)
        if progress.result is not None:
            break
        await asyncio.sleep(0.2)
    assert progress.result is not None
    assert progress.result.status in {"timeout", "killed", "done"}
    after = (await bac.run(A.INSPECT_AFTER)).json()
    assert after["procs"] == []  # plus aucun reste de la bombe
    await bac.hello()


async def test_disk_fill_limited(bac: Bac) -> None:
    data = (await bac.run(A.DISK_FILL, timeout_s=15)).json()
    assert 8 * MIB <= data["work"]["bytes"] <= 64 * MIB, data
    assert 8 * MIB <= data["tmp"]["bytes"] <= 16 * MIB, data
    assert data["work"]["stopped_by"] == "ENOSPC" and data["tmp"]["stopped_by"] == "ENOSPC"
    after = (await bac.run(A.INSPECT_AFTER)).json()
    assert after["free_work"] > 60 * MIB  # l'espace est rendu
    await bac.hello()


async def test_inode_flood_limited_and_the_runner_survives(bac: Bac) -> None:
    # Sans `nr_inodes`, des millions de fichiers vides remplissaient la mémoire du noyau et le
    # noyau tuait tout le conteneur, lanceur compris (constaté à la première version de D201).
    data = (await bac.run(A.INODE_FLOOD, timeout_s=12)).json()
    assert len(data) == 3, data  # les trois dossiers inscriptibles s arrêtent sur ENOSPC
    assert all(count <= 5000 and errno == 28 for count, errno in data.values()), data
    assert await bac.sandbox.healthy()
    await bac.hello()


async def test_shared_memory_flood_is_killed_and_freed(bac: Bac) -> None:
    run = await bac.run(A.SYSV_SHM_FLOOD, timeout_s=15)
    assert run.result.status in {"killed", "done", "timeout"}
    after = (await bac.run(A.INSPECT_AFTER)).json()
    assert after["sysv"] == []  # les segments ne survivent pas à l'exécution
    assert await bac.sandbox.healthy()
    await bac.hello()


async def test_output_flood_truncated(bac: Bac) -> None:
    run = await bac.run(A.OUTPUT_FLOOD, timeout_s=3)
    assert run.result.truncated is True
    assert len(run.output.encode()) <= 65_536
    assert run.result.status in {"timeout", "killed"}
    await bac.hello()


async def test_forged_job_in_work_is_ignored(bac: Bac) -> None:
    data = (await bac.run(A.FORGE)).json()
    assert data["/spool/jobs"] == "PermissionError" and data["/spool"] == "PermissionError"
    await asyncio.sleep(1.5)  # le temps qu'un lanceur naïf le ramasse
    with pytest.raises(UnknownRun):
        await bac.sandbox.poll(FORGED, 0)
    assert not any("ffffffff" in p.name for d in ("jobs", "out") for p in (bac.spool / d).iterdir())
    assert "proof" not in (await bac.run(A.INSPECT_AFTER)).json()["tmp"]


async def test_leftovers_cleaned_after_run(bac: Bac) -> None:
    first = (await bac.run(A.LEAVE_THINGS)).json()
    assert first["shm"] >= 0
    after = (await bac.run(A.INSPECT_AFTER)).json()
    assert after["procs"] == [], "un démon du code a survécu à la fin de l'exécution"
    assert after["tmp"] == [] and after["shm_files"] == []
    assert after["work"] == [after["cwd"].rsplit("/", 1)[1]]  # son seul dossier
    assert after["cwd_files"] == ["main.py"] and after["sysv"] == []  # rien de la course d avant


async def test_next_run_works_after_abuse(bac: Bac) -> None:
    for abuse in (A.FORK_BOMB, A.OUTPUT_FLOOD, A.CPU_LOOP, A.MEMORY_SPREAD):
        await bac.run(abuse, timeout_s=2)
    await bac.hello()
    assert (await bac.run("import sys\nsys.exit(7)")).result.exit_code == 7
    assert await bac.sandbox.healthy()


async def test_cancel_stops_a_running_job(bac: Bac) -> None:
    code = "import time\ntime.sleep(60)"
    victim = uuid.uuid4().hex
    await bac.sandbox.submit(SandboxJob(victim, {"main.py": code}, "main.py", "run", 15))
    await asyncio.sleep(1)
    started = time.monotonic()
    await bac.sandbox.cancel(victim)
    for _ in range(50):
        progress = await bac.sandbox.poll(victim, 0)
        if progress.result is not None:
            break
        await asyncio.sleep(0.1)
    assert progress.result is not None and progress.result.status == "killed"
    assert time.monotonic() - started < 3


async def test_check_runs_the_exercise_tests_with_pytest(bac: Bac) -> None:
    files = {
        "main.py": "def double(x): return 2 * x",
        "test_main.py": "from main import double\ndef test_ok(): assert double(2) == 4\n",
    }
    run = await bac.run("", kind="check", files=files)
    assert (run.result.status, run.result.exit_code) == ("done", 0)
    assert "1 passed" in run.output


async def test_spool_volume_rights_come_from_the_image(bac: Bac) -> None:
    info = bac.spool.stat()
    assert stat.S_IMODE(info.st_mode) == 0o2770 and info.st_gid == 12345
    for sub in ("jobs", "out", "cancel"):
        assert stat.S_IMODE((bac.spool / sub).stat().st_mode) == 0o2770
