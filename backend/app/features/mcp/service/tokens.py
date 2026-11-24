"""Les jetons d'accès au MCP (phase 10, P16) : créés, limités à certaines features (lecture seule
par défaut), expirant après 1, 7, 30 ou 90 jours, révocables. Seul le SHA-256 est gardé ; la valeur
n'est rendue qu'à la création. Jamais journalisée. Les features `mcp` et `auth`
restent réservées à l'interface (niveau 4)."""

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.mcp.repository import TokenRepository
from app.features.mcp.schemas import McpTokenOut
from app.mcp.auth import new_token
from app.mcp.base import NEVER_EXPOSED_FEATURES

_FEATURE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


class TokenService:
    """`known_features` : les features qui déclarent des outils (`None` tant qu'aucune n'en
    déclare : rien à comparer)."""

    def __init__(
        self, db: AsyncSession, user_id: str, known_features: frozenset[str] | None = None
    ) -> None:
        self._tokens = TokenRepository(db, user_id)
        self._known = known_features

    def _clean_features(self, features: list[str]) -> list[str]:
        unique = list(dict.fromkeys(name.strip().lower() for name in features))
        for name in unique:
            if not _FEATURE_NAME.match(name):
                raise AppError("invalid_feature", "Nom de feature invalide.", 422)
            if name in NEVER_EXPOSED_FEATURES:
                raise AppError(
                    "feature_never_exposed",
                    f"La feature « {name} » ne s'ouvre jamais au MCP.",
                    422,
                )
            if self._known is not None and name not in self._known:
                raise AppError("unknown_feature", "The selected feature has no MCP tools.", 422)
        return unique

    async def create(
        self, label: str, features: list[str], mode: str, days: int
    ) -> tuple[McpTokenOut, str]:
        """Crée un jeton. Rend sa fiche et sa valeur en clair, **montrée une seule fois**."""
        clean = self._clean_features(features)
        label = label.strip()
        if not label:
            raise AppError("invalid_label", "Donne un nom au jeton.", 422)
        plain, digest = new_token()
        now = datetime.now(UTC)
        row = await self._tokens.add(
            label=label,
            hash=digest,
            features=clean,
            mode=mode,
            expires_at=now + timedelta(days=days),
        )
        return McpTokenOut.model_validate(row), plain

    async def mine(self) -> list[McpTokenOut]:
        """Mes jetons, révoqués compris, sans leur valeur."""
        return [McpTokenOut.model_validate(row) for row in await self._tokens.newest_first()]

    async def dedicated_writers(self, feature: str) -> list[McpTokenOut]:
        """Jetons actifs limités à une seule feature, pour une autorisation de transport."""
        now = datetime.now(UTC)
        return [
            token
            for token in await self.mine()
            if token.mode == "write"
            and token.features == [feature]
            and token.revoked_at is None
            and token.expires_at > now
        ]

    async def revoke(self, token_id: str) -> None:
        """Révoque le jeton (404 s'il n'est pas à moi) ; sans effet s'il l'est déjà."""
        if await self._tokens.revoke(token_id, datetime.now(UTC)) is None:
            raise AppError("not_found", "Resource not found.", 404)
