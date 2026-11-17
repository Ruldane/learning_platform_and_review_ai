"""Le lanceur (10.A1) sans changer d'identité : `RunEnv(drop=False)`. Ces tests tournent dans le
conteneur de test du back (Linux) ; l'isolation elle-même est prouvée par
`backend/tests/sandbox_live/test_escape.py`, contre le vrai conteneur.

Lancer : `cd backend && uv run pytest -c pyproject.toml ../sandbox/tests -q`."""

import dataclasses
import json
import os
import stat
import sys
import threading
import time
from pathlib import Path

import pytest

SANDBOX = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SANDBOX))

import runner  # noqa: E402
import runner_exec  # noqa: E402
import runner_job  # noqa: E402
from runner_job import JobRefused, Limits, RunEnv  # noqa: E402

LIMITS = Limits()


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


def log(env: RunEnv, run_id: str = "r1") -> str:
    return (env.spool / "out" / f"{run_id}.log").read_text()


def done(env: RunEnv, run_id: str = "r1") -> dict[str, object]:
    data: dict[str, object] = json.loads((env.spool / "out" / f"{run_id}.done.json").read_text())
    return data


def test_run_captures_output_and_exit_code(env: RunEnv) -> None:
    result = runner_exec.run_job(job("import sys\nprint('salut')\nsys.exit(3)"), LIMITS, env)
    assert (result.status, result.exit_code, result.truncated) == ("done", 3, False)
    assert log(env) == "salut\n"
    assert not (env.work / "r1").exists()  # dossier de travail retiré


def test_code_gets_an_empty_environment(env: RunEnv) -> None:
    os.environ["SECRET_DU_LANCEUR"] = "x"
    try:
        code = "import os, json\nprint(json.dumps(sorted(os.environ)))\nprint(os.environ['HOME'])"
        runner_exec.run_job(job(code), LIMITS, env)
    finally:
        del os.environ["SECRET_DU_LANCEUR"]
    names_line, home = log(env).splitlines()
    assert set(json.loads(names_line)) <= {"PATH", "HOME", "PYTHONDONTWRITEBYTECODE", "LC_CTYPE"}
    assert home == str(env.work / "r1")


def test_job_limits_clamped_by_runner() -> None:
    assert runner_job.clamp_timeout(999, LIMITS) == LIMITS.wall_max_s == 15
    assert runner_job.clamp_timeout(0, LIMITS) == 1
    assert runner_job.clamp_timeout(-5, LIMITS) == 1
    assert runner_job.clamp_timeout(None, LIMITS) == 10
    assert runner_job.clamp_timeout(True, LIMITS) == 10
    assert runner_job.clamp_timeout("999", LIMITS) == 10
    greedy = job("x=1", timeout_s=10**9, limits={"cpu_s": 9999, "memory_bytes": 10**12})
    assert runner_job.validate_job(greedy, LIMITS).wall_s == 15
    # Le travail ne touche jamais aux plafonds : constantes du lanceur.
    assert (LIMITS.cpu_s, LIMITS.memory_bytes) == (10, 256 * 1024 * 1024)
    assert (LIMITS.processes, LIMITS.file_bytes, LIMITS.output_bytes) == (32, 8 * 1024**2, 65_536)
    assert (LIMITS.uid, LIMITS.gid, LIMITS.max_files, LIMITS.max_total_bytes) == (
        20000,
        20000,
        20,
        200_000,
    )


def test_wall_clock_kills_a_runaway(env: RunEnv) -> None:
    start = time.monotonic()
    result = runner_exec.run_job(job("while True: pass", timeout_s=1), LIMITS, env)
    assert result.status == "timeout" and result.exit_code is None
    assert time.monotonic() - start < 5


@pytest.mark.parametrize(
    "name", ["../x.py", "/abs.py", ".", "a/./b.py", "a/../b.py", "a//b.py", "a\\b.py", "", "a/"]
)
def test_path_traversal_in_file_names_refused(env: RunEnv, name: str) -> None:
    bad = job("x=1") | {"files": {"main.py": "x=1", name: "y"}}
    with pytest.raises(JobRefused):
        runner_job.validate_job(bad, LIMITS)
    result = runner_exec.run_job(bad, LIMITS, env)
    assert result.status == "error"
    assert "refusé" in log(env)
    assert list(env.work.iterdir()) == []


def test_too_many_files_or_bytes_refused() -> None:
    many = job("x=1") | {"files": {f"f{i}.py": "x" for i in range(20)} | {"main.py": "x"}}
    with pytest.raises(JobRefused):
        runner_job.validate_job(many, LIMITS)
    with pytest.raises(JobRefused):
        runner_job.validate_job(job("x" * 200_001), LIMITS)
    for broken in ({"entry": "absent.py"}, {"kind": "other"}, {"run_id": "../x"}, {"files": {}}):
        with pytest.raises(JobRefused):
            runner_job.validate_job(job("x=1") | broken, LIMITS)
    with pytest.raises(JobRefused):
        runner_job.validate_job("pas un dict", LIMITS)


def test_files_written_in_subfolders_and_importable(env: RunEnv) -> None:
    files = {"main.py": "from pkg.util import f\nprint(f())", "pkg/util.py": "def f(): return 42"}
    assert runner_exec.run_job(job("", files=files), LIMITS, env).status == "done"
    assert log(env) == "42\n"


def test_file_and_folder_name_conflict_is_an_error_and_leaves_nothing(env: RunEnv) -> None:
    clash = job("x=1") | {"files": {"main.py": "x", "a": "f", "a/b.py": "y"}}
    assert runner_exec.run_job(clash, LIMITS, env).status == "error"
    assert list(env.work.iterdir()) == []


