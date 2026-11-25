"""Port of the mock interview (SPEC F10, D145). `app.agents` imports no feature (contract 6):
it describes here what the `interview` graph needs; the `applications` feature implements it
(`AgentInterviewStore`, task 7.9).

January's answers, the offer, the profile and the file are personal or untrusted data
(17.2, 17.4): never logged, neither here nor by the implementation.

- `context`: read-only; 404 `interview_not_found` if the interview is not January's.
- `save_result`: **idempotent per session**: a node replayed after a stop (SPEC 9.4) rereads
  the outcome of its session, writes no second debrief or second card. `debrief=None` and
  `exchanges=[]`: interview stopped before the first answer (`stopped`, nothing else: no
  exchange, no card, no event); `debrief=None` with exchanges: the debrief failed,
  interview `debrief_failed` (the answers are kept, no card, no debrief event); otherwise
  interview `done` with its exchanges, its debrief, the terms the profile does not state in the
  improved answer (`flags`: answer "to verify") and the review cards of the missed questions
  (source `interview`)."""

from typing import Protocol

from app.agents.tools.interview_schema import Debrief, Exchange, InterviewContext
from app.agents.tools.study_schema import CardDraft
from app.agents.tools.system_design_port import (
    SystemDesignContext,
    SystemDesignReview,
    SystemDesignSubmission,
)
from app.core.errors import AppError


class InterviewStore(Protocol):
    async def freeze_design(
        self, user_id: str, session_id: str, interview_id: str, submission: SystemDesignSubmission
    ) -> SystemDesignContext: ...

    async def save_design_review(
        self, user_id: str, session_id: str, interview_id: str, review: SystemDesignReview
    ) -> None: ...

    async def context(self, user_id: str, interview_id: str) -> InterviewContext: ...

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        interview_id: str,
        exchanges: list[Exchange],
        debrief: Debrief | None,
        flags: list[str],
        cards: list[CardDraft],
    ) -> None: ...


def interview_unavailable() -> AppError:
    return AppError(
        "interview_unavailable", "Mock interviews are unavailable in this runtime.", 503
    )


class _NoInterviews:
    """Engine default value (tests, starts without the feature)."""

    async def freeze_design(
        self, user_id: str, session_id: str, interview_id: str, submission: SystemDesignSubmission
    ) -> SystemDesignContext:
        raise interview_unavailable()

    async def save_design_review(
        self, user_id: str, session_id: str, interview_id: str, review: SystemDesignReview
    ) -> None:
        raise interview_unavailable()

    async def context(self, user_id: str, interview_id: str) -> InterviewContext:
        raise interview_unavailable()

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        interview_id: str,
        exchanges: list[Exchange],
        debrief: Debrief | None,
        flags: list[str],
        cards: list[CardDraft],
    ) -> None:
        raise interview_unavailable()


NO_INTERVIEWS: InterviewStore = _NoInterviews()
