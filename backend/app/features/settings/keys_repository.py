from datetime import datetime

from app.db.models.accounts import ApiKey
from app.db.repository import UserScopedRepository


class ApiKeyRepository(UserScopedRepository[ApiKey]):
    """Une ligne `api_keys` par fournisseur et par utilisateur (clé chiffrée)."""

    model = ApiKey

    async def get_by_provider(self, provider: str) -> ApiKey | None:
        rows = await self.list(provider=provider)
        return rows[0] if rows else None

    async def upsert(self, provider: str, encrypted_key: str, last4: str) -> ApiKey:
        """Remplace la clé ; le résultat du dernier test ne vaut plus pour la nouvelle clé."""
        fields = {
            "encrypted_key": encrypted_key,
            "last4": last4,
            "last_tested_at": None,
            "last_test_ok": None,
        }
        row = await self.get_by_provider(provider)
        if row is None:
            return await self.add(provider=provider, **fields)
        updated = await self.update(row.id, **fields)
        assert updated is not None
        return updated

    async def record_test(self, provider: str, ok: bool, at: datetime) -> None:
        row = await self.get_by_provider(provider)
        if row is not None:
            await self.update(row.id, last_tested_at=at, last_test_ok=ok)

    async def delete_provider(self, provider: str) -> bool:
        row = await self.get_by_provider(provider)
        return await self.delete(row.id) if row is not None else False
