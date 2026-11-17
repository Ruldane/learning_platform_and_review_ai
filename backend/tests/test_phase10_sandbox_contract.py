"""Le port du bac à sable (10.P) : plafonds, validation des chemins et des identifiants, double de
test (`FakeSandbox`) : sortie scriptée, état « en cours », annulation."""

import uuid

import pytest

from app.providers.sandbox.base import (
    MAX_FILES,
    MAX_OUTPUT_BYTES,
    MAX_TIMEOUT_S,
    MAX_TOTAL_BYTES,
    SandboxJob,
    SandboxResult,
    UnknownRun,
    check_job_limits,
)
from app.providers.sandbox.fake import FakeSandbox


def rid() -> str:
    return str(uuid.uuid4())


def job(run_id: str | None = None, kind: str = "run", **changes: object) -> SandboxJob:
    values: dict[str, object] = {
        "run_id": rid() if run_id is None else run_id,
        "files": {"main.py": "x"},
        "entry": "main.py",
        "kind": kind,
    }
    values.update(changes)
    return SandboxJob(**values)  # type: ignore[arg-type]


def test_sandbox_job_ceilings_constants() -> None:
    assert (MAX_FILES, MAX_TOTAL_BYTES, MAX_TIMEOUT_S, MAX_OUTPUT_BYTES) == (
        20,
        200_000,
        15,
        65_536,
    )
    assert SandboxJob(run_id="r", files={}, entry="main.py", kind="run").timeout_s == 10


def test_check_means_running_the_exercise_tests_with_pytest() -> None:
    doc = (SandboxJob.__doc__ or "") + (check_job_limits.__doc__ or "")
    assert "pytest" in doc and "syntaxe" not in doc


@pytest.mark.parametrize(
    "name",
    [
        "",
        ".",
        "..",
        "a/..",
        "../x",
        "/abs.py",
        "\\x.py",
        "a//b.py",
        "a/./b.py",
        "a/",
        "a\0b",
        "C:/x.py",
        "a\\b.py",
    ],
)
def test_bad_file_names_refused(name: str) -> None:
    with pytest.raises(ValueError):
        check_job_limits(job(files={name: "x", "main.py": "x"}))


@pytest.mark.parametrize("entry", [".", "", "..", "/main.py"])
def test_bad_entries_refused(entry: str) -> None:
    with pytest.raises(ValueError):
        check_job_limits(job(files={entry: "x"}, entry=entry))


@pytest.mark.parametrize("run_id", ["", "../x", "r1", "a/b", "G" * 32, "x" * 200, "..", " "])
def test_bad_run_ids_refused(run_id: str) -> None:
    with pytest.raises(ValueError):
        check_job_limits(job(run_id=run_id))


def test_run_id_accepts_uuid_hex_and_uuid4_text() -> None:
    value = uuid.uuid4()
    check_job_limits(job(run_id=value.hex))
    check_job_limits(job(run_id=str(value)))
    check_job_limits(job(files={"pkg/a.py": "x", "main.py": "x"}))


async def test_fake_sandbox_scripted() -> None:
    done = SandboxResult(status="done", exit_code=0, duration_ms=12, truncated=False)
    timeout = SandboxResult(status="timeout", exit_code=None, duration_ms=10_000, truncated=False)
    r1, r2, r3 = rid(), rid(), rid()
    sandbox = FakeSandbox({r1: "bonjour\n", r2: timeout, "*": done})
    assert await sandbox.healthy() is True

    await sandbox.submit(job(r1))
    first = await sandbox.poll(r1, 0)
    assert first.output == "bonjour\n" and first.next_offset == len(b"bonjour\n")
    assert first.result is not None and first.result.status == "done"
    assert first.result.exit_code == 0
    rest = await sandbox.poll(r1, first.next_offset)
    assert rest.output == "" and rest.next_offset == first.next_offset
    assert (await sandbox.poll(r1, 3)).output == "jour\n"

    await sandbox.submit(job(r2))
    assert (await sandbox.poll(r2, 0)).result == timeout
    await sandbox.submit(job(r3, kind="check"))
    assert (await sandbox.poll(r3, 0)).result == done  # repli « * »
    with pytest.raises(UnknownRun):
        await sandbox.poll(rid(), 0)


async def test_fake_sandbox_cancel_keeps_a_finished_run_finished() -> None:
    run = rid()
    sandbox = FakeSandbox({run: "fini\n"})
    await sandbox.submit(job(run))
    await sandbox.cancel(run)
    result = (await sandbox.poll(run, 0)).result
    assert result is not None and result.status == "done" and result.exit_code == 0
    await sandbox.cancel(rid())  # inconnu : sans effet


async def test_fake_sandbox_running_state_grows_by_chunks_and_can_be_cancelled() -> None:
    run, other = rid(), rid()
    sandbox = FakeSandbox({run: ("a\n", "b\n", "c\n"), other: ("x\n", "y\n")})
    await sandbox.submit(job(run))
    first = await sandbox.poll(run, 0)
    assert first.output == "a\n" and first.result is None
    second = await sandbox.poll(run, first.next_offset)
    assert second.output == "b\n" and second.result is None
    third = await sandbox.poll(run, second.next_offset)
    assert third.output == "c\n" and third.result is not None
    assert third.result.status == "done"

    await sandbox.submit(job(other))
    assert (await sandbox.poll(other, 0)).result is None
    await sandbox.cancel(other)
    cut = await sandbox.poll(other, 0)
    assert cut.output == "x\n"
    assert cut.result is not None and cut.result.status == "killed"


async def test_fake_sandbox_truncates_and_checks_ceilings() -> None:
    big = rid()
    sandbox = FakeSandbox({"*": "é" * MAX_OUTPUT_BYTES})
    await sandbox.submit(job(big))
    progress = await sandbox.poll(big, 0)
    assert progress.next_offset <= MAX_OUTPUT_BYTES
    assert progress.result is not None and progress.result.truncated is True
    too_many = {f"f{i}.py": "x" for i in range(MAX_FILES + 1)}
    for bad in (
        job(files=too_many, entry="f0.py"),
        job(files={"main.py": "x" * (MAX_TOTAL_BYTES + 1)}),
        job(timeout_s=MAX_TIMEOUT_S + 1),
        job(entry="absent.py"),
    ):
        with pytest.raises(ValueError):
            await sandbox.submit(bad)
