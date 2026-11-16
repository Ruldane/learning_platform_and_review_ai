"""Les candidatures dans la vie de l'application (D139) : base, lanceur de sessions (lié au moteur
ensuite, pour l'Assistant de suivi, 7.4) et verrous. Créé par le lifespan
(`app.state.career.applications`)."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.lessons.service.runtime import Launcher
from app.features.postings.service.runtime import KeyLocks, utc_now

LOCK_KEY = "applications"


@dataclass
class ApplicationsRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    now: Callable[[], datetime] = utc_now
    # Création, événements et adoption des versions : un verrou par utilisatrice (le contrôle des
    # doublons et l'écriture de la fiche ne se croisent pas).
    locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)
    # Création de la fiche entreprise : le même `KeyLocks` que celui des revues de CV (M7).
    company_locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)

    def lock(self, user_id: str) -> asyncio.Lock:
        """Le verrou des candidatures de l'utilisatrice."""
        return self.locks.get(user_id, LOCK_KEY)
