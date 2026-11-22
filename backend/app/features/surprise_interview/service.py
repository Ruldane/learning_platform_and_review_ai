"""Invitation hebdomadaire et garde du transport Nod."""

from datetime import date
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.core.caller import McpIdentity
from app.core.clock import user_zone
from app.core.errors import AppError
from app.db.models.surprise_interview import SurpriseInvitation, SurpriseSettings
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.telegram_interviews import (
    read_telegram_interview,
    start_telegram_interview,
)
from app.features.message_review.service import TelegramConnection, telegram_connection
from app.features.sessions.service import SessionFacts, session_facts
from app.features.surprise_interview.preferences import FEATURE
from app.features.surprise_interview.repository import InvitationRepository, SettingsRepository
from app.features.surprise_interview.schedule import due_week
from app.features.surprise_interview.schemas import (
    SurpriseAnswerIn,
    SurpriseAnswerOut,
    SurpriseDebrief,
    SurpriseInvitationOut,
    SurpriseInviteOut,
    SurpriseQuestion,
    SurpriseStartOut,
    SurpriseStateOut,
)


def _unbound() -> AppError:
    return AppError(
        "surprise_telegram_not_authorized",
        "Ce jeton et cette discussion ne sont pas associés à un entretien surprise actif.",
        403,
    )


def _pending(facts: SessionFacts | None) -> SurpriseQuestion | None:
    if facts is None or facts.status != "waiting_user" or facts.pending is None:
        return None
    prompt = facts.pending
    key, text = prompt.get("interrupt_id"), prompt.get("question")
    if (
        prompt.get("kind") != "interview_answer"
        or not isinstance(key, str)
        or not isinstance(text, str)
    ):
        return None
    return SurpriseQuestion(id=key, text=text)


def _stale_question() -> AppError:
    return AppError("surprise_question_changed", "Cette question n’attend plus de réponse.", 409)


class SurpriseInterviews:
    def __init__(
        self, db: AsyncSession, rt: ApplicationsRuntime, actor: McpIdentity, runner: SessionRunner
    ) -> None:
        self.db, self.rt, self.actor, self.runner = db, rt, actor, runner
        self.user = actor.user_id
        self.invitations = InvitationRepository(db, self.user)

    async def consent(
        self, chat_id: str, *, lock: bool
    ) -> tuple[SurpriseSettings, TelegramConnection]:
        if self.actor.mode != "write" or self.actor.features != frozenset({FEATURE}):
            raise _unbound()
        prefs = await SettingsRepository(self.db, self.user).authorized(
            self.actor.token_id, lock=lock
        )
        link = await telegram_connection(self.db, self.user)
        if (
            not prefs
            or not link
            or prefs.chat_consent_id != link.consent_id
            or chat_id != link.chat_id
        ):
            raise _unbound()
        return prefs, link

    async def invite(self, chat_id: str) -> SurpriseInviteOut:
        prefs, link = await self.consent(chat_id, lock=True)
        due = due_week(link, self.rt.now(), prefs.consent_id)
        if due is None:
            return SurpriseInviteOut()
        week, day = due
        row = await self.invitations.for_week(week)
        if row is None:
            row = await self.invitations.add(
                week=week, day=day, consent_id=prefs.consent_id, role=prefs.role
            )
        if row.consent_id != prefs.consent_id:
            return SurpriseInviteOut()
        return SurpriseInviteOut(invitation=SurpriseInvitationOut(id=row.id, day=row.day))

    async def owned(self, consent: SurpriseSettings, invitation_id: str) -> SurpriseInvitation:
        row = await self.invitations.get(invitation_id)
        if row is None or row.consent_id != consent.consent_id:
            raise AppError("surprise_invitation_not_found", "Invitation introuvable.", 404)
        return row

    def today(self, link: TelegramConnection) -> date:
        return self.rt.now().astimezone(user_zone(link.timezone)).date()

    async def accept(self, invitation_id: str, chat_id: str) -> SurpriseStartOut:
        prefs, _ = await self.consent(chat_id, lock=False)
        invitation = await self.owned(prefs, invitation_id)

        async def check(db: AsyncSession) -> None:
            service = SurpriseInterviews(db, self.rt, self.actor, self.runner)
            consent, link = await service.consent(chat_id, lock=True)
            fresh = await service.owned(consent, invitation_id)
            if fresh.day != service.today(link):
                raise AppError("surprise_invitation_expired", "Cette invitation a expiré.", 409)

        started = await start_telegram_interview(
            self.rt, self.user, invitation.id, invitation.role, check
        )
        return SurpriseStartOut(interview_id=started.interview_id, session_id=started.session_id)

    async def state(self, invitation_id: str, chat_id: str) -> SurpriseStateOut:
        prefs, _ = await self.consent(chat_id, lock=False)
        invitation = await self.owned(prefs, invitation_id)
        interview = await read_telegram_interview(self.db, self.user, invitation.id)
        if interview is None:
            return SurpriseStateOut(status="invited")
        if interview.status == "done" and interview.debrief is not None:
            result = SurpriseDebrief.model_validate(interview.debrief.model_dump())
            return SurpriseStateOut(status="done", debrief=result)
        if interview.status == "stopped":
            return SurpriseStateOut(status="stopped")
        facts = await session_facts(self.db, self.user, interview.session_id)
        if question := _pending(facts):
            return SurpriseStateOut(status="question", question=question)
        if (
            facts is None
            or interview.status != "running"
            or facts.status in {"failed", "cancelled"}
        ):
            return SurpriseStateOut(status="failed")
        return SurpriseStateOut(status="preparing")

    async def answer(self, invitation_id: str, body: SurpriseAnswerIn) -> SurpriseAnswerOut:
        async with self.rt.locks.get(self.user, "surprise_interview_answer"):
            return await self._answer(invitation_id, body)

    async def _answer(self, invitation_id: str, body: SurpriseAnswerIn) -> SurpriseAnswerOut:
        prefs, _ = await self.consent(body.chat_id, lock=True)
        invitation = await self.owned(prefs, invitation_id)
        interview = await read_telegram_interview(self.db, self.user, invitation.id)
        if interview is None:
            raise _stale_question()
        current = _pending(await session_facts(self.db, self.user, interview.session_id))
        same_question = current is not None and current.id == body.question_id
        receipt = {
            "message_id": body.message_id,
            "digest": sha256(body.answer.encode()).hexdigest(),
        }
        answers = invitation.answers
        previous = answers.get(body.question_id)
        if previous is not None:
            if any(previous.get(key) != value for key, value in receipt.items()):
                raise _stale_question()
            if not same_question:
                if previous.get("received") is True:
                    return SurpriseAnswerOut()
                raise _stale_question()
        else:
            if not same_question:
                raise _stale_question()
            if any(r["message_id"] == body.message_id for r in answers.values()):
                raise _stale_question()
            answers = {**answers, body.question_id: receipt}
            await self.invitations.save_receipts(invitation_id, answers)
        await self.db.commit()
        try:
            await self.runner.resume(
                self.user,
                interview.session_id,
                body.question_id,
                {"answers": {"answer": body.answer}},
            )
        except AppError as error:
            if error.code == "stale_interrupt":
                raise _stale_question() from error
            raise
        if previous is None or previous.get("received") is not True:
            answers = {**answers, body.question_id: {**receipt, "received": True}}
            await self.invitations.save_receipts(invitation_id, answers)
            await self.db.commit()
        return SurpriseAnswerOut()
