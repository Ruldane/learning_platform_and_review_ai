# ruff: noqa: E501
"""Mineurs de la revérification de 10.A1 (M3, N2, M1) : une borne qui s'exécute vraiment, un `Unsafe`
qu'une panne du volume ne remplace pas, un nettoyage qui lève n'est pas un « travail illisible ».

Lancer : `cd backend && uv run pytest -c pyproject.toml ../sandbox/tests -q`."""

import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

SANDBOX = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SANDBOX))

import runner  # noqa: E402
import runner_exec  # noqa: E402
import runner_proc  # noqa: E402
from runner_job import Limits, RunEnv, Unsafe, validate_job  # noqa: E402

LIMITS = Limits()


@pytest.fixture
def env(tmp_path: Path) -> RunEnv:
    for name in ("jobs", "out", "cancel"):
        (tmp_path / "spool" / name).mkdir(parents=True)
    (tmp_path / "work").mkdir()
    return RunEnv(spool=tmp_path / "spool", work=tmp_path / "work", drop=False, clean_roots=())


def job(code: str = "print(1)", run_id: str = "r1") -> dict[str, object]:
    return {"run_id": run_id, "files": {"main.py": code}, "entry": "main.py", "kind": "run"}


class Stuck:
    """Un processus qui ne meurt jamais (état D) : `poll` rend toujours `None`."""

    pid = 2**22 + 7  # jamais un vrai processus : `killpg` échoue (OSError ignorée)

    def __init__(self, fd: int) -> None:
        self.stdout = types.SimpleNamespace(fileno=lambda: fd)

    def poll(self) -> None:
        return None

    def wait(self, timeout: float | None = None) -> int:
        raise subprocess.TimeoutExpired("python", timeout or 0)


def test_supervise_stops_the_runner_when_the_main_process_never_dies(
    env: RunEnv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M3 : la borne est dans la boucle (elle ne dépend plus de `poll`) ; sans elle, le lanceur
    tournerait sans fin en battant le coeur."""
    monkeypatch.setattr(runner_exec, "WAIT_S", 0.3)
    monkeypatch.setattr(runner_proc, "kill_user_processes", lambda uid, rounds=100: True)
    read_fd, write_fd = os.pipe()
    ticks: list[int] = []

    def tick() -> None:
        ticks.append(1)
        if len(ticks) > 200:  # 10 s : sans la borne, le test échoue au lieu de se bloquer
            raise RuntimeError("la boucle ne finit jamais")

    waiting = RunEnv(spool=env.spool, work=env.work, drop=False, clean_roots=(), tick=tick)
    valid = validate_job({**job(), "timeout_s": 1}, LIMITS)
    valid = type(valid)(valid.run_id, valid.files, valid.entry, valid.kind, 0)  # échéance aussitôt
    sink = runner_exec.LogSink(env.spool / "out" / "r1.log", 1_000)
    try:
        with pytest.raises(Unsafe):
            runner_exec.supervise(Stuck(read_fd), sink, valid, LIMITS, waiting)  # type: ignore[arg-type]
    finally:
        sink.close()
        os.close(read_fd)
        os.close(write_fd)
    assert len(ticks) < 100


def test_a_volume_failure_does_not_replace_unsafe(
    env: RunEnv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N2 : `refuse` et `write_done` peuvent lever `OSError` (volume plein) ; `Unsafe` sort quand
    même, le lanceur s'arrête."""
    r = runner.Runner(env)
    r.prepare()
    monkeypatch.setattr(runner_proc, "kill_user_processes", lambda uid, rounds=100: False)

    def full(*args: object, **kwargs: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(runner.Runner, "write_done", full)
    path = env.spool / "jobs" / "r1.json"
    path.write_text(json.dumps(job()))
    with pytest.raises(Unsafe):
        r.process(path)
    monkeypatch.setattr(runner.Runner, "refuse", full)
    second = env.spool / "jobs" / "r2.json"
    second.write_text(json.dumps(job(run_id="r2")))
    with pytest.raises(Unsafe):
        r.process(second)


def test_a_cleanup_that_raises_is_not_an_unreadable_job(
    env: RunEnv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M1 : une exception du nettoyage (`fork` refusé…) mène à `Unsafe`, pas à « travail
    illisible » suivi d'un lanceur qui continue sans avoir nettoyé."""
    r = runner.Runner(env)
    r.prepare()

    def refused(uid: int, rounds: int = 100) -> bool:
        raise OSError(11, "Resource temporarily unavailable")

    monkeypatch.setattr(runner_proc, "kill_user_processes", refused)
    path = env.spool / "jobs" / "r1.json"
    path.write_text(json.dumps(job()))
    with pytest.raises(Unsafe):
        r.process(path)
    assert "illisible" not in (env.spool / "out" / "r1.log").read_text()


def test_purge_that_raises_is_reported_as_not_clean(
    env: RunEnv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refused(*args: object, **kwargs: object) -> bool:
        raise OSError(12, "Cannot allocate memory")

    monkeypatch.setattr(runner_proc, "purge_user_files", refused)
    changing = RunEnv(spool=env.spool, work=env.work, drop=True, clean_roots=())
    assert runner_exec._cleanup(None, LIMITS, changing) is False
