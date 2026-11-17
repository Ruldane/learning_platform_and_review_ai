# ruff: noqa: E501
"""Correctifs de la relecture de sécurité de 10.A1 (I1 à I3, M1, M3, M5) : comme les autres tests
unitaires du lanceur, sans changer d'identité (`RunEnv(drop=False)`).

Lancer : `cd backend && uv run pytest -c pyproject.toml ../sandbox/tests -q`."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SANDBOX = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SANDBOX))

import runner  # noqa: E402
import runner_exec  # noqa: E402
import runner_proc  # noqa: E402
from runner_job import Limits, RunEnv, Unsafe  # noqa: E402

LIMITS = Limits()
SHM = """       key      shmid perms                  size  cpid  lpid nattch   uid   gid  cuid  cgid      atime      dtime      ctime                   rss                  swap
         0          1  1666                 4096   100   100      0 20000 20000 20000 20000          0          0          1                     0                     0
         0          2  1666                 4096   100   100      0     0     0 20000 20000          0          0          1                     0                     0
         0          3  1666                 4096   100   100      0 20000 20000     0     0          0          0          1                     0                     0
         0          4  1666                 4096   100   100      0     0     0     0     0          0          0          1                     0                     0
"""


@pytest.fixture
def env(tmp_path: Path) -> RunEnv:
    for name in ("jobs", "out", "cancel"):
        (tmp_path / "spool" / name).mkdir(parents=True)
    (tmp_path / "work").mkdir()
    return RunEnv(spool=tmp_path / "spool", work=tmp_path / "work", drop=False, clean_roots=())


def job(code: str, run_id: str = "r1", **extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "run_id": run_id,
        "files": {"main.py": code},
        "entry": "main.py",
        "kind": "run",
        "timeout_s": 5,
    }
    return base | extra


def done(env: RunEnv, run_id: str = "r1") -> dict[str, object]:
    data: dict[str, object] = json.loads((env.spool / "out" / f"{run_id}.done.json").read_text())
    return data


def test_sysv_cleanup_covers_objects_the_code_created_but_gave_away() -> None:
    """I1 : `IPC_SET` change le propriétaire (`uid`) ; le créateur (`cuid`) reste 20000."""
    assert runner_proc.sysv_ids(SHM, 20000, "shmid") == [1, 2, 3]
    assert runner_proc.sysv_ids(SHM, 0, "shmid") == [2, 3, 4]  # jamais ceux d'un autre uid
    assert runner_proc.sysv_ids("", 20000, "shmid") == []
    assert runner_proc.sysv_ids("seul l'entête", 20000, "shmid") == []


def test_process_name_cannot_break_the_status_parsing() -> None:
    """I2 : `Name:` est fixé par le code (`prctl`) et peut contenir un retour chariot."""
    trap = (
        b"Name:\ta\rVmRSS:\tx\rUid:\t0\t0\nState:\tR (running)\nUid:\t20000\t20000\t20000\t20000\n"
    )
    assert runner_proc.parse_status(trap) == ({20000}, "R", 0)  # la fausse ligne est ignorée
    real = trap + b"VmRSS:\t2048 kB\n"
    assert runner_proc.parse_status(real) == ({20000}, "R", 2048 * 1024)
    zombie = b"Name:\tx\nState:\tZ (zombie)\nUid:\t20000\t20000\t20000\t20000\n"
    assert runner_proc.parse_status(zombie) == ({20000}, "Z", 0)
    garbled = b"Name:\tx\nState:\tR\nUid:\t20000\t20000\nVmRSS:\tpas un nombre kB\n"
    assert runner_proc.parse_status(garbled) == ({20000}, "R", 0)  # jamais d'exception
    for junk in (b"", b"Name:\tx", b"Name:\tx\nUid:\tbof\n", b"\xff\xfe\n\x00"):
        assert runner_proc.parse_status(junk) is None


def test_wipe_dir_reports_success_and_removes_nested_trees(tmp_path: Path) -> None:
    """M1 : `_wipe_dir` rend `True` quand tout est parti (dossiers sous la racine compris)."""
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "f.txt").write_text("x")
    (tmp_path / "g").write_text("y")
    assert runner_proc._wipe_dir(str(tmp_path), os.getuid()) is True
    assert list(tmp_path.iterdir()) == []


def test_serve_survives_an_unexpected_exception(
    env: RunEnv, capsys: pytest.CaptureFixture[str]
) -> None:
    """I2 : un incident inattendu clôt le travail en `error` et le lanceur continue."""
    r = runner.Runner(env)
    r.prepare()
    (env.spool / "jobs" / "r1.json").write_text(json.dumps(job("print(1)")))
    (env.spool / "jobs" / "r2.json").write_text(json.dumps(job("print(2)", run_id="r2")))
    real = r.process

    def flaky(path: Path) -> None:
        if path.stem == "r1":
            raise RuntimeError("SECRET-DU-TRAVAIL")
        real(path)
        r.stopping = True

    r.process = flaky  # type: ignore[method-assign]
    r.serve()  # ne lève pas, et finit après le second travail
    assert done(env, "r1")["status"] == "error"
    assert done(env, "r2")["status"] == "done"
    assert list((env.spool / "jobs").iterdir()) == []
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "r1" in err and "SECRET-DU-TRAVAIL" not in err


def test_job_is_never_invisible_between_pickup_and_log(
    env: RunEnv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """I3 : le journal existe avant que le fichier du travail soit retiré."""
    r = runner.Runner(env)
    r.prepare()
    path = env.spool / "jobs" / "r1.json"
    path.write_text(json.dumps(job("print('ok')")))
    seen: list[tuple[bool, bool]] = []
    real_unlink = runner._unlink

    def watching(target: Path) -> None:
        if target == path:
            seen.append((target.exists(), (env.spool / "out" / "r1.log").exists()))
        real_unlink(target)

    monkeypatch.setattr(runner, "_unlink", watching)
    real_run = runner_exec.run_job

    def run_checking(*args: object, **kwargs: object) -> object:
        assert not path.exists() and (env.spool / "out" / "r1.log").exists()
        return real_run(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(runner_exec, "run_job", run_checking)
    r.process(path)
    assert seen == [(True, True)]  # le fichier du travail partait alors que le journal existait
    assert done(env)["status"] == "done"


def test_unreadable_job_is_still_claimed_with_a_log(env: RunEnv) -> None:
    r = runner.Runner(env)
    r.prepare()
    path = env.spool / "jobs" / "r1.json"
    path.write_text("{pas du json")
    r.process(path)
    assert not path.exists() and (env.spool / "out" / "r1.log").exists()
    assert done(env)["status"] == "error"


def test_orphan_job_taken_then_interrupted_does_not_run_again(env: RunEnv) -> None:
    (env.spool / "out" / "r9.log").write_text("")
    (env.spool / "jobs" / "r9.json").write_text(json.dumps(job("print(1)", run_id="r9")))
    runner.Runner(env).prepare()
    assert done(env, "r9")["status"] == "error"
    assert not (env.spool / "jobs" / "r9.json").exists()


def test_next_job_tolerates_a_dangling_link(env: RunEnv) -> None:
    """I2 : un lien pendant dans `jobs/` ne fait pas tomber le lanceur."""
    r = runner.Runner(env)
    r.prepare()
    (env.spool / "jobs" / "r5.json").symlink_to(env.work / "absent")
    (env.spool / "jobs" / "autre.lien").symlink_to(env.work / "absent")
    assert r.next_job() == env.spool / "jobs" / "r5.json"
    r.process(env.spool / "jobs" / "r5.json")  # jamais suivi : fin `error`
    assert done(env, "r5")["status"] == "error"
    assert r.next_job() is None


def test_leftover_that_cannot_be_removed_stops_the_runner(
    env: RunEnv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M1 : un balayage ou un nettoyage qui échoue = plus aucun travail servi (fin `error`, puis
    `Unsafe` : le lanceur s'arrête, Compose le relance)."""
    r = runner.Runner(env)
    r.prepare()
    monkeypatch.setattr(runner_proc, "kill_user_processes", lambda uid, rounds=100: False)
    path = env.spool / "jobs" / "r1.json"
    path.write_text(json.dumps(job("print('ok')")))
    with pytest.raises(Unsafe):
        r.process(path)
    assert done(env)["status"] == "error"
    with pytest.raises(Unsafe):
        r.prepare()  # même au démarrage


