"""Les offres dans la vie de l'application (D122) : ce que les routes `postings` et `gap` et le port
de l'Analyste (`AgentGapStore`) partagent : base, recherche web (lecture du lien), mémoire
(élément `offre`, doublons « possibles »), lanceur de sessions (lié au moteur ensuite) et verrous.
Créé par le lifespan avant le moteur d'agents (`app.state.career.postings`)."""

import asyncio
import weakref
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.features.research.service.runtime import ResearchRuntime

GRAPH = "gap_analysis"
SUBJECT = "posting"


def utc_now() -> datetime:
    return datetime.now(UTC)


class KeyLocks:
    """Verrous par clé, faibles (un verrou que plus personne ne tient disparaît). Propres à ce
    processus (un seul worker, comme les autres verrous de l'application)."""

    def __init__(self) -> None:
        self._locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )

    def get(self, user_id: str, key: str) -> asyncio.Lock:
        lock = self._locks.get((user_id, key))
        if lock is None:
            lock = asyncio.Lock()
            self._locks[(user_id, key)] = lock
        return lock


def company_lock(locks: KeyLocks, user_id: str, key: str) -> asyncio.Lock:
    """Le verrou de la fiche entreprise `key` (`company_key`) : la revue de CV et le dossier du kit
    la créent toutes deux ; `locks` est le même `KeyLocks` des deux côtés (`bootstrap_career`)."""
    return locks.get(user_id, f"company:{key}")


@dataclass
class PostingsRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    research: ResearchRuntime
    memory: MemoryRuntime
    launcher: Launcher
    now: Callable[[], datetime] = utc_now
    # Ajout d'une offre : un verrou par lien normalisé ou par empreinte de texte (deux envois
    # du même lien attendent l'un l'autre ; l'index unique reste le dernier rempart).
    source_locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)
    # Lancement de l'analyse : un verrou par offre (ajout et relance n'en lancent qu'une).
    launch_locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)
