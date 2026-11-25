"""On-call journey, in simulated time and on behalf of a single account."""

import secrets
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.oncall_port import ReviewScore
from app.core.caller import Caller
from app.core.errors import AppError
from app.db.base import new_id
from app.db.models.oncall import OncallIncident
from app.features.ide.service import IdeService
from app.features.oncall.repository import IncidentRepository, diagnostic_in_progress
from app.features.oncall.scenarios import (
    FIXTURES,
    KINDS,
    MAX_MINUTE,
    SOURCE,
    ScenarioKind,
    observation,
    project_files,
)
from app.features.oncall.schemas import (
    DiagnosticState,
    DiagnosticView,
    IncidentCreate,
    IncidentEvent,
    IncidentSummary,
    IncidentView,
)
from app.features.oncall.service import diagnostic
from app.features.sessions.service import session_facts
from app.providers.sandbox.base import CodeSandbox, UnknownRun


def _summary(row: OncallIncident) -> IncidentSummary:
    kind = cast(ScenarioKind, row.kind)
    return IncidentSummary(
        id=row.id,
        kind=kind,
        title=FIXTURES[kind].title,
        seed=row.seed,
        minute=row.minute,
        alerted=row.minute >= row.alert_at,
        ide_session_id=row.ide_session_id,
        proof_recorded=row.proof_recorded,
    )


def sandbox_unavailable() -> AppError:
    return AppError("sandbox_unavailable", "The sandbox is unavailable.", 503)


async def review_state(
    db: AsyncSession, user_id: str, row: OncallIncident
) -> Literal["idle", "running", "failed", "complete"]:
    if row.verdict is not None:
        return "complete"
    if row.review_session_id is None:
        return "idle"
    session = await session_facts(db, user_id, row.review_session_id)
    return (
        "running"
        if session and session.status in {"running", "waiting_user", "paused"}
        else "failed"
    )


class OncallService:
    def __init__(self, db: AsyncSession, user_id: str, sandbox: CodeSandbox | None) -> None:
        self.db, self.user_id = db, user_id
        self.repo = IncidentRepository(db, user_id)
        self.ide = IdeService(db, user_id, sandbox, Caller("app", "astreinte"))
        self._sandbox = sandbox

    async def list(self) -> list[IncidentSummary]:
        return [_summary(row) for row in await self.repo.recent()]

    async def create(self, draft: IncidentCreate) -> IncidentView:
        seed = draft.seed if draft.seed is not None else secrets.randbelow(1_000_000)
        kind = draft.kind or KINDS[seed % len(KINDS)]
        session = await self.ide.open_session(title=f"On-call · {FIXTURES[kind].title}")
        await self.ide.save_files(session.id, project_files(kind), entry=SOURCE)
        row = await self.repo.add(
            kind=kind, seed=seed, alert_at=2 + seed % 3, ide_session_id=session.id
        )
        return await self.view(row)

    async def advance(self, incident_id: str) -> IncidentView:
        row = await self.repo.require(incident_id)
        if row.minute < MAX_MINUTE:
            await self.repo.claim(row)
            row.minute += 1
            event = observation(
                cast(ScenarioKind, row.kind),
                row.seed,
                row.minute,
                row.alert_at,
                repaired=await self.repaired(row),
            )
            row.events = [*row.events, event][-30:]
        return await self.view(row)

    async def observe(self, incident_id: str, event_id: str) -> IncidentView:
        row = await self.repo.require(incident_id)
        if all(event["id"] != event_id for event in row.events):
            raise AppError("incident_event_not_found", "Event not found.", 404)
        if event_id not in row.observed_events:
            await self.repo.claim(row)
            row.observed_events = [*row.observed_events, event_id][-30:]
        return await self.view(row)

    async def _project_files(self, row: OncallIncident) -> dict[str, str]:
        project = await self.ide.get_session(row.ide_session_id)
        return project.files

    async def repaired(self, row: OncallIncident) -> bool:
        if row.diagnostic_state != "passed" or row.diagnostic_hash is None:
            return False
        files = await self._project_files(row)
        return SOURCE in files and diagnostic.project_fingerprint(files) == row.diagnostic_hash

    async def view(self, row: OncallIncident) -> IncidentView:
        state = cast(DiagnosticState, row.diagnostic_state)
        if state == "passed" and not await self.repaired(row):
            state = "stale"
        return IncidentView(
            **_summary(row).model_dump(),
            events=[IncidentEvent.model_validate(item) for item in row.events],
            observed_events=list(row.observed_events),
            diagnostic=DiagnosticView(state=state, run_id=row.diagnostic_run_id),
            report=row.report,
            review_session_id=row.review_session_id,
            review_state=await review_state(self.db, self.user_id, row),
            verdict=ReviewScore.model_validate(row.verdict) if row.verdict is not None else None,
        )

    async def get(self, incident_id: str) -> IncidentView:
        row = await self.repo.require(incident_id)
        try:
            await self._settle(row)
        except AppError as exc:
            if exc.code != "incident_changed":
                raise
            row = await self.repo.require(incident_id)
        return await self.view(row)

    async def _settle(self, row: OncallIncident) -> None:
        if (
            row.diagnostic_state != "running"
            or row.diagnostic_run_id is None
            or self._sandbox is None
        ):
            return
        try:
            progress = await self._sandbox.poll(row.diagnostic_run_id, 0)
        except UnknownRun:
            success = False
        except OSError:
            return
        else:
            if progress.result is None:
                return
            success = diagnostic.passed(progress)
        await self.repo.claim(row)
        diagnostic.record(row, "passed" if success else "failed")

    async def diagnose(self, incident_id: str) -> DiagnosticView:
        row = await self.repo.require(incident_id)
        if row.minute < row.alert_at:
            raise AppError("before_alert", "Wait for the simulated alert before diagnosing.", 409)
        if self._sandbox is None:
            raise sandbox_unavailable()
        active = await self.repo.running_diagnostic()
        if active is not None:
            await self._settle(active)
            if active.diagnostic_state == "running":
                if active.id == row.id:
                    return DiagnosticView(state="running", run_id=active.diagnostic_run_id)
                raise diagnostic_in_progress()
        files = await self._project_files(row)
        if SOURCE not in files:
            raise AppError("incident_source_missing", "The service.py file is missing.", 422)
        run_id = new_id()
        try:
            job = diagnostic.job_for(run_id, files)
            await self.repo.reserve_diagnostic(row, run_id, diagnostic.project_fingerprint(files))
            await self._sandbox.submit(job)
        except ValueError:
            raise AppError(
                "incident_source_invalid",
                "Reduce the number or size of files to leave room for the diagnostic.",
                422,
            ) from None
        except OSError:
            raise sandbox_unavailable() from None
        return DiagnosticView(state="running", run_id=run_id)
