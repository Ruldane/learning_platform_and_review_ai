"""Doubles des exécutions IDE et de l'astreinte, sans code exécuté."""

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agents.nodes.professor.prompt import AGENT as PROFESSOR_AGENT
from app.providers.sandbox.base import SandboxJob, SandboxProgress, SandboxResult
from app.providers.sandbox.fake import FakeSandbox

REVIEW = json.dumps(
    {
        "diagnosis": 4,
        "evidence": 4,
        "correction": 4,
        "prevention": 4,
        "feedback": "La file a été rétablie et le rapport explique la prévention.",
    }
)
TEACHER = json.dumps(
    {
        "kind": "explanation",
        "path": "main.py",
        "start_line": 1,
        "text": "Relis le premier appel dans ce fichier.",
    }
)
IDE_SCRIPTS = {"oncall_reviewer": [REVIEW], PROFESSOR_AGENT: [TEACHER]}
_TERMINAL_INPUT = b"echo tremplin-recette\n"
_TERMINAL_OUTPUT = b"tremplin-recette\n"


class _OncallSandbox(FakeSandbox):
    def __init__(self) -> None:
        super().__init__()
        self._terminals: dict[str, SandboxResult | None] = {}

    async def submit(self, job: SandboxJob) -> None:
        service = job.files.get("service.py", "")
        diagnostic = job.entry.endswith("/diagnostic.py")
        if job.kind == "terminal":
            self._scripted[job.run_id] = ("", "")
        elif diagnostic and "QUEUE_CAPACITY = 12" in service:
            self._scripted[job.run_id] = json.dumps(
                {
                    "checks": [
                        {
                            "latency_ms": 180,
                            "pending": 0,
                            "accepted": size,
                            "note": "routine fictive disponible",
                        }
                        for size in (3, 7, 11)
                    ]
                }
            )
        elif diagnostic:
            self._scripted[job.run_id] = SandboxResult("done", 1, 1, False)
        await super().submit(job)
        if job.kind == "terminal":
            self._terminals[job.run_id] = None

    async def poll(self, run_id: str, offset: int) -> SandboxProgress:
        if run_id not in self._terminals:
            return await super().poll(run_id, offset)
        output = _TERMINAL_OUTPUT if (run_id, _TERMINAL_INPUT) in self.inputs else b""
        return SandboxProgress(
            output=output[offset:].decode(),
            next_offset=max(offset, len(output)),
            result=self._terminals[run_id],
        )

    async def cancel(self, run_id: str) -> None:
        await super().cancel(run_id)
        if run_id in self._terminals:
            self._terminals[run_id] = SandboxResult("killed", None, 1, False)


def install_sandbox(app: FastAPI) -> None:
    lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def with_sandbox(application: FastAPI):
        async with lifespan(application):
            application.state.providers.sandbox = _OncallSandbox()
            yield

    app.router.lifespan_context = with_sandbox
