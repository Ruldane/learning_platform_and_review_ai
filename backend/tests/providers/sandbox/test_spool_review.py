"""Correctifs de la relecture de 10.A1 côté back (M5, M6) : lecture du journal bornée, travaux
de caractères de contrôle, texte invalide, dépôt sans course sur un doublon."""

import asyncio
import json
from pathlib import Path

import pytest

from app.providers.sandbox.base import MAX_OUTPUT_BYTES, MAX_TOTAL_BYTES, SandboxJob, UnknownRun
from app.providers.sandbox.spool import MAX_JOB_BYTES, MAX_READ_BYTES, SpoolSandbox

R1, R2 = "1" * 32, "2" * 32


@pytest.fixture
def spool(tmp_path: Path) -> Path:
    for name in ("jobs", "out", "cancel"):
        (tmp_path / name).mkdir()
    return tmp_path


def job(run_id: str = R1, code: str = "print(1)") -> SandboxJob:
    return SandboxJob(run_id=run_id, files={"main.py": code}, entry="main.py", kind="run")


async def test_log_read_is_bounded_even_if_the_volume_holds_a_huge_file(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    await sandbox.submit(job())
    (spool / "out" / f"{R1}.log").write_bytes(b"x" * (MAX_READ_BYTES * 20))
    progress = await sandbox.poll(R1, 0)
    assert len(progress.output) == MAX_READ_BYTES == MAX_OUTPUT_BYTES + 4
    assert progress.next_offset == MAX_READ_BYTES


async def test_job_of_control_characters_fits_the_runner_limit(spool: Path) -> None:
    """200 000 caractères de contrôle font 1,2 Mo de JSON : acceptés, sous la limite du lanceur."""
    await SpoolSandbox(spool).submit(job(code="\x01" * MAX_TOTAL_BYTES))
    size = (spool / "jobs" / f"{R1}.json").stat().st_size
    assert 1_000_000 < size <= MAX_JOB_BYTES
    assert json.loads((spool / "jobs" / f"{R1}.json").read_text())["files"]["main.py"][0] == "\x01"


async def test_non_ascii_job_is_written_as_utf8_and_a_lone_surrogate_is_refused(
    spool: Path,
) -> None:
    sandbox = SpoolSandbox(spool)
    await sandbox.submit(job(code="print('é')"))
    assert "é" in (spool / "jobs" / f"{R1}.json").read_text(encoding="utf-8")
    for bad in ("x = '\ud800'", "\udfff"):
        with pytest.raises(ValueError):
            await sandbox.submit(job(R2, bad))
    assert not (spool / "jobs" / f"{R2}.json").exists()
    assert sorted(p.name for p in (spool / "jobs").iterdir()) == [f"{R1}.json"]  # aucun reste


async def test_a_duplicate_deposit_never_overwrites_the_first(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    await sandbox.submit(job(code="print('premier')"))
    with pytest.raises(ValueError, match="déjà déposé"):
        await sandbox.submit(job(code="print('second')"))
    assert "premier" in (spool / "jobs" / f"{R1}.json").read_text()
    assert sorted(p.name for p in (spool / "jobs").iterdir()) == [f"{R1}.json"]


async def test_two_simultaneous_deposits_of_one_id_leave_exactly_one(spool: Path) -> None:
    sandbox = SpoolSandbox(spool)
    results = await asyncio.gather(
        *(sandbox.submit(job(code=f"print({n})")) for n in range(8)), return_exceptions=True
    )
    assert sum(r is None for r in results) == 1
    assert all(isinstance(r, ValueError) for r in results if r is not None)
    assert sorted(p.name for p in (spool / "jobs").iterdir()) == [f"{R1}.json"]


async def test_job_taken_between_the_two_reads_is_not_unknown(
    spool: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N1 : le lanceur crée le journal et retire le travail entre la lecture du journal (absent) et
    celle du travail : `poll` relit le journal au lieu de lever `UnknownRun`."""
    sandbox = SpoolSandbox(spool)
    await sandbox.submit(job())
    real = SpoolSandbox._job
    taken: list[bool] = []

    def racing(self: SpoolSandbox, run_id: str) -> Path:
        path = real(self, run_id)
        if not taken:  # la première lecture du travail : le lanceur vient de le prendre
            taken.append(True)
            (spool / "out" / f"{run_id}.log").write_bytes(b"")
            path.unlink()
        return path

    monkeypatch.setattr(SpoolSandbox, "_job", racing)
    progress = await sandbox.poll(R1, 0)
    assert progress.result is None and progress.output == ""  # en cours, pas inconnu


async def test_unknown_job_is_still_unknown_after_the_second_read(spool: Path) -> None:
    with pytest.raises(UnknownRun):
        await SpoolSandbox(spool).poll(R2, 0)
