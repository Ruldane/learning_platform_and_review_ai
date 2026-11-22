"""Réutilise les énoncés publics du quiz d'origine et fige chaque résultat."""

from difflib import SequenceMatcher

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.skill_transfer_port import (
    TransferAssessment,
    TransferContext,
    TransferExercise,
)
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.base import utcnow
from app.db.models.skill_transfer import SkillTransfer
from app.features.quiz.service.quizzes import get_quiz
from app.features.skill_transfer.repository import Transfers


def _phase(row: SkillTransfer, session_id: str) -> None:
    if row.session_id != session_id:
        raise AppError("skill_transfer_changed", "Ce contrôle n’a plus cette session active.", 409)


async def _previous(repo: Transfers, row: SkillTransfer) -> tuple[str, ...]:
    prompts = await repo.prior_prompts(row.skill_id, row.id)
    ref = row.proof.get("ref_id")
    if row.proof.get("kind") != "quiz" or not isinstance(ref, str):
        return prompts
    try:
        source = await get_quiz(repo.session, repo.user_id, ref)
    except AppError as error:
        if error.code != "quiz_not_found":
            raise
        return prompts
    return (*prompts, *(question.prompt for question in source.questions))


def _require_novel(prompt: str, previous: tuple[str, ...]) -> None:
    comparison = normalize_skill_name(prompt)
    if any(
        SequenceMatcher(None, comparison, normalize_skill_name(old)).ratio() >= 0.85
        for old in previous
    ):
        raise AppError("skill_transfer_reused", "L’énoncé reprend un exercice précédent.", 409)


class AgentSkillTransferStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def context(self, user_id: str, transfer_id: str, session_id: str) -> TransferContext:
        async with self._factory() as db:
            repo = Transfers(db, user_id)
            row = await repo.get_owned(transfer_id)
            _phase(row, session_id)
            exercise = TransferExercise.model_validate(row.exercise) if row.exercise else None
            return TransferContext(
                stage=row.stage,
                skill=str(row.proof["skill_name"]),
                proof_kind=str(row.proof["kind"]),
                proof_label=str(row.proof["label"]),
                previous_prompts=(await _previous(repo, row)) if row.stage == "preparing" else (),
                exercise=exercise,
                answer=row.answer,
            )

    async def publish(
        self, user_id: str, transfer_id: str, session_id: str, exercise: TransferExercise
    ) -> None:
        async with self._factory.begin() as db:
            await db.execute(text("BEGIN IMMEDIATE"))
            repo = Transfers(db, user_id)
            row = await repo.get_owned(transfer_id)
            _phase(row, session_id)
            if row.stage == "preparing":
                await_novel = await _previous(repo, row)
                _require_novel(exercise.prompt, await_novel)
                row.exercise = exercise.model_dump()
                row.stage = "ready"

    async def assess(
        self, user_id: str, transfer_id: str, session_id: str, assessment: TransferAssessment
    ) -> None:
        async with self._factory.begin() as db:
            row = await Transfers(db, user_id).get_owned(transfer_id)
            _phase(row, session_id)
            if row.stage == "grading":
                row.assessment = assessment.model_dump()
                row.assessed_at = utcnow()
                row.stage = "complete"
