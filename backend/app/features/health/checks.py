"""Contrôles de santé qui s'appuient sur les features : la base et les clés LLM (sans réseau)."""

from collections.abc import Callable, Mapping
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import Cipher
from app.features.settings.keys_service import ApiKeyService
from app.providers.health import HealthStatus, available
from app.providers.llm.base import LlmProvider


class DatabaseCheck:
    name = "db"

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def check(self) -> HealthStatus:
        async with self._session_factory() as session:
            await session.execute(text("SELECT 1"))
        return available()


class _KeyEntry(Protocol):
    """Ce que `_describe` lit d'une entrée de `ApiKeyService.list()` (type local : une feature
    n'importe d'une autre que son service)."""

    @property
    def label(self) -> str: ...
    @property
    def source(self) -> str | None: ...
    @property
    def readable(self) -> bool: ...


def _describe(entry: _KeyEntry) -> str:
    if entry.source is None:
        return f"{entry.label} : aucune clé"
    return f"{entry.label} : {'clé présente' if entry.readable else 'clé illisible'}"


class LlmKeysCheck:
    """`ok` si l'utilisateur local a au moins une clé LLM lisible (interface ou `.env`).
    Aucun appel réseau : le test réel d'une clé reste l'action « Tester » des réglages."""

    name = "llm"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cipher: Cipher,
        env_keys: Mapping[str, str | None],
        providers: Mapping[str, LlmProvider],
        local_user_id: Callable[[], str | None],
    ) -> None:
        self._session_factory = session_factory
        self._cipher = cipher
        self._env_keys = env_keys
        self._providers = providers
        self._local_user_id = local_user_id

    async def check(self) -> HealthStatus:
        user_id = self._local_user_id()
        if user_id is None:
            return HealthStatus(ok=False, detail="Aucun utilisateur local.")
        async with self._session_factory() as session:
            service = ApiKeyService(
                session, user_id, self._cipher, self._env_keys, self._providers, llm=self._providers
            )
            entries = await service.list()
        usable = any(e.source is not None and e.readable for e in entries)
        return HealthStatus(ok=usable, detail=" ; ".join(_describe(e) for e in entries))
