"""Probe of submitted files and bounded check of functional results."""

import asyncio
import json
from contextlib import suppress
from typing import Literal

from app.agents.tools.boss_port import BossCheck, BossDiagnostic
from app.core.errors import AppError
from app.providers.sandbox.base import (
    CodeSandbox,
    SandboxJob,
    SandboxProgress,
    UnknownRun,
    check_job_limits,
)

# Generated data, kept on the controller side. The order does not depend on sorting ids.
_CASES = (
    ("Empty batch", (), ()),
    ("Urgent first", (("D-1", False), ("D-2", True)), ("D-2", "D-1")),
    (
        "Urgent requests in order of arrival",
        (("D-3", True), ("D-4", True), ("D-5", False)),
        ("D-3", "D-4", "D-5"),
    ),
    (
        "Mixed priorities and intact list",
        (("D-8", False), ("D-6", False), ("D-7", True), ("D-9", False)),
        ("D-7", "D-8", "D-6", "D-9"),
    ),
)
_DATA = json.dumps(
    [
        # `urgente` and `planifier` below serve files started before the switch to English.
        [{"id": key, "urgent": urgent, "urgente": urgent} for key, urgent in values]
        for _, values, _ in _CASES
    ]
)
_CONTROLLER = f"""import json
import os
import subprocess
import sys
from pathlib import Path

worker = Path(__file__).with_name("worker.py")
read_fd, write_fd = os.pipe()
with os.fdopen(read_fd, "rb") as stream:
    try:
        child = subprocess.Popen(
            [sys.executable, str(worker), str(write_fd), {_DATA!r}],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, pass_fds=(write_fd,),
        )
    finally:
        os.close(write_fd)
    result = stream.read(4097)
if child.wait() != 0 or len(result) > 4096:
    raise SystemExit(1)
print(json.dumps({{"checks": json.loads(result)}}))
"""
_WORKER = """import copy
import json
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

fd = int(sys.argv[1])
os.set_inheritable(fd, False)
cases = json.loads(sys.argv[2])
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
spec = spec_from_file_location("service", root / "service.py")
service = module_from_spec(spec)
sys.modules[spec.name] = service
spec.loader.exec_module(service)

checks = []
for rows in cases:
    source = copy.deepcopy(rows)
    try:
        schedule = getattr(service, "schedule", None) or service.planifier
        ordered = schedule(rows)
        checks.append({"ordered": ordered, "intact": rows == source})
    except Exception:
        checks.append({"ordered": None, "intact": False})
with os.fdopen(fd, "w") as output:
    json.dump(checks, output)
"""


def job_for(run_id: str, files: dict[str, str]) -> SandboxJob:
    occupied = {name.partition("/")[0] for name in files}
    area = "_tremplin_boss"
    while area in occupied:
        area += "_"
    entry = f"{area}/diagnostic.py"
    job = SandboxJob(
        run_id, {**files, entry: _CONTROLLER, f"{area}/worker.py": _WORKER}, entry, "run", 8
    )
    try:
        check_job_limits(job)
    except ValueError:
        raise AppError(
            "boss_project_too_large",
            "Shrink the files to leave room for the diagnostic.",
            422,
        ) from None
    return job


def _failed(outcome: Literal["failed", "timeout"]) -> BossDiagnostic:
    return BossDiagnostic(
        outcome=outcome, checks=[BossCheck(label=label, passed=False) for label, _, _ in _CASES]
    )


def _passed_case(found: object, expected: tuple[str, ...]) -> bool:
    return (
        isinstance(found, dict)
        and found.get("ordered") == list(expected)
        and found.get("intact") is True
    )


def evaluate(progress: SandboxProgress) -> BossDiagnostic:
    result = progress.result
    if result is None or result.status == "timeout":
        return _failed("timeout")
    if result.status != "done" or result.exit_code != 0 or result.truncated:
        return _failed("failed")
    try:
        message = json.loads(progress.output)
    except (ValueError, RecursionError):
        return _failed("failed")
    checks = message.get("checks") if isinstance(message, dict) else None
    if not isinstance(checks, list) or len(checks) != len(_CASES):
        return _failed("failed")
    return BossDiagnostic(
        outcome="completed",
        checks=[
            BossCheck(label=label, passed=_passed_case(found, ordered))
            for found, (label, _, ordered) in zip(checks, _CASES, strict=True)
        ],
    )


async def run(sandbox: CodeSandbox, job: SandboxJob) -> BossDiagnostic:
    try:
        async with asyncio.timeout(30):
            try:
                progress = await sandbox.poll(job.run_id, 0)
            except UnknownRun:
                await sandbox.submit(job)
                progress = await sandbox.poll(job.run_id, 0)
            while progress.result is None:
                await asyncio.sleep(0.2)
                progress = await sandbox.poll(job.run_id, 0)
    except TimeoutError:
        with suppress(OSError, TimeoutError):
            async with asyncio.timeout(1):
                await sandbox.cancel(job.run_id)
        return _failed("timeout")
    except (ValueError, OSError, UnknownRun):
        raise AppError(
            "boss_sandbox_unavailable", "The sandbox is not responding for the Boss.", 503
        ) from None
    return evaluate(progress)
