"""`SpoolSandbox` (10.A1) : le côté back du volume d'échange, sans conteneur. Le lanceur est joué
à la main : on écrit les fichiers qu'il écrirait (`out/<id>.log`, `out/<id>.done.json`)."""

import json
import os
import stat
import time
from pathlib import Path

import pytest

from app.providers.sandbox.base import (
    MAX_FILES,
    MAX_TOTAL_BYTES,
    SandboxJob,
    SandboxResult,
    UnknownRun,
)
from app.providers.sandbox.spool import QUEUE_DEAD_S, SpoolSandbox

R1, R2, R3 = "1" * 32, "2" * 32, "3" * 32


@pytest.fixture
def spool(tmp_path: Path) -> Path:
    for name in ("jobs", "out", "cancel"):
        (tmp_path / name).mkdir()
    return tmp_path


def job(run_id: str = R1, files: dict[str, str] | None = None, **kw: object) -> SandboxJob:
    files = files if files is not None else {"main.py": "print(1)"}
    return SandboxJob(run_id=run_id, files=files, entry="main.py", kind="run", **kw)  # type: ignore[arg-type]


def finish(spool: Path, run_id: str, out: bytes, status: str = "done") -> None:
    (spool / "out" / f"{run_id}.log").write_bytes(out)
    done = {"status": status, "exit_code": 0, "duration_ms": 5, "truncated": False}
    (spool / "out" / f"{run_id}.done.json").write_text(json.dumps(done))


async def test_job_written_atomically_with_0660(spool: Path) -> None:
    os.umask(0o022)  # le umask du back : sans `fchmod`, le groupe perdrait l'écriture
    await SpoolSandbox(spool).submit(job())
    path = spool / "jobs" / f"{R1}.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o660
    assert sorted(p.name for p in (spool / "jobs").iterdir()) == [f"{R1}.json"]  # pas de reste .tmp
    payload = json.loads(path.read_text())
    assert payload == {
        "run_id": R1,
        "files": {"main.py": "print(1)"},
        "entry": "main.py",
        "kind": "run",
        "timeout_s": 10,
    }


async def test_submit_twice_same_id_refused(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    await sandbox.submit(job())
    with pytest.raises(ValueError, match="déjà"):
        await sandbox.submit(job())


async def test_poll_returns_output_from_offset(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    await sandbox.submit(job())
    (spool / "out" / f"{R1}.log").write_bytes("héllo ".encode())
    first = await sandbox.poll(R1, 0)
    assert (first.output, first.result) == ("héllo ", None)
    assert first.next_offset == len("héllo ".encode())  # octets, pas caractères
    finish(spool, R1, "héllo monde".encode())
    rest = await sandbox.poll(R1, first.next_offset)
    assert rest.output == "monde"
    assert rest.result == SandboxResult("done", 0, 5, False)
    again = await sandbox.poll(R1, rest.next_offset)
    assert (again.output, again.next_offset) == ("", rest.next_offset)


async def test_poll_holds_back_a_split_character_until_the_run_ends(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    await sandbox.submit(job())
    (spool / "out" / f"{R1}.log").write_bytes(b"a" + "é".encode()[:1])
    part = await sandbox.poll(R1, 0)
    assert (part.output, part.next_offset) == ("a", 1)
    finish(spool, R1, b"a" + "é".encode())
    assert (await sandbox.poll(R1, 1)).output == "é"


async def test_poll_unknown_run_is_error_not_hang(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    for bad in ("nope", "../x", "", "a/b", "x" * 99):
        with pytest.raises(UnknownRun):
            await sandbox.poll(bad, 0)


async def test_poll_queued_run_is_running_then_error_if_runner_is_dead(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    await sandbox.submit(job())
    queued = await sandbox.poll(R1, 0)
    assert queued.result is None and queued.output == ""
    old = time.time() - QUEUE_DEAD_S - 5
    os.utime(spool / "jobs" / f"{R1}.json", (old, old))
    assert (await sandbox.poll(R1, 0)).result == SandboxResult("error", None, 0, False)
    (spool / "heartbeat").write_text("x")  # le lanceur bat : le travail attend son tour
    assert (await sandbox.poll(R1, 0)).result is None


async def test_poll_corrupt_done_file_is_error(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    await sandbox.submit(job())
    (spool / "out" / f"{R1}.log").write_bytes(b"x")
    (spool / "out" / f"{R1}.done.json").write_text("{pas du json")
    assert (await sandbox.poll(R1, 0)).result == SandboxResult("error", None, 0, False)


@pytest.mark.parametrize("name", ["../x.py", "/abs.py", ".", "a/../b.py", "a//b.py", ""])
async def test_path_traversal_in_file_names_refused(spool: Path, name: str) -> None:
    with pytest.raises(ValueError):
        await SpoolSandbox(spool).submit(job(files={"main.py": "x", name: "y"}))
    assert list((spool / "jobs").iterdir()) == []


@pytest.mark.parametrize(
    "run_id", ["../evil", "a/b", "", ".hidden", "x" * 65, "a b", "r1", "A" * 32]
)
async def test_bad_run_id_refused(spool: Path, run_id: str) -> None:
    with pytest.raises(ValueError):
        await SpoolSandbox(spool).submit(job(run_id=run_id))
    assert list((spool / "jobs").iterdir()) == []


async def test_too_many_files_or_bytes_refused(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    many = {f"f{i}.py": "x" for i in range(MAX_FILES + 1)}
    with pytest.raises(ValueError):
        await sandbox.submit(SandboxJob(R2, many, "f0.py", "run"))
    big = {"main.py": "x" * (MAX_TOTAL_BYTES + 1)}
    with pytest.raises(ValueError):
        await sandbox.submit(SandboxJob(R3, big, "main.py", "run"))
    with pytest.raises(ValueError):
        await sandbox.submit(job(timeout_s=999))
    assert list((spool / "jobs").iterdir()) == []


async def test_cancel_drops_a_marker_only_for_a_running_run(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    await sandbox.cancel("ghost")  # inconnu : sans effet
    await sandbox.cancel("../x")
    assert list((spool / "cancel").iterdir()) == []
    await sandbox.submit(job())
    await sandbox.cancel(R1)
    marker = spool / "cancel" / R1
    assert marker.exists() and stat.S_IMODE(marker.stat().st_mode) == 0o660
    await sandbox.submit(job(R2))
    finish(spool, R2, b"x")
    await sandbox.cancel(R2)  # fini : sans effet
    assert not (spool / "cancel" / R2).exists()


async def test_healthy_follows_the_heartbeat_age(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    assert await sandbox.healthy() is False  # pas de battement
    beat = spool / "heartbeat"
    beat.write_text("x")
    assert await sandbox.healthy() is True
    old = time.time() - 30
    os.utime(beat, (old, old))
    assert await sandbox.healthy() is False
    assert await SpoolSandbox(spool / "absent").healthy() is False