def test_main_exits_with_code_70_when_unsafe(env: RunEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    real = runner.Runner
    monkeypatch.setattr(runner, "Runner", lambda _env: real(env))
    monkeypatch.setattr(runner.signal, "signal", lambda *args: None)
    monkeypatch.setattr(runner_proc, "kill_user_processes", lambda uid, rounds=100: False)
    assert runner.main() == runner.UNSAFE_EXIT == 70


def test_a_process_that_does_not_die_stops_the_runner(
    env: RunEnv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M3 : `wait` borné ; au-delà, `Unsafe` (et non un blocage du lanceur)."""

    def never(self: subprocess.Popen[bytes], timeout: float | None = None) -> int:
        raise subprocess.TimeoutExpired("python", timeout or 0)

    monkeypatch.setattr(subprocess.Popen, "wait", never)
    with pytest.raises(Unsafe):
        runner_exec.run_job(job("print(1)"), LIMITS, env)
    assert list(env.work.iterdir()) == []  # le nettoyage a eu lieu malgré tout


def test_a_job_of_control_characters_is_not_too_big(env: RunEnv) -> None:
    """M5 : 200 000 caractères de contrôle font 1,2 Mo de JSON : la limite du lanceur le permet."""
    r = runner.Runner(env)
    r.prepare()
    path = env.spool / "jobs" / "r1.json"
    raw = json.dumps(job("\x01" * 200_000))
    assert len(raw) > 1_000_000
    path.write_text(raw)
    r.process(path)
    assert "trop gros" not in (env.spool / "out" / "r1.log").read_text()
    assert done(env)["status"] == "done"
