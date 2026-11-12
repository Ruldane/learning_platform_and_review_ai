"""Le programme dans la vie de l'application : ce que les requêtes HTTP et le port du Stratège
partagent (base, mémoire pour le reflet des niveaux, verrous par programme). Ouvert par le
lifespan (`app.state.program`), avant le moteur d'agents (D88)."""

import asyncio
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.memory.service.runtime import MemoryRuntime


@dataclass
class ProgramRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    memory: MemoryRuntime
    # Validations demandées par la route et reprises dans la session du Stratège : un second
    # clic pendant que `finalize` tourne rend le même état (202) au lieu d'un 409.
    validating: set[str] = field(default_factory=set, repr=False, compare=False)
    # Faible : un verrou que plus personne ne tient disparaît (une entrée par programme sinon).
    _locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )

    def _lock(self, user_id: str, program_id: str) -> asyncio.Lock:
        key = (user_id, program_id)
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    @asynccontextmanager
    async def program_lock(self, user_id: str, program_id: str) -> AsyncIterator[None]:
        """Section critique d'un programme : toute modification de January (déplacement, ajout,
        suppression, date de début), la validation et l'écriture d'une version par le Stratège.
        Les règles (85 %, pratique, quiz) sont vérifiées sous ce verrou, sur l'état relu : deux
        déplacements simultanés ne dépassent jamais le plafond ensemble. Propre à ce processus
        (un seul worker, comme les verrous de l'apprentissage et de la recherche)."""
        async with self._lock(user_id, program_id):
            yield
