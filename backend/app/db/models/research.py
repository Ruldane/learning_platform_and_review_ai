from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types shared with `app.agents`, which cannot import a feature (contract 6).
PageStatus = Literal["ok", "unreadable"]
SourceVerdict = Literal["pending", "kept", "rejected"]
# « Pages et personnes repérées » (SPEC 13.3); the people part comes in phase 4.
SourceKind = Literal["page", "person"]
CacheKind = Literal["page", "search"]
# Minimum score out of 100 for a source to be kept (SPEC 10.3).
SOURCE_THRESHOLD = 60


class WebCacheEntry(UserScopedMixin, Base):
    """Cache of a user's web search: a page read or a list of results (SPEC 13.6).

    `key_hash` is the fingerprint of the normalized URL or of the query: the plain key (a URL,
    a query) is never stored here."""

    __tablename__ = "web_cache"
    # `uq_web_cache_user_id`: name that the `Base` convention gives to (user_id, kind, key_hash).
    __table_args__ = (UniqueConstraint("user_id", "kind", "key_hash"),)

    kind: Mapped[str] = mapped_column(String(8))
    key_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)


class Source(UserScopedMixin, Base):
    """A source found by a search session, with its score and verdict (SPEC 13.3).

    `session_id` is not a foreign key: the sources outlive their session."""

    __tablename__ = "sources"
    # `uq_sources_user_id`: name from the `Base` convention for (user_id, session_id, url_hash).
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
    """A query run by a session, cleaned of any personal data.

    It is used to replay a node (the same query is neither counted nor billed again) and to
    display the queries run."""

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
    """Requests sent to a paid provider this month (Brave: 900 per UTC calendar month).

    `key_fingerprint` is a short fingerprint of the key, never the key: the same `.env` key
    shared between users has a counter per user, which `month_total` adds up."""

    __tablename__ = "search_usage"
    # `uq_search_usage_user_id` : (user_id, provider, month, key_fingerprint).
    __table_args__ = (UniqueConstraint("user_id", "provider", "month", "key_fingerprint"),)

    provider: Mapped[str] = mapped_column(String(16))
    month: Mapped[str] = mapped_column(String(7))
    # Derived from a secret: never exported (`info`, D185 no. 10 b), even if it is not the key.
    key_fingerprint: Mapped[str] = mapped_column(String(16), info={"export": False})
    count: Mapped[int] = mapped_column(Integer, default=0)
