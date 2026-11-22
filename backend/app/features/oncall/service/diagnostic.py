"""Vérifie la copie courante du service dans le bac, sur des cas générés."""

import json

from app.db.models.oncall import OncallIncident
from app.features.ide.service import file_hash
from app.features.oncall.scenarios import REFERENCE, SIZES
from app.features.oncall.service.controller import CONTROLLER, ENTRY, SERVICE_WORKER, WORKER
from app.providers.sandbox.base import SandboxJob, SandboxProgress, check_job_limits

TIMEOUT_S = 8


def project_fingerprint(files: dict[str, str]) -> str:
    return file_hash(json.dumps(files, sort_keys=True))


def job_for(run_id: str, project: dict[str, str]) -> SandboxJob:
    roots = {name.partition("/")[0] for name in project}
    controller_dir = "_tremplin_oncall"
    while controller_dir in roots:
        controller_dir += "_"
    entry = f"{controller_dir}/{ENTRY}"
    job = SandboxJob(
        run_id=run_id,
        files={**project, entry: CONTROLLER, f"{controller_dir}/{WORKER}": SERVICE_WORKER},
        entry=entry,
        kind="run",
        timeout_s=TIMEOUT_S,
    )
    check_job_limits(job)
    return job


def passed(progress: SandboxProgress) -> bool:
    result = progress.result
    if result is None or result.status != "done" or result.exit_code != 0 or result.truncated:
        return False
    try:
        data = json.loads(progress.output)
    except (ValueError, RecursionError):
        return False
    checks = data.get("checks") if isinstance(data, dict) else None
    if not isinstance(checks, list) or len(checks) != len(SIZES):
        return False
    return all(_check(check, size) for check, size in zip(checks, SIZES, strict=True))


def _check(check: object, size: int) -> bool:
    if not isinstance(check, dict):
        return False
    latency = check.get("latency_ms")
    return (
        type(latency) is int
        and 0 <= latency <= 250
        and type(check.get("pending")) is int
        and check["pending"] == 0
        and type(check.get("accepted")) is int
        and check["accepted"] == size
        and check.get("note") == REFERENCE
    )


def record(row: OncallIncident, result: str) -> None:
    row.diagnostic_state = result
    row.events = [
        *row.events,
        {
            "id": f"diagnostic-{row.version}",
            "minute": row.minute,
            "kind": "diagnostic",
            "metric": row.kind,
            "value": int(result == "passed"),
        },
    ][-30:]
