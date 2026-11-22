"""Défi d’une seule fiche due associé au compte, au consentement et à sa discussion."""

from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import McpIdentity
from app.core.clock import user_zone
from app.core.errors import AppError
from app.db.models.message_review import TelegramReviewChallenge, TelegramReviewSettings
from app.features.message_review.preferences import FEATURE
from app.features.message_review.repository import ChallengeRepository, ConsentRepository
from app.features.message_review.schemas import (
    TelegramAnswerIn,
    TelegramAnswerOut,
    TelegramChallenge,
    TelegramClaimOut,
    TelegramRevealOut,
)
from app.features.quiz.service import cards
from app.features.quiz.service.runtime import QuizRuntime
from app.features.settings.service import SettingsService


def _forbidden() -> AppError:
    return AppError(
        "telegram_review_not_authorized",
        "Ce jeton et cette discussion ne sont pas associés à une révision active.",
        403,
    )


class TelegramReviews:
    def __init__(self, db: AsyncSession, quiz: QuizRuntime, actor: McpIdentity) -> None:
        self._db, self._quiz, self._actor = db, quiz, actor
        self._user_id = actor.user_id
        self._challenges = ChallengeRepository(db, actor.user_id)

    async def _consent(self, chat_id: str, *, lock: bool) -> TelegramReviewSettings:
        actor = self._actor
        if actor.mode != "write" or actor.features != frozenset({FEATURE}):
            raise _forbidden()
        prefs = await ConsentRepository(self._db, self._user_id).authorized(
            actor.token_id, chat_id, lock=lock
        )
        if prefs is None:
            raise _forbidden()
        return prefs

    async def _local_now(self) -> datetime:
        settings = await SettingsService(self._db, self._user_id).get()
        return self._quiz.now().astimezone(user_zone(settings.timezone))

    async def claim(self, chat_id: str) -> TelegramClaimOut:
        prefs = await self._consent(chat_id, lock=True)
        local_now = await self._local_now()
        if not prefs.start <= local_now.strftime("%H:%M") < prefs.end:
            return TelegramClaimOut()
        day = local_now.date()
        existing = await self._challenges.for_day(day)
        if existing is not None:
            return await self._existing(existing, prefs.consent_id)
        queue = await cards.due_queue(self._quiz, self._db, self._user_id)
        if not queue.cards:
            return TelegramClaimOut()
        card = queue.cards[0]
        row = await self._challenges.reserve(prefs, day, card.id)
        return TelegramClaimOut(
            challenge=TelegramChallenge(id=row.id, day=day, question=card.front)
        )

    async def _existing(self, row: TelegramReviewChallenge, consent_id: str) -> TelegramClaimOut:
        if row.consent_id != consent_id or row.outcome is not None:
            return TelegramClaimOut()
        try:
            card = await cards.read_due_card(self._quiz, self._db, self._user_id, row.card_id)
        except AppError as error:
            if error.code not in {"card_not_found", "card_not_due"}:
                raise
            return TelegramClaimOut()
        return TelegramClaimOut(
            challenge=TelegramChallenge(id=row.id, day=row.day, question=card.front)
        )

    async def _owned(self, challenge_id: str, consent_id: str) -> TelegramReviewChallenge:
        row = await self._challenges.get(challenge_id)
        if row is None or row.consent_id != consent_id:
            raise AppError("telegram_challenge_not_found", "Défi introuvable.", 404)
        return row

    async def _check_day(self, day: date) -> None:
        if day != (await self._local_now()).date():
            raise AppError("telegram_challenge_expired", "Le défi du jour est expiré.", 409)

    async def reveal(self, challenge_id: str, chat_id: str) -> TelegramRevealOut:
        prefs = await self._consent(chat_id, lock=False)
        row = await self._owned(challenge_id, prefs.consent_id)
        await self._check_day(row.day)
        card = await cards.read_due_card(self._quiz, self._db, self._user_id, row.card_id)
        return TelegramRevealOut(answer=card.back)

    async def answer(self, challenge_id: str, body: TelegramAnswerIn) -> TelegramAnswerOut:
        prefs = await self._consent(body.chat_id, lock=True)
        row = await self._owned(challenge_id, prefs.consent_id)
        if row.outcome is not None:
            if row.rating != body.result:
                raise AppError("telegram_already_rated", "Ce défi a déjà reçu un avis.", 409)
            return TelegramAnswerOut.model_validate(row.outcome)
        await self._check_day(row.day)
        review = await cards.review_in_session(
            self._quiz, self._db, self._user_id, row.card_id, body.result == "ok"
        )
        outcome = TelegramAnswerOut(step=review.step, due_date=review.due_date)
        row.rating, row.outcome = body.result, outcome.model_dump(mode="json")
        await self._db.commit()
        await cards.reflect_review(self._quiz, self._user_id, review)
        return outcome
