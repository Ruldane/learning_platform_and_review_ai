"""The daily brief in the application's lifetime (D162): what the routes, the morning job and the
`daily_brief` flow port (`AgentBriefStore`) share: database, session launcher (bound to the
engine later), the features whose facts it reads (quiz, study, applications), clock and locks.
Created by `app.bootstrap_daily` before the agent engine (`app.state.daily.brief`)."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.lessons.service.runtime import Launcher
from app.features.postings.service.runtime import KeyLocks
from app.features.quiz.service.runtime import QuizRuntime
from app.features.study.service.runtime import StudyRuntime

GRAPH = "daily_brief"
SUBJECT = "brief"
_ENSURE = "brief-ensure"


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class BriefRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    quiz: QuizRuntime
    study: StudyRuntime
    applications: ApplicationsRuntime
    now: Callable[[], datetime] = utc_now
    locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)

    def ensure_lock(self, user_id: str) -> asyncio.Lock:
        """The brief creation lock of a user: the "already there?" check, the insert and the
        session launch form a single section. Local to this process; the brief's
        `(user_id, day)` uniqueness remains the last safeguard."""
        return self.locks.get(user_id, _ENSURE)
