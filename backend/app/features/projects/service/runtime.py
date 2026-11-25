"""Projects in the application's life (D166): what the routes, the brief task and the port of the
`project_brief` and `project_review` paths (`AgentProjectStore`) share: database, session
launcher (bound to the engine later), screenshot storage, memory (level reflection), master
profile (project entry), web search (reading the repository), clock and locks. Created by
`app.bootstrap_daily` before the agent engine (`app.state.daily.projects`)."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.cv.service.runtime import CvRuntime
from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.features.postings.service.runtime import KeyLocks
from app.features.research.service.runtime import ResearchRuntime
from app.providers.github.base import GithubContributions
from app.providers.storage.base import FileStorage

BRIEF_GRAPH = "project_brief"
REVIEW_GRAPH = "project_review"
SUBJECT = "project"
STORAGE_CATEGORY = "projects"
BRIEF_ATTEMPTS = 3  # automatic tests of the statement (P1), then « Réessayer » (retry)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class ProjectsRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    storage: FileStorage
    memory: MemoryRuntime
    cv: CvRuntime
    research: ResearchRuntime
    github: GithubContributions
    now: Callable[[], datetime] = utc_now
    locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)

    def project_lock(self, user_id: str, project_id: str) -> asyncio.Lock:
        """A project's lock: the submission (screenshots, status, launch), writing the brief or the
        assessment, correcting a status whose session died, an edited draft and the profile entry
        each form a single section."""
        return self.locks.get(user_id, f"project:{project_id}")

    def ensure_lock(self, user_id: str) -> asyncio.Lock:
        """Creation of a user's projects: one pass of the task at a time."""
        return self.locks.get(user_id, "projects-ensure")