def test_cancel_kills_run(env: RunEnv) -> None:
    def cancel_soon() -> None:
        time.sleep(0.6)
        (env.spool / "cancel" / "r1").touch()

    threading.Thread(target=cancel_soon).start()
    start = time.monotonic()
    result = runner_exec.run_job(job("import time\ntime.sleep(30)", timeout_s=15), LIMITS, env)
    assert result.status == "killed"
    assert time.monotonic() - start < 4


def test_output_is_cut_at_the_cap_on_a_character_boundary(env: RunEnv) -> None:
    code = "import sys\nsys.stdout.write('é' * 100000)"
    result = runner_exec.run_job(job(code), LIMITS, env)
    text = (env.spool / "out" / "r1.log").read_bytes()
    assert result.truncated and len(text) <= 65_536
    text.decode("utf-8")  # pas de caractère coupé


def test_check_runs_the_tests_with_pytest(env: RunEnv) -> None:
    files = {
        "calc.py": "def add(a, b): return a + b",
        "test_calc.py": (
            "from calc import add\n"
            "def test_add(): assert add(1, 2) == 3\n"
            "def test_bad(): assert add(1, 1) == 3\n"
        ),
    }
    result = runner_exec.run_job(job("", kind="check", files=files, entry="calc.py"), LIMITS, env)
    assert (result.status, result.exit_code) == ("done", 1)
    assert "1 failed, 1 passed" in log(env)
    assert not (env.work / "r1").exists()


def test_stale_files_purged(env: RunEnv) -> None:
    now = time.time()
    old, fresh = env.spool / "out" / "a.log", env.spool / "out" / "b.log"
    done_old, tmp_old = env.spool / "out" / "a.done.json", env.spool / "jobs" / ".c.tmp"
    for path in (old, fresh, tmp_old, done_old):
        path.write_text("x")
    for path in (old, done_old):
        os.utime(path, (now - 3600, now - 3600))
    os.utime(tmp_old, (now - 120, now - 120))
    assert runner.purge_stale(env.spool, now) == 3
    assert [p.name for p in (env.spool / "out").iterdir()] == ["b.log"]
    assert list((env.spool / "jobs").iterdir()) == []


def test_runner_processes_a_dropped_job_and_writes_done_atomically(env: RunEnv) -> None:
    r = runner.Runner(env)
    r.prepare()
    path = env.spool / "jobs" / "r1.json"
    path.write_text(json.dumps(job("print('ok')")))
    assert r.next_job() == path
    r.process(path)
    end = done(env)
    assert end == {
        "status": "done",
        "exit_code": 0,
        "duration_ms": end["duration_ms"],
        "truncated": False,
    }
    assert not path.exists()
    assert stat.S_IMODE((env.spool / "out" / "r1.done.json").stat().st_mode) == 0o660
    assert not list((env.spool / "out").glob(".*"))  # pas de fichier temporaire


def test_runner_refuses_forged_or_unreadable_jobs(env: RunEnv) -> None:
    r = runner.Runner(env)
    r.prepare()
    jobs = env.spool / "jobs"
    (jobs / "r1.json").write_text(json.dumps(job("print(1)", run_id="autre")))
    r.process(jobs / "r1.json")
    assert done(env, "r1")["status"] == "error"
    (jobs / "r2.json").write_text("{pas du json")
    r.process(jobs / "r2.json")
    assert done(env, "r2")["status"] == "error"
    (jobs / "r3.json").symlink_to("/etc/passwd")
    r.process(jobs / "r3.json")  # lien symbolique : jamais suivi
    assert done(env, "r3")["status"] == "error"
    (jobs / "nom etranger.json").write_text("{}")
    assert r.next_job() is None  # le nom étranger est jeté
    assert list(jobs.iterdir()) == []


def test_runner_cancel_before_start_never_runs(env: RunEnv) -> None:
    r = runner.Runner(env)
    r.prepare()
    marker = env.work.parent / "ran"
    (env.spool / "jobs" / "r1.json").write_text(json.dumps(job(f"open({str(marker)!r}, 'w')")))
    (env.spool / "cancel" / "r1").touch()
    r.process(env.spool / "jobs" / "r1.json")
    assert not marker.exists()
    assert done(env)["status"] == "killed"
    assert not (env.spool / "cancel" / "r1").exists()


def test_runner_orphan_log_gets_an_error_end_on_restart(env: RunEnv) -> None:
    (env.spool / "out" / "r9.log").write_text("début")
    runner.Runner(env).prepare()
    assert done(env, "r9")["status"] == "error"


def test_runner_spool_dirs_are_setgid_and_group_writable(env: RunEnv) -> None:
    runner.Runner(env).prepare()
    for sub in (env.spool, env.spool / "jobs", env.spool / "out", env.spool / "cancel"):
        assert stat.S_IMODE(sub.stat().st_mode) == 0o2770


def test_heartbeat_is_written_at_most_once_a_second(env: RunEnv) -> None:
    r = runner.Runner(env)
    r.prepare()
    r.beat()
    beat = env.spool / "heartbeat"
    first = beat.stat().st_mtime_ns
    assert stat.S_IMODE(beat.stat().st_mode) == 0o660
    r.beat()
    assert beat.stat().st_mtime_ns == first


def test_runner_result_and_run_id_match_the_port() -> None:
    from app.providers.sandbox.base import SandboxResult, check_run_id

    assert [f.name for f in dataclasses.fields(runner_job.SandboxResult)] == [
        f.name for f in dataclasses.fields(SandboxResult)
    ]
    for run_id in ("a" * 32, "12345678-1234-4234-8234-123456789abc"):
        check_run_id(run_id)  # tout identifiant que le port accepte, le lanceur le sert
        assert runner_job.RUN_ID.fullmatch(run_id)
