"""Schedule, re-read and launch a check on the requested local day."""

import json
from datetime import date, datetime
from hashlib import sha256
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.skill_transfer_port import (
    TRANSFER_GRAPH,
    TransferAssessment,
    TransferExercise,
)
from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.core.skills import Evidence
from app.db.models.skill_transfer import SkillTransfer
from app.features.sessions.service import session_facts
from app.features.settings.service import SettingsService
from app.features.skill_transfer.repository import Transfers
from app.features.skill_transfer.schemas import (
    AnswerIn,
    AssessmentOut,
    ProofOption,
    TransferExerciseOut,
    TransferIn,
    TransferOut,
    TransferStarted,
)

Retry = Literal["prepare", "answer"]
_FAILED = frozenset({"cancelled", "expired", "failed"})


def _proof(sid: str, name: str, evidence: Evidence) -> ProofOption:
    identity = json.dumps({"skill_id": sid, **evidence}, sort_keys=True).encode()
    return ProofOption(
        id=sha256(identity).hexdigest(),
        skill_id=sid,
        skill_name=name,
        kind=evidence["kind"],
        label=evidence["label"],
        at=evidence["at"] or None,
    )


async def proofs(db: AsyncSession, user_id: str, skill_id: str | None) -> list[ProofOption]:
    repo = Transfers(db, user_id)
    return [_proof(sid, name, item) for sid, name, item in await repo.proofs(skill_id)]


async def _today(db: AsyncSession, user_id: str, now: datetime) -> date:
    settings = await SettingsService(db, user_id).get()
    return local_today(user_zone(settings.timezone), now)


async def schedule(db: AsyncSession, user_id: str, body: TransferIn, now: datetime) -> TransferOut:
    repo = Transfers(db, user_id)
    await repo.lock_schedule()
    for sid, name, item in await repo.proofs(str(body.skill_id)):
        chosen = _proof(sid, name, item)
        if chosen.id == body.proof_id:
            break
    else:
        raise AppError("skill_transfer_proof_not_found", "Skill evidence not found.", 404)
    today = await _today(repo.session, repo.user_id, now)
    if body.due_on < today:
        raise AppError("skill_transfer_date_past", "Choose today or a future date.", 422)
    snapshot = chosen.model_dump() | {"ref_id": item["ref_id"]}
    row = await repo.schedule(sid, chosen.id, snapshot, body.due_on)
    return await _view(repo, row, today)


async def _retry(repo: Transfers, row: SkillTransfer) -> Retry | None:
    if row.stage not in {"preparing", "grading"}:
        return None
    prior = (
        await session_facts(repo.session, repo.user_id, row.session_id) if row.session_id else None
    )
    if prior is None or prior.status in _FAILED:
        return "prepare" if row.stage == "preparing" else "answer"
    return None


def _assessment(row: SkillTransfer) -> AssessmentOut | None:
    if row.stage != "complete" or row.assessment is None or row.assessed_at is None:
        return None
    grade = TransferAssessment.model_validate(row.assessment)
    exercise = TransferExercise.model_validate(row.exercise)
    return AssessmentOut(
        verdict="demonstrated" if all(grade.met) else "needs_review",
        criteria=exercise.criteria,
        met=grade.met,
        feedback=grade.feedback,
        assessed_at=row.assessed_at,
    )


async def _view(repo: Transfers, row: SkillTransfer, today: date) -> TransferOut:
    retry = await _retry(repo, row)
    return TransferOut(
        id=row.id,
        proof=ProofOption.model_validate(row.proof),
        due_on=row.due_on,
        available=row.due_on <= today,
        stage=row.stage,
        retry=retry,
        session_id=row.session_id,
        exercise=TransferExerciseOut.model_validate(row.exercise) if row.exercise else None,
        answer=row.answer,
        assessment=_assessment(row),
    )


async def history(
    db: AsyncSession, user_id: str, skill_id: str | None, now: datetime
) -> list[TransferOut]:
    repo = Transfers(db, user_id)
    today = await _today(repo.session, repo.user_id, now)
    return [await _view(repo, row, today) for row in await repo.history(skill_id)]


async def read(db: AsyncSession, user_id: str, transfer_id: str, now: datetime) -> TransferOut:
    repo = Transfers(db, user_id)
    row = await repo.get_owned(transfer_id)
    return await _view(repo, row, await _today(repo.session, repo.user_id, now))


async def require_preparation(repo: Transfers, row: SkillTransfer, now: datetime) -> None:
    if row.due_on > await _today(repo.session, repo.user_id, now):
        raise AppError("skill_transfer_not_due", "This check is not due yet.", 409)
    if row.stage != "scheduled" and await _retry(repo, row) != "prepare":
        raise AppError(
            "skill_transfer_already_started", "This check is already ready or in progress.", 409
        )


async def _require_answer(repo: Transfers, row: SkillTransfer, answer: str) -> None:
    if row.stage == "ready":
        return
    if await _retry(repo, row) == "answer" and row.answer == answer:
        return
    raise AppError("skill_transfer_answer_locked", "This check is not accepting answers.", 409)


async def launch(
    launcher: SessionLauncher,
    user_id: str,
    transfer_id: str,
    now: datetime,
    answer: AnswerIn | None = None,
) -> TransferStarted:
    async def reserve(db: AsyncSession, session_id: str) -> None:
        repo = Transfers(db, user_id)
        row = await repo.get_owned(transfer_id)
        if answer is None:
            await require_preparation(repo, row, now)
            row.stage = "preparing"
        else:
            await _require_answer(repo, row, answer.answer)
            row.answer = answer.answer
            row.stage = "grading"
        row.session_id = session_id

    session_id = await launcher.start(
        user_id,
        TRANSFER_GRAPH,
        {"transfer_id": transfer_id},
        subject_type=TRANSFER_GRAPH,
        subject_id=transfer_id,
        prepare=reserve,
    )
    return TransferStarted(transfer_id=transfer_id, session_id=session_id)
