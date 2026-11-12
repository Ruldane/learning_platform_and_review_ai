import builtins
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.core.security import Cipher, KnownSecrets, SecretUnreadable
from app.db.models.accounts import ApiKey
from app.features.settings.keys_repository import ApiKeyRepository
from app.features.settings.keys_schemas import ApiKeyOut, ModelsOut, ProviderModels
from app.providers.keys import KeyProvider
from app.providers.llm.base import KeyTestResult, LlmProvider
from app.providers.llm.model_defaults import PRESETS

logger = logging.getLogger(__name__)

Source = Literal["ui", "env"]
_MIN_KEY_LENGTH = 8


def _env_key(env_keys: Mapping[str, str | None], provider: str) -> str | None:
    value = (env_keys.get(provider) or "").strip()
    return value or None


async def _resolve_key(
    repo: ApiKeyRepository,
    cipher: Cipher,
    env_keys: Mapping[str, str | None],
    provider: str,
) -> tuple[str, Source] | None:
    """Clé en clair et origine : base d'abord, puis `.env` (D8). Lève `SecretUnreadable` si la
    clé de la base ne se déchiffre plus. Toute valeur déchiffrée rejoint `KnownSecrets`."""
    row = await repo.get_by_provider(provider)
    if row is not None:
        plain = cipher.decrypt(row.encrypted_key)
        KnownSecrets.add(plain)
        return plain, "ui"
    env_key = _env_key(env_keys, provider)
    if env_key is None:
        return None
    KnownSecrets.add(env_key)
    return env_key, "env"


class DbKeyReader:
    """Lecture des clés pour la fabrique LLM. Ouvre sa propre session : elle est appelée hors
    requête HTTP (agents, tâches planifiées). Satisfait `KeyReader`."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cipher: Cipher,
        env_keys: Mapping[str, str | None],
    ) -> None:
        self._session_factory = session_factory
        self._cipher = cipher
        self._env_keys = env_keys

    async def get_key(self, user_id: str, provider: str) -> str | None:
        async with self._session_factory() as session:
            repo = ApiKeyRepository(session, user_id)
            resolved = await _resolve_key(repo, self._cipher, self._env_keys, provider)
        return resolved[0] if resolved is not None else None


def _unknown(name: str) -> AppError:
    return AppError("unknown_provider", f"Fournisseur inconnu : {name}.", 404)


class ApiKeyService:
    """`providers` : fournisseurs de l'écran des clés (LLM et Brave), pour lister, saisir,
    supprimer et tester une clé ; `llm` : les seuls fournisseurs LLM, pour les modèles (D73)."""

    def __init__(
        self,
        session: AsyncSession,
        user_id: str,
        cipher: Cipher,
        env_keys: Mapping[str, str | None],
        providers: Mapping[str, KeyProvider],
        *,
        llm: Mapping[str, LlmProvider],
    ) -> None:
        self._repo = ApiKeyRepository(session, user_id)
        self._cipher = cipher
        self._env_keys = env_keys
        self._providers = providers
        self._llm = llm

    def _provider(self, name: str) -> KeyProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise _unknown(name)
        return provider

    def _llm_provider(self, name: str) -> LlmProvider:
        provider = self._llm.get(name)
        if provider is None:
            raise _unknown(name)
        return provider

    async def get_plaintext(self, provider: str) -> str | None:
        """Clé en clair (base d'abord, puis `.env`), ou `None`. Lève `SecretUnreadable`."""
        self._provider(provider)
        resolved = await _resolve_key(self._repo, self._cipher, self._env_keys, provider)
        return resolved[0] if resolved is not None else None

    def _out(self, provider: KeyProvider, row: ApiKey | None) -> ApiKeyOut:
        if row is not None:
            return ApiKeyOut(
                provider=provider.name,
                label=provider.label,
                source="ui",
                last4=row.last4,
                readable=self._is_readable(row),
                last_tested_at=row.last_tested_at,
                last_test_ok=row.last_test_ok,
            )
        env_key = _env_key(self._env_keys, provider.name)
        return ApiKeyOut(
            provider=provider.name,
            label=provider.label,
            source="env" if env_key else None,
            last4=env_key[-4:] if env_key else None,
            readable=True,
            last_tested_at=None,
            last_test_ok=None,
        )

    def _is_readable(self, row: ApiKey) -> bool:
        try:
            KnownSecrets.add(self._cipher.decrypt(row.encrypted_key))
        except SecretUnreadable:
            return False
        return True

    async def test(self, provider: str) -> KeyTestResult:
        """Teste la clé en vigueur. Le résultat est mémorisé pour une clé saisie dans l'interface
        (une clé `.env` n'a pas de ligne où l'écrire)."""
        key_provider = self._provider(provider)
        try:
            resolved = await _resolve_key(self._repo, self._cipher, self._env_keys, provider)
        except SecretUnreadable as exc:
            result = KeyTestResult(ok=False, message=exc.message)
            await self._repo.record_test(provider, False, datetime.now(UTC))
            return result
        if resolved is None:
            return KeyTestResult(
                ok=False, message=f"Aucune clé enregistrée pour {key_provider.label}."
            )
        plain, source = resolved
        result = await key_provider.test_key(plain)
        if source == "ui":
            await self._repo.record_test(provider, result.ok, datetime.now(UTC))
        return result

    async def _usable_key(self, provider: str) -> str | None:
        """Clé lisible, ou `None` si absente ou illisible."""
        try:
            return await self.get_plaintext(provider)
        except SecretUnreadable:
            return None

    async def list_models(self, provider: str) -> builtins.list[str] | None:
        llm = self._llm_provider(provider)
        key = await self._usable_key(provider)
        return await llm.list_models(key) if key else None

    async def _models_or_none(self, provider: str) -> builtins.list[str] | None:
        try:
            return await self.list_models(provider)
        except Exception as exc:
            # Un fournisseur en panne ne doit pas faire échouer toute la page : on ne journalise
            # que son nom et le type d'erreur, jamais la clé ni le message de l'exception.
            logger.warning(
                "Liste des modèles indisponible pour %s (%s)", provider, type(exc).__name__
            )
            return None

    async def models_overview(self) -> ModelsOut:
        """Fournisseurs, présence d'une clé lisible, modèles proposés et préréglages."""
        entries: builtins.list[ProviderModels] = []
        for llm in self._llm.values():
            has_key = await self._usable_key(llm.name) is not None
            models = await self._models_or_none(llm.name) if has_key else None
            entries.append(
                ProviderModels(name=llm.name, label=llm.label, has_key=has_key, models=models)
            )
        return ModelsOut(providers=entries, presets=PRESETS)

    async def delete(self, provider: str) -> None:
        self._provider(provider)
        await self._repo.delete_provider(provider)

    async def set(self, provider: str, key: str) -> ApiKeyOut:
        key_provider = self._provider(provider)
        clean = key.strip()
        if not clean:
            raise AppError("invalid_key", "La clé est vide.", 422)
        if len(clean) < _MIN_KEY_LENGTH:
            raise AppError("invalid_key", "La clé est trop courte.", 422)
        KnownSecrets.add(clean)
        row = await self._repo.upsert(provider, self._cipher.encrypt(clean), clean[-4:])
        return self._out(key_provider, row)

    async def list(self) -> builtins.list[ApiKeyOut]:
        rows = {row.provider: row for row in await self._repo.list()}
        return [self._out(p, rows.get(name)) for name, p in self._providers.items()]
