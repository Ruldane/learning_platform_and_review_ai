"""Le CV dans la vie de l'application (D124) : ce que les routes du profil maître et le port de
l'Archiviste (`AgentProfileStore`) partagent : base, mémoire (documents rangés, fichiers relus),
lanceur de sessions (lié au moteur ensuite), mise en page des PDF et verrous. Créé par le lifespan
avant le moteur d'agents (`app.state.career.cv`)."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.providers.pdf.base import PdfLayoutExtractor

CAPTURE_GRAPH = "cv_capture"
PROFILE_SUBJECT = "master_profile"


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class CvRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    memory: MemoryRuntime
    launcher: Launcher
    layout: PdfLayoutExtractor
    now: Callable[[], datetime] = utc_now
    _versions: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)
    _imports: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)

    def version_lock(self, user_id: str) -> asyncio.Lock:
        """Une nouvelle version du profil à la fois par utilisateur (brouillon de l'Archiviste,
        version de January) : numéros sans course. Propre à ce processus (un seul worker) ; l'index
        unique `(user_id, version)` reste le dernier rempart."""
        return self._versions.setdefault(user_id, asyncio.Lock())

    def import_lock(self, user_id: str) -> asyncio.Lock:
        """« Capture ouverte ? sinon lancer » : un double envoi ne lance qu'une capture."""
        return self._imports.setdefault(user_id, asyncio.Lock())
