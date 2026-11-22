"""Ouverture du tableau, remise de la version sélectionnée et critique durable."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.repositories import SessionRepository
from app.agents.tools.system_design_port import (
    SystemDesignContext,
    SystemDesignReview,
    SystemDesignSubmission,
)
from app.core.errors import AppError
from app.core.skills import evidence
from app.db.base import new_id
from app.db.models.applications import Interview
from app.features.applications.repository_interviews import InterviewRepository
from app.features.applications.schemas_interviews import InterviewStartOut
from app.features.applications.schemas_system_design import DesignState, DesignSubject
from app.features.applications.service.design_scene import describe_scene
from app.features.applications.service.interviews import GRAPH, SUBJECT, interview_lock, settle
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.learning.service.design_boards import create_design_board, read_design_board
from app.features.skills.service import SkillsService

SKILL = "Conception de systèmes"
SUBJECT_CARD = DesignSubject(
    title="Concevoir un service de rappels",
    situation=(
        "Des équipes programment des rappels qui sont ensuite distribués à leurs membres. "
        "Le trafic connaît un pic au début de la journée."
    ),
    requirements=(
        "Accepter et annuler un rappel avant sa distribution.",
        "Absorber 10 000 rappels à remettre dans une même minute.",
        "Reprendre les envois après une panne et limiter les doublons.",
        "Expliquer le compromis retenu entre coût, délai et fiabilité.",
    ),
)


def _missing() -> AppError:
    return AppError("design_not_found", "Entretien d’architecture introuvable.", 404)


async def _row(db: AsyncSession, user_id: str, interview_id: str) -> Interview:
    row = await InterviewRepository(db, user_id).get_fresh(interview_id)
    if row is None or row.system_design is None:
        raise _missing()
    return row


async def start(rt: ApplicationsRuntime, user_id: str) -> InterviewStartOut:
    async with interview_lock(rt, user_id):
        async with rt.session_factory() as db:
            await settle(db, user_id)
            existing = await InterviewRepository(db, user_id).recent_design()
            if existing is not None and existing.status == "running":
                return InterviewStartOut(interview_id=existing.id, session_id=existing.session_id)

        interview_id = new_id()

        async def prepare(db: AsyncSession, session_id: str) -> None:
            await InterviewRepository(db, user_id).add(
                id=interview_id,
                session_id=session_id,
                role=SUBJECT_CARD.title,
                mode="case",
                duration_min=30,
                language="fr",
                status="running",
                system_design={"subject": SUBJECT_CARD.model_dump(mode="json")},
            )
            await create_design_board(db, user_id, interview_id, session_id)

        session_id = await rt.launcher.start(
            user_id,
            GRAPH,
            {"interview_id": interview_id, "system_design": True},
            subject_type=SUBJECT,
            subject_id=interview_id,
            prepare=prepare,
        )
        return InterviewStartOut(interview_id=interview_id, session_id=session_id)


async def _view(db: AsyncSession, user_id: str, row: Interview) -> DesignState:
    data = row.system_design or {}
    version_id = data.get("version_id")
    board = await read_design_board(db, user_id, row.id, version_id)
    return DesignState.model_validate(
        {
            "id": row.id,
            "session_id": row.session_id,
            "status": row.status,
            "subject": data["subject"],
            "board": board,
            "version_id": version_id,
            "defense": data.get("defense"),
            "review": data.get("review"),
            "proof_saved": data.get("proof_saved", False),
        }
    )


async def read(
    rt: ApplicationsRuntime, user_id: str, interview_id: str | None = None
) -> DesignState | None:
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        await settle(db, user_id)
        row = (
            await _row(db, user_id, interview_id)
            if interview_id is not None
            else await InterviewRepository(db, user_id).recent_design()
        )
        return await _view(db, user_id, row) if row is not None else None


async def _session_row(
    db: AsyncSession, user_id: str, interview_id: str, session_id: str
) -> Interview:
    row = await _row(db, user_id, interview_id)
    if row.session_id != session_id:
        raise _missing()
    return row


async def freeze(
    rt: ApplicationsRuntime,
    user_id: str,
    session_id: str,
    interview_id: str,
    submission: SystemDesignSubmission,
) -> SystemDesignContext:
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        row = await _session_row(db, user_id, interview_id, session_id)
        if row.status != "running":
            raise AppError("design_closed", "Cet entretien d’architecture est terminé.", 409)
        data: dict[str, Any] = dict(row.system_design or {})
        version_id = data.get("version_id") or str(submission.board_id)
        defense = data.get("defense") or submission.defense
        board = await read_design_board(db, user_id, interview_id, version_id)
        diagram = describe_scene(board.scene)
        if "version_id" not in data:
            row.system_design = {**data, "version_id": version_id, "defense": defense}
            await db.commit()
        subject = DesignSubject.model_validate(data["subject"])
        return SystemDesignContext(
            subject.title, subject.situation, subject.requirements, diagram, defense
        )


async def save_review(
    rt: ApplicationsRuntime,
    user_id: str,
    session_id: str,
    interview_id: str,
    review: SystemDesignReview,
) -> None:
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        # Réserver l’écriture SQLite avant de lire l’entretien. Une annulation déjà
        # validée empêche de ranger le verdict et sa preuve dans cette transaction.
        if not await SessionRepository(db, user_id).transition(
            session_id, from_={"running"}, to="running"
        ):
            return
        row = await _session_row(db, user_id, interview_id, session_id)
        if row.status != "running":
            return
        data = row.system_design or {}
        if "version_id" not in data:
            raise AppError("design_missing_submission", "La version remise est introuvable.", 409)
        proof_saved = review.earns_proof
        if proof_saved:
            proof = evidence("system_design", row.id, "Entretien d’architecture réussi", rt.now())
            await SkillsService(db, user_id).raise_levels([SKILL], "en_cours", proof)
        row.status = "done"
        row.system_design = {
            **data,
            "review": review.model_dump(mode="json"),
            "proof_saved": proof_saved,
        }
        await db.commit()
