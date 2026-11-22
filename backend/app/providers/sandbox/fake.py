"""Bac à sable de test (phase 10) : sortie scriptée, déterministe, sans processus ni disque.

`scripted` associe un `run_id` à une sortie : `str` (le travail finit `done`, code 0, dès le
dépôt), `SandboxResult` (fin sans sortie), ou `tuple[str, ...]` (**en cours** : chaque `poll` révèle
un morceau de plus, `result` reste `None` jusqu'au dernier, puis `done`, code 0). La clé `"*"`
répond à tout travail non scripté (les services créent leurs identifiants eux-mêmes). Sans clé ni
`"*"` : fin `done`, code 0, sortie vide. `cancel` rend `killed` un travail **en cours** (la sortie
déjà révélée reste) ; un travail fini reste fini, un inconnu est sans effet."""

from dataclasses import dataclass, field

from app.providers.sandbox.base import (
    MAX_INPUT_CHUNK_BYTES,
    MAX_OUTPUT_BYTES,
    SandboxJob,
    SandboxProgress,
    SandboxResult,
    UnknownRun,
    check_job_limits,
)

Script = SandboxResult | str | tuple[str, ...]


@dataclass
class _Run:
    data: bytes
    result: SandboxResult
    ends: list[int]  # fin (en octets) de chaque morceau ; une seule entrée = fini dès le dépôt
    revealed: int
    killed: bool = False
    killed_result: SandboxResult = field(init=False)

    def __post_init__(self) -> None:
        self.killed_result = SandboxResult(
            status="killed",
            exit_code=None,
            duration_ms=self.result.duration_ms,
            truncated=self.result.truncated,
        )

    @property
    def finished(self) -> bool:
        return self.killed or self.revealed >= len(self.ends)


class FakeSandbox:
    def __init__(self, scripted: dict[str, Script] | None = None) -> None:
        self._scripted = dict(scripted or {})
        self._runs: dict[str, _Run] = {}
        self.inputs: list[tuple[str, bytes]] = []
        self.jobs: list[SandboxJob] = []

    async def submit(self, job: SandboxJob) -> None:
        check_job_limits(job)
        self.jobs.append(job)
        script = self._scripted.get(job.run_id, self._scripted.get("*", ""))
        if isinstance(script, SandboxResult):
            self._runs[job.run_id] = _Run(b"", script, [0], 1)
            return
        chunks = script if isinstance(script, tuple) else (script,)
        data = "".join(chunks).encode()
        truncated = len(data) > MAX_OUTPUT_BYTES
        if truncated:  # coupé sur une frontière de caractère
            data = data[:MAX_OUTPUT_BYTES].decode(errors="ignore").encode()
        ends, total = [], 0
        for chunk in chunks:
            total = min(total + len(chunk.encode()), len(data))
            ends.append(total)
        result = SandboxResult(status="done", exit_code=0, duration_ms=1, truncated=truncated)
        revealed = 0 if isinstance(script, tuple) else 1
        self._runs[job.run_id] = _Run(data, result, ends or [0], revealed)

    async def poll(self, run_id: str, offset: int) -> SandboxProgress:
        run = self._runs.get(run_id)
        if run is None:
            raise UnknownRun(run_id)
        if not run.finished:
            run.revealed += 1
        seen = run.ends[run.revealed - 1] if run.revealed else 0
        return SandboxProgress(
            output=run.data[max(offset, 0) : seen].decode(errors="replace"),
            next_offset=max(offset, seen),
            result=(run.killed_result if run.killed else run.result) if run.finished else None,
        )

    async def cancel(self, run_id: str) -> None:
        run = self._runs.get(run_id)
        if run is not None and not run.finished:
            run.killed = True

    async def write_input(self, run_id: str, data: bytes) -> None:
        run = self._runs.get(run_id)
        if run is None or run.finished:
            raise UnknownRun(run_id)
        if not 0 < len(data) <= MAX_INPUT_CHUNK_BYTES:
            raise ValueError("entrée trop grande")
        self.inputs.append((run_id, data))

    async def healthy(self) -> bool:
        return True
