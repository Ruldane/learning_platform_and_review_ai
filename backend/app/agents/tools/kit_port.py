"""Port of the application kit (SPEC 6.4, F16, D142). `app.agents` imports no feature
(contract 6): it describes here what the `application_kit` graph needs; the feature
`applications` implements it (`AgentKitStore`, task 7.6).

The profile, the offer, the written pieces and the file are personal or untrusted data
(17.2, 17.4): never logged, neither here nor by the implementation.

- `context`: read-only; 404 `application_not_found` if the record is not January's.
- `save_piece`: **idempotent per `(record, piece, session)`**: a node replayed after a stop
  (SPEC 9.4) rereads the row of its session and writes no second one; a new session
  replaces the content of the piece (unless January edited it: `keep`). Returns the piece's id.
- `save_dossier`: `companies.dossier`, its read pages and its date, idempotent per session.
"""

from typing import Any, Protocol

from app.agents.tools.kit_schema import CompanyDossier, KitContext, KitKind, KitStatus, SourceRef
from app.core.errors import AppError


class KitStore(Protocol):
    async def context(self, user_id: str, application_id: str) -> KitContext: ...

    async def save_piece(
        self,
        user_id: str,
        session_id: str,
        application_id: str,
        kind: KitKind,
        status: KitStatus,
        content: str,
        meta: dict[str, Any],
    ) -> str: ...

    async def save_dossier(
        self,
        user_id: str,
        session_id: str,
        company: str,
        dossier: CompanyDossier,
        sources: list[SourceRef],
    ) -> None: ...


def kit_unavailable() -> AppError:
    return AppError("kit_unavailable", "Application kits are unavailable in this runtime.", 503)


class _NoKit:
    """Engine default value (tests, starts without the feature)."""

    async def context(self, user_id: str, application_id: str) -> KitContext:
        raise kit_unavailable()

    async def save_piece(
        self,
        user_id: str,
        session_id: str,
        application_id: str,
        kind: KitKind,
        status: KitStatus,
        content: str,
        meta: dict[str, Any],
    ) -> str:
        raise kit_unavailable()

    async def save_dossier(
        self,
        user_id: str,
        session_id: str,
        company: str,
        dossier: CompanyDossier,
        sources: list[SourceRef],
    ) -> None:
        raise kit_unavailable()


NO_KIT: KitStore = _NoKit()
