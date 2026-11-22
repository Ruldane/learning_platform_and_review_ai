"""Réservation du rapport et dossier lu par le responsable d'exploitation."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.oncall_port import REVIEW_GRAPH, SUBJECT, ReviewInput, ReviewScore
from app.core.errors import AppError
from app.core.skills import evidence
from app.db.base import utcnow
from app.db.models.oncall import OncallIncident
from app.features.oncall.repository import IncidentRepository
from app.features.oncall.schemas import OncallReviewStarted
from app.features.oncall.service import OncallService, review_state
from app.features.skills.service import SkillsService


async def launch_report(
    launcher: SessionLauncher,
    user_id: str,
    incident_id: str,
    report: str,
) -> OncallReviewStarted:
    report = report.strip()
    if len(report) < 8:
        raise AppError("incident_report_empty", "Écris d’abord ton rapport d’incident.", 422)

    async def prepare(db: AsyncSession, session_id: str) -> None:
        service = OncallService(db, user_id, None)
        row = await service.repo.require(incident_id)
        if row.proof_recorded or await review_state(db, user_id, row) == "running":
            raise AppError("incident_review_busy", "Un rapport est déjà en cours ou validé.", 409)
        if not await service.repaired(row):
            raise AppError(
                "incident_repair_required",
                "Fais passer le diagnostic sur le service actuel.",
                409,
            )
        observations = [event for event in row.events if event["id"] in row.observed_events]
        if not observations:
            raise AppError(
                "incident_observation_required", "Consulte un événement du journal.", 409
            )
        await service.repo.claim(row)
        row.report, row.review_session_id, row.verdict = report, session_id, None
        row.review_context = {
            "kind": row.kind,
            "minute": row.minute,
            "observations": observations,
            "diagnostic_hash": row.diagnostic_hash,
        }

    session_id = await launcher.start(
        user_id,
        REVIEW_GRAPH,
        {"incident_id": incident_id},
        subject_type=SUBJECT,
        subject_id=incident_id,
        prepare=prepare,
    )
    return OncallReviewStarted(session_id=session_id)


async def _assigned(
    db: AsyncSession,
    user_id: str,
    incident_id: str,
    session_id: str,
) -> OncallIncident:
    row = await IncidentRepository(db, user_id).require(incident_id)
    if row.review_session_id != session_id or row.report is None or row.review_context is None:
        raise AppError("incident_review_stale", "Ce rapport n’est plus celui à évaluer.", 409)
    return row


class AgentOncallStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def read(self, user_id: str, incident_id: str, session_id: str) -> ReviewInput:
        async with self._factory() as db:
            row = await _assigned(db, user_id, incident_id, session_id)
            return ReviewInput.model_validate(
                {
                    **(row.review_context or {}),
                    "report": row.report,
                    "previous": row.verdict,
                }
            )

    async def record(
        self,
        user_id: str,
        incident_id: str,
        session_id: str,
        score: ReviewScore,
    ) -> bool:
        async with self._factory() as db:
            row = await _assigned(db, user_id, incident_id, session_id)
            if row.verdict is not None:
                return row.proof_recorded
            service = OncallService(db, user_id, None)
            await service.repo.claim(row)
            row.verdict = score.model_dump()
            same_diagnostic = (row.review_context or {}).get(
                "diagnostic_hash"
            ) == row.diagnostic_hash
            if score.accepted and same_diagnostic and await service.repaired(row):
                proof = evidence(
                    "ide", row.ide_session_id, "Simulation d’astreinte réussie", utcnow()
                )
                await SkillsService(db, user_id).raise_levels(
                    ["Diagnostic d’incident"], "en_cours", proof
                )
                row.proof_recorded = True
            await db.commit()
            return row.proof_recorded
