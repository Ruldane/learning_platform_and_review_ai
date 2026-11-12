"""L'apprentissage dans la vie de l'application : ce que les requêtes HTTP et les agents
partagent (base, lanceur de sessions, verrous par objectif). Ouvert par le lifespan
(`app.state.learning`), avant le moteur d'agents (D87)."""

import asyncio
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher


@dataclass
class LearningRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: SessionLauncher
    # Faible : un verrou que plus personne ne tient disparaît (une entrée par objectif sinon).
    _goal_locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )

    def _lock(self, user_id: str, goal_id: str) -> asyncio.Lock:
        key = (user_id, goal_id)
        lock = self._goal_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._goal_locks[key] = lock
        return lock

    @asynccontextmanager
    async def goal_lock(self, user_id: str, goal_id: str) -> AsyncIterator[None]:
        """Section critique d'un objectif : choix du parcours (route `choose`), choix enregistré
        et lancement du programme (port, nœud `finalize`). Double clic, ou choix en même temps
        qu'une reprise générique : un seul `program_builder`. Propre à ce processus (un seul
        worker, comme les verrous de la recherche)."""
        async with self._lock(user_id, goal_id):
            yield
