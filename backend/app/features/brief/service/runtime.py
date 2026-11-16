"""Le brief du jour dans la vie de l'application (D162) : ce que les routes, la tâche du matin et le
port du parcours `daily_brief` (`AgentBriefStore`) partagent : base, lanceur de sessions (lié au
moteur ensuite), les features dont il lit les faits (quiz, étude, candidatures), horloge et
verrous. Créé par `app.bootstrap_daily` avant le moteur d'agents (`app.state.daily.brief`)."""

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
        """Le verrou de création du brief d'une utilisatrice : la vérification « déjà là ? »,
        l'insertion et le lancement de la session forment une seule section. Propre à ce
        processus ; l'unicité `(user_id, day)` du brief reste le dernier rempart."""
        return self.locks.get(user_id, _ENSURE)
