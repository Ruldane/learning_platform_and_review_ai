"""Ce que « Mes données » reçoit du démarrage : le stockage des fichiers, le moteur d'agents (que
« Tout supprimer » interroge pour annuler les sessions en cours) et les verrous par compte."""

from dataclasses import dataclass, field

from app.agents.runtime.handle import AgentRuntime
from app.features.postings.service.runtime import KeyLocks
from app.providers.storage.base import FileStorage
from app.providers.vector.base import MemoryRepository


@dataclass(frozen=True)
class AccountRuntime:
    storage: FileStorage
    index: MemoryRepository
    runtime: AgentRuntime
    locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)
