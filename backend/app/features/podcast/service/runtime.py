from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.db.base import utcnow
from app.features.postings.service.runtime import KeyLocks
from app.features.quiz.service.runtime import QuizRuntime
from app.providers.speech.base import SpeechProvider
from app.providers.storage.base import FileStorage

GRAPH = "podcast"
SUBJECT = "podcast"
CATEGORY = "podcasts"


@dataclass
class PodcastRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: SessionLauncher
    quiz: QuizRuntime
    storage: FileStorage
    speech: SpeechProvider
    now: Callable[[], datetime] = utcnow
    locks: KeyLocks = field(default_factory=KeyLocks)
