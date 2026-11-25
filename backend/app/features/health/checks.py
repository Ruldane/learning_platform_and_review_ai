"""Health checks that rely on features: the database and the LLM keys (no network)."""

from collections.abc import Callable, Mapping
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import Cipher
from app.features.settings.keys_service import ApiKeyService
from app.providers.health import HealthStatus, available
from app.providers.llm.base import LlmProvider
from app.providers.sandbox.base import CodeSandbox


class DatabaseCheck:
    name = "db"

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def check(self) -> HealthStatus:
        async with self._session_factory() as session:
            await session.execute(text("SELECT 1"))
        return available()


class _KeyEntry(Protocol):
    """What `_describe` reads from an entry of `ApiKeyService.list()` (local type: a feature
    imports only the service of another feature)."""

    @property
    def label(self) -> str: ...
    @property
    def source(self) -> str | None: ...
    @property
    def readable(self) -> bool: ...


def _describe(entry: _KeyEntry) -> str:
    if entry.source is None:
        return f"{entry.label}: no key"
    return f"{entry.label}: {'key present' if entry.readable else 'key unreadable'}"


GOOGLE_MODE_DETAIL = "Google mode: each account's keys are checked in its settings."


class LlmKeysCheck:
    """`ok` if the local user has at least one readable LLM key (interface or `.env`).
    No network call: the real test of a key remains the "Test" action in the settings.

    Google mode (P12): `/health` is public and there is no longer "one" user; the keys are
    those of each account (or of `.env`), checked in its settings: the check is `ok`
    with a hint, never a permanent degraded state (D28 no. 3)."""

    name = "llm"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cipher: Cipher,
        env_keys: Mapping[str, str | None],
        providers: Mapping[str, LlmProvider],
        local_user_id: Callable[[], str | None],
        *,
        google_mode: bool = False,
    ) -> None:
        self._session_factory = session_factory
        self._cipher = cipher
        self._env_keys = env_keys
        self._providers = providers
        self._local_user_id = local_user_id
        self._google_mode = google_mode

    async def check(self) -> HealthStatus:
        if self._google_mode:
            return HealthStatus(ok=True, detail=GOOGLE_MODE_DETAIL)
        user_id = self._local_user_id()
        if user_id is None:
            return HealthStatus(ok=False, detail="No local user.")
        async with self._session_factory() as session:
            service = ApiKeyService(
                session, user_id, self._cipher, self._env_keys, self._providers, llm=self._providers
            )
            entries = await service.list()
        usable = any(e.source is not None and e.readable for e in entries)
        return HealthStatus(ok=usable, detail="; ".join(_describe(e) for e in entries))


class SandboxCheck:
    """`ok` if the sandbox has a heartbeat (the `sandbox` container launcher writes its
    heartbeat every
    second). No code is executed: the check only reads a timestamp."""

    name = "sandbox"
    label = "Sandbox"

    def __init__(self, sandbox: CodeSandbox) -> None:
        self._sandbox = sandbox

    async def check(self) -> HealthStatus:
        if await self._sandbox.healthy():
            return available()
        return HealthStatus(ok=False, detail="Sandbox: the container is not responding.")
