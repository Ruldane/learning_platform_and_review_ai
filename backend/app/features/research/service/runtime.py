"""La recherche web dans la vie de l'application : ce que les requêtes HTTP et les agents
partagent (fournisseurs, lecteur de clés, verrous). Ouvert par le lifespan
(`app.state.research`)."""

import asyncio
import weakref
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import ResearchProviders
from app.db.base import utcnow
from app.features.research.repository import WebCacheRepository
from app.features.research.service.pacing import BRAVE_INTERVAL_S, KeyPacer
from app.providers.llm.base import KeyReader

# Purge des entrées expirées du cache web d'un utilisateur : au plus une fois par heure, à
# l'occasion d'une écriture dans son cache (D76).
PURGE_EVERY = timedelta(hours=1)


@dataclass
class ResearchRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    providers: ResearchProviders
    keys: KeyReader
    now: Callable[[], datetime] = utcnow
    # Un seul verrou pour le processus : le compteur mensuel d'une clé Brave est partagé.
    brave_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    # Cadence de Brave par clé (1 requête par seconde en offre gratuite), pour tout le processus.
    brave_pacer: KeyPacer = field(default_factory=lambda: KeyPacer(BRAVE_INTERVAL_S))
    # Faible : un verrou que plus personne ne tient disparaît (une entrée par session sinon).
    _session_locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )
    _last_purge: dict[str, datetime] = field(default_factory=dict, repr=False, compare=False)

    def session_lock(self, user_id: str, session_id: str) -> asyncio.Lock:
        """Verrou d'une session de recherche : le contrôle « déjà fait ? plafond atteint ? »,
        l'appel au fournisseur et l'écriture forment une seule section, pour que deux appels
        simultanés (nœud rejoué) ne comptent qu'une fois. Propre à ce processus (un seul worker)."""
        key = (user_id, session_id)
        lock = self._session_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._session_locks[key] = lock
        return lock

    def purge_due(self, user_id: str, now: datetime) -> bool:
        """Vrai (et noté) si le cache de l'utilisateur n'a pas été purgé depuis `PURGE_EVERY`."""
        last = self._last_purge.get(user_id)
        if last is not None and now - last < PURGE_EVERY:
            return False
        self._last_purge[user_id] = now
        return True

    async def purge_if_due(self, db: AsyncSession, user_id: str) -> None:
        """Supprime les entrées expirées du cache de l'utilisateur, au plus une fois par
        `PURGE_EVERY`, dans la transaction d'écriture de l'appelant (D76)."""
        now = self.now()
        if self.purge_due(user_id, now):
            await WebCacheRepository(db, user_id).purge_expired(now)
