"""Tables du serveur MCP (phase 10, P3, P14 à P19) : jetons, interrupteur général, journal des
appels, historique des changements (annulation) et demandes « À confirmer ». Aucune clé
étrangère : le journal et l'historique survivent à la révocation d'un jeton."""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

McpMode = Literal["read", "write"]
ConfirmationStatus = Literal["pending", "confirmed", "refused", "expired", "failed"]
ChangeOp = Literal["insert", "update", "delete"]


class McpToken(UserScopedMixin, Base):
    """Un jeton d'accès au MCP (P16) : `tmcp_` + 32 octets aléatoires, **seul le SHA-256 est
    gardé** (`hash`, jamais exporté, jamais journalisé) et la valeur n'est montrée qu'une fois.
    `features` : les features ouvertes ; `mode` : `read` par défaut ; `expires_at` : 1, 7, 30 ou 90
    jours après la création."""

    __tablename__ = "mcp_tokens"
    # `uq_mcp_tokens_hash` : une empreinte désigne un seul jeton.
    __table_args__ = (UniqueConstraint("hash"),)

    label: Mapped[str] = mapped_column(String(60))
    hash: Mapped[str] = mapped_column(String(64), info={"export": False})
    features: Mapped[list[Any]] = mapped_column(default=list)
    mode: Mapped[str] = mapped_column(String(8), default="read")
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)


class McpPrefs(UserScopedMixin, Base):
    """L'interrupteur général du MCP, une ligne par compte. Coupé par défaut (P16) : sans ligne,
    ou `enabled` faux, aucun jeton n'ouvre rien."""

    __tablename__ = "mcp_prefs"
    # `uq_mcp_prefs_user_id` : une ligne par compte.
    __table_args__ = (UniqueConstraint("user_id"),)

    enabled: Mapped[bool] = mapped_column(default=False)


class McpCall(UserScopedMixin, Base):
    """Un appel d'outil (P19) : l'outil, son niveau, le code de résultat (HTTP), la durée et les
    identifiants touchés. **Jamais le contenu** des paramètres ni de la réponse. Un appel refusé
    est journalisé aussi : `level` 0 = refusé avant la résolution de l'outil, `token_id` vide =
    jeton non reconnu."""

    __tablename__ = "mcp_calls"
    __table_args__ = (Index("ix_mcp_calls_user_created", "user_id", "created_at"),)

    token_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)
    action: Mapped[str] = mapped_column(String(80))
    level: Mapped[int] = mapped_column(Integer)
    code: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    ids: Mapped[dict[str, Any]] = mapped_column(default=dict)


class McpChange(UserScopedMixin, Base):
    """Une ligne touchée par un appel de niveau 2 (P14) : l'état avant et après (`before`,
    `after` ; vide pour un ajout ou une suppression). `undo(call_id)` applique l'inverse **si la
    ligne est restée dans l'état « après »**. `undone_at` : posé une fois annulée."""

    __tablename__ = "mcp_changes"
    __table_args__ = (Index("ix_mcp_changes_call", "call_id"),)

    call_id: Mapped[str] = mapped_column(String(36))
    table_name: Mapped[str] = mapped_column(String(64))
    row_id: Mapped[str] = mapped_column(String(36))
    op: Mapped[str] = mapped_column(String(8))
    before: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    after: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    undone_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)


class McpConfirmation(UserScopedMixin, Base):
    """Une demande « À confirmer » (P15) : la requête complète (méthode, chemin, paramètres,
    corps), un résumé neutre et le verdict d'un éventuel contrôle préalable. Expire après 24 h ;
    à la confirmation, la requête s'exécute une seule fois sous l'identité enregistrée."""

    __tablename__ = "mcp_confirmations"
    __table_args__ = (Index("ix_mcp_confirmations_user_status", "user_id", "status"),)

    token_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(80))
    request: Mapped[dict[str, Any]] = mapped_column(default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    precheck: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    result_code: Mapped[int | None] = mapped_column(Integer, default=None)
