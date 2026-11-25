"""MCP access tokens (phase 10, P16): created, limited to certain features (read-only by
default), expiring after 1, 7, 30 or 90 days, revocable. Only the SHA-256 is kept; the value is
only returned at creation. Never logged. The `mcp` and `auth` features stay reserved to the
interface (level 4)."""

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
    """`known_features`: the features that declare tools (`None` as long as none declares any:
    nothing to compare)."""

    def __init__(
        self, db: AsyncSession, user_id: str, known_features: frozenset[str] | None = None
    ) -> None:
        self._tokens = TokenRepository(db, user_id)
        self._known = known_features

    def _clean_features(self, features: list[str]) -> list[str]:
        unique = list(dict.fromkeys(name.strip().lower() for name in features))
        for name in unique:
            if not _FEATURE_NAME.match(name):
                raise AppError("invalid_feature", "Invalid feature name.", 422)
            if name in NEVER_EXPOSED_FEATURES:
                raise AppError(
                    "feature_never_exposed",
                    f"The feature '{name}' is never opened to MCP.",
                    422,
                )
            if self._known is not None and name not in self._known:
                raise AppError("unknown_feature", "The selected feature has no MCP tools.", 422)
        return unique

    async def create(
        self, label: str, features: list[str], mode: str, days: int
    ) -> tuple[McpTokenOut, str]:
        """Creates a token. Returns its record and its clear value, **shown only once**."""
        clean = self._clean_features(features)
        label = label.strip()
        if not label:
            raise AppError("invalid_label", "Give the token a name.", 422)
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
        """My tokens, revoked ones included, without their value."""
        return [McpTokenOut.model_validate(row) for row in await self._tokens.newest_first()]

    async def dedicated_writers(self, feature: str) -> list[McpTokenOut]:
        """Active tokens limited to a single feature, for a transport authorization."""
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
        """Revokes the token (404 if it is not mine); no effect if it already is."""
        if await self._tokens.revoke(token_id, datetime.now(UTC)) is None:
            raise AppError("not_found", "Resource not found.", 404)
