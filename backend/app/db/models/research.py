from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types partagés avec `app.agents`, qui ne peut pas importer une feature (contrat 6).
PageStatus = Literal["ok", "unreadable"]
SourceVerdict = Literal["pending", "kept", "rejected"]
# « Pages et personnes repérées » (SPEC 13.3) ; les personnes viennent en phase 4.
SourceKind = Literal["page", "person"]
CacheKind = Literal["page", "search"]
# Note minimale sur 100 pour qu'une source soit retenue (SPEC 10.3).
SOURCE_THRESHOLD = 60


class WebCacheEntry(UserScopedMixin, Base):
    """Cache de la recherche web d'un utilisateur : page lue ou liste de résultats (SPEC 13.6).

    `key_hash` est l'empreinte de l'URL normalisée ou de la requête : la clé en clair
    (une URL, une requête) n'est jamais stockée ici.
    """

    __tablename__ = "web_cache"
    # `uq_web_cache_user_id` : nom que la convention de `Base` donne à (user_id, kind, key_hash).
    __table_args__ = (UniqueConstraint("user_id", "kind", "key_hash"),)

    kind: Mapped[str] = mapped_column(String(8))
    key_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)


class Source(UserScopedMixin, Base):
    """Une source repérée par une session de recherche, avec sa note et son verdict (SPEC 13.3).

    `session_id` n'est pas une clé étrangère : les sources survivent à leur session.
    """

    __tablename__ = "sources"
    # `uq_sources_user_id` : nom de la convention de `Base` pour (user_id, session_id, url_hash).
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", "url_hash"),
        Index("ix_sources_user_session", "user_id", "session_id"),
    )

    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    kind: Mapped[str] = mapped_column(String(8), default="page")
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(Text, default=None)
    author: Mapped[str | None] = mapped_column(Text, default=None)
    lang: Mapped[str | None] = mapped_column(String(8), default=None)
    published: Mapped[str | None] = mapped_column(String(32), default=None)
    status: Mapped[str] = mapped_column(String(16))
    verdict: Mapped[str] = mapped_column(String(16), default="pending")
    score: Mapped[int | None] = mapped_column(Integer, default=None)
    score_detail: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    reason: Mapped[str | None] = mapped_column(String(300), default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)


class WebQuery(UserScopedMixin, Base):
    """Une requête lancée par une session, nettoyée de toute donnée personnelle.

    Elle sert au rejeu d'un nœud (la même requête n'est ni recomptée ni refacturée) et à
    l'affichage des requêtes lancées.
    """

    __tablename__ = "web_queries"
    # `uq_web_queries_user_id` : (user_id, session_id, query_hash).
    __table_args__ = (UniqueConstraint("user_id", "session_id", "query_hash"),)

    session_id: Mapped[str] = mapped_column(String(36))
    query_hash: Mapped[str] = mapped_column(String(64))
    query: Mapped[str] = mapped_column(Text)
    lang: Mapped[str | None] = mapped_column(String(8), default=None)
    provider: Mapped[str | None] = mapped_column(String(16), default=None)
    result_count: Mapped[int] = mapped_column(Integer, default=0)


class SearchUsage(UserScopedMixin, Base):
    """Requêtes envoyées à un fournisseur payant ce mois-ci (Brave : 900 par mois civil UTC).

    `key_fingerprint` est une empreinte courte de la clé, jamais la clé : une même clé `.env`
    partagée entre utilisateurs a un compteur par utilisateur, que `month_total` additionne.
    """

    __tablename__ = "search_usage"
    # `uq_search_usage_user_id` : (user_id, provider, month, key_fingerprint).
    __table_args__ = (UniqueConstraint("user_id", "provider", "month", "key_fingerprint"),)

    provider: Mapped[str] = mapped_column(String(16))
    month: Mapped[str] = mapped_column(String(7))
    key_fingerprint: Mapped[str] = mapped_column(String(16))
    count: Mapped[int] = mapped_column(Integer, default=0)
