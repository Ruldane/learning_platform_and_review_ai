"""Bac à sable de test (phase 10) : sortie scriptée, déterministe, sans processus ni disque.

`scripted` associe un `run_id` à une sortie (`str` : le travail finit `done`, code 0) ou à un
résultat (`SandboxResult` : fin sans sortie). La clé `"*"` répond à tout travail non scripté (les
services créent leurs identifiants eux-mêmes). Sans clé ni `"*"` : fin `done`, code 0, sortie vide.
Le travail finit dès le dépôt ; `cancel` le rend `killed`."""

from app.providers.sandbox.base import (
    MAX_OUTPUT_BYTES,
    SandboxJob,
    SandboxProgress,
    SandboxResult,
    UnknownRun,
    check_job_limits,
)


class FakeSandbox:
    def __init__(self, scripted: dict[str, SandboxResult | str] | None = None) -> None:
        self._scripted = dict(scripted or {})
        self._runs: dict[str, tuple[bytes, SandboxResult]] = {}

    async def submit(self, job: SandboxJob) -> None:
        check_job_limits(job)
        script = self._scripted.get(job.run_id, self._scripted.get("*", ""))
        if isinstance(script, SandboxResult):
            self._runs[job.run_id] = (b"", script)
            return
        data = script.encode()
        truncated = len(data) > MAX_OUTPUT_BYTES
        if truncated:  # coupé sur une frontière de caractère
            data = data[:MAX_OUTPUT_BYTES].decode(errors="ignore").encode()
        result = SandboxResult(status="done", exit_code=0, duration_ms=1, truncated=truncated)
        self._runs[job.run_id] = (data, result)

    async def poll(self, run_id: str, offset: int) -> SandboxProgress:
        if run_id not in self._runs:
            raise UnknownRun(run_id)
        data, result = self._runs[run_id]
        return SandboxProgress(
            output=data[max(offset, 0) :].decode(errors="replace"),
            next_offset=max(offset, len(data)),
            result=result,
        )

    async def cancel(self, run_id: str) -> None:
        if run_id in self._runs:
            data, result = self._runs[run_id]
            killed = SandboxResult(
                status="killed",
                exit_code=None,
                duration_ms=result.duration_ms,
                truncated=result.truncated,
            )
            self._runs[run_id] = (data, killed)

    async def healthy(self) -> bool:
        return True
