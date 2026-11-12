"""Les leçons dans la vie de l'application (D91) : ce que la production en chaîne, le port du
Rédacteur (`AgentLessonStore`), la tâche planifiée et les routes partagent (base, lanceur de
sessions, mémoire, recherche, stockage des fichiers, rendu PDF, verrous par programme). Créé par
le lifespan avant le moteur d'agents (`app.state.lessons`), avec le lanceur encore non lié."""

import asyncio
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import PublishingProviders
from app.features.memory.service.runtime import MemoryRuntime
from app.features.research.service.runtime import ResearchRuntime
from app.providers.storage.base import FileStorage


class Launcher(Protocol):
    """Ce que la production attend du lanceur de sessions (`SessionLauncher`, D82)."""

    async def start(
        self,
        user_id: str,
        graph: str,
        input: dict[str, Any],
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
    ) -> str: ...


class ProgramLocks:
    """Verrous des leçons, un par programme : la production (validation, tâche planifiée, fin
    d'une leçon) passe dessous. Faibles : un verrou que plus personne ne tient disparaît. Propres
    à ce processus (un seul worker, comme les verrous du programme et de la recherche)."""

    def __init__(self) -> None:
        self._locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )

    def get(self, user_id: str, program_id: str) -> asyncio.Lock:
        key = (user_id, program_id)
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock


@dataclass
class LessonsRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    memory: MemoryRuntime
    research: ResearchRuntime
    storage: FileStorage
    publishing: PublishingProviders
    _locks: ProgramLocks = field(default_factory=ProgramLocks, repr=False, compare=False)

    @asynccontextmanager
    async def lessons_lock(self, user_id: str, program_id: str) -> AsyncIterator[None]:
        async with self._locks.get(user_id, program_id):
            yield
