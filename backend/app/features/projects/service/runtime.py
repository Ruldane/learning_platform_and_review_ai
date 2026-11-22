"""Les projets dans la vie de l'application (D166) : ce que les routes, la tâche des énoncés et le
port des parcours `project_brief` et `project_review` (`AgentProjectStore`) partagent : base,
lanceur de sessions (lié au moteur ensuite), stockage des captures, mémoire (reflet des niveaux),
profil maître (entrée de projet), recherche web (lecture du dépôt), horloge et verrous. Créé par
`app.bootstrap_daily` avant le moteur d'agents (`app.state.daily.projects`)."""

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
BRIEF_ATTEMPTS = 3  # essais automatiques de l'énoncé (P1), puis « Réessayer »


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
        """Le verrou d'un projet : le rendu (captures, statut, lancement), l'écriture de l'énoncé
        ou de l'évaluation, la correction d'un statut dont la session est morte, un brouillon
        retouché et l'entrée au profil forment chacun une seule section."""
        return self.locks.get(user_id, f"project:{project_id}")

    def ensure_lock(self, user_id: str) -> asyncio.Lock:
        """Création des projets d'une utilisatrice : un passage de la tâche à la fois."""
        return self.locks.get(user_id, "projects-ensure")
