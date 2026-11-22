"""Doubles du bac d'astreinte et du responsable d'exploitation, sans code exécuté."""

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.providers.sandbox.base import SandboxJob, SandboxResult
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


class _OncallSandbox(FakeSandbox):
    async def submit(self, job: SandboxJob) -> None:
        service = job.files.get("service.py", "")
        diagnostic = job.entry.endswith("/diagnostic.py")
        if diagnostic and "QUEUE_CAPACITY = 12" in service:
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


def install_sandbox(app: FastAPI) -> None:
    lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def with_sandbox(application: FastAPI):
        async with lifespan(application):
            application.state.providers.sandbox = _OncallSandbox()
            yield

    app.router.lifespan_context = with_sandbox
