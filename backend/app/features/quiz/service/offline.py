from app.core.errors import AppError
from app.features.quiz.offline_repository import OfflineReviewRepository
from app.features.quiz.schemas import ReviewOut, ReviewReceiptIn
from app.features.quiz.service.cards import reflect_review, review_in_session
from app.features.quiz.service.runtime import QuizRuntime


async def review_offline(
    rt: QuizRuntime, user_id: str, card_id: str, ok: bool, receipt: ReviewReceiptIn
) -> ReviewOut:
    async with rt.session_factory() as db:
        repo = OfflineReviewRepository(db, user_id)
        receipt_id = str(receipt.id)
        new = await repo.reserve(receipt_id, card_id, receipt.due_date, ok)
        if new is None:
            past = await repo.by_receipt(receipt_id)
            if (
                past is None
                or past.response is None
                or (past.card_id, past.due_date, past.ok) != (card_id, receipt.due_date, ok)
            ):
                raise AppError(
                    "card_receipt_changed", "This answer has already been recorded.", 409
                )
            return ReviewOut.model_validate(past.response)
        out = await review_in_session(rt, db, user_id, card_id, ok, expected_due=receipt.due_date)
        await repo.complete(new, out.model_dump(mode="json"))
        await db.commit()
    await reflect_review(rt, user_id, out)
    return out
