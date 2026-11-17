"""Tests d'évasion du bac à sable (10.A1) : ils parlent au VRAI conteneur `sandbox` par le volume
d'échange (`SANDBOX_SPOOL_DIR`, `/spool` par défaut). Hors suite normale (marque `sandbox_live`).

Lancer, sur une pile jetable (voir la décision D201) :
`pytest -m sandbox_live tests/sandbox_live -p no:cacheprovider`, en utilisateur 10001 avec
`--group-add 12345` et le volume `sandbox_spool` monté sur `/spool` (comme le back)."""

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from app.providers.sandbox.base import SandboxJob, SandboxResult
from app.providers.sandbox.spool import SpoolSandbox


@dataclass
class Run:
    output: str
    result: SandboxResult

    def json(self) -> Any:
        return json.loads(self.output.strip().splitlines()[-1])


class Bac:
    def __init__(self, sandbox: SpoolSandbox, spool: Path) -> None:
        self.sandbox, self.spool = sandbox, spool

    async def run(
        self,
        code: str,
        *,
        timeout_s: int = 10,
        kind: str = "run",
        files: dict[str, str] | None = None,
        wait: float = 40,
    ) -> Run:
        import asyncio
        import time

        run_id = uuid.uuid4().hex
        files = files or {"main.py": code}
        entry = "main.py" if "main.py" in files else sorted(files)[0]
        job = SandboxJob(run_id, files, entry, kind, timeout_s)  # type: ignore[arg-type]
        await self.sandbox.submit(job)
        output, offset, deadline = "", 0, time.monotonic() + wait
        while time.monotonic() < deadline:
            progress = await self.sandbox.poll(run_id, offset)
            output, offset = output + progress.output, progress.next_offset
            if progress.result is not None:
                return Run(output, progress.result)
            await asyncio.sleep(0.1)
        raise AssertionError(f"le travail {run_id} ne finit pas")

    async def hello(self) -> None:
        run = await self.run("print('ok')")
        assert (run.output, run.result.status, run.result.exit_code) == ("ok\n", "done", 0)


@pytest.fixture
async def bac() -> Bac:
    spool = Path(os.environ.get("SANDBOX_SPOOL_DIR", "/spool"))
    sandbox = SpoolSandbox(spool)
    if not await sandbox.healthy():
        pytest.skip("aucun bac à sable vivant sur " + str(spool))
    return Bac(sandbox, spool)
