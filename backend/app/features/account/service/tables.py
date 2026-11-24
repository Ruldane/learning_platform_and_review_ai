"""Which tables go into the export, with which columns, and the JSON shape of a row.

Tables are read from `Base.metadata`: any table with a `user_id` column is exported, including
one a feature adds tomorrow, without changing anything here. **What never leaves is declared in
the model**, where the column is born: `info={"export": False}` on the column
(`api_keys.encrypted_key`) or on the table (`__table_args__ = {"info": {"export": False}}`,
`auth_sessions`). A guard (`unreviewed_secret_columns`) forces that decision for any column whose
name suggests a secret (limit: a secret stored in a JSON column has no name to spot, only review
catches it, D185 no. 10 b). `all_user_tables` lists the tables to erase and the technical queue
that finishes the purge of the old Google account."""

import base64
import re
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Column, MetaData, Table

import app.db.models  # noqa: F401  (registers the models on Base.metadata)
from app.db.base import Base

EXPORT = "export"  # `info` key: `False` excludes the column or the table from the export

# A column name that looks like a secret forces a choice: `info={"export": False}`, or list it
# here with the reason it is not a secret.
SECRET_NAME = re.compile(
    r"key|token|secret|hash|password|passwd|cookie|credential|cipher|encrypted|salt|nonce"
    r"|private|fingerprint|bearer|passphrase|signature|authoriz|totp|mfa"
    r"|(?:^|_)(?:otp|auth|jwt|pwd|pin)(?:_|$)",
    re.I,
)
REVIEWED_NOT_SECRET = frozenset(
    {
        # Fingerprints of content, address or query (deduplication), never a secret.
        "flashcards.front_hash",
        "job_postings.text_hash",
        "memory_items.content_hash",
        "documents.source_hash",
        "sources.url_hash",
        "resources.url_hash",
        "web_cache.key_hash",
        "web_queries.query_hash",
        "atlas_hypotheses.label_key",  # fingerprint of the hypothesis's normalised label
        "atlas_observations.evidence_key",  # stable marker of an account's evidence
        "shared_week_proposals.fingerprint",  # fingerprint of the proposed schedule
        "shared_week_proposals.selection_key",  # fingerprint of the group of programs
        "plan_versions.base_fingerprint",  # fingerprint of the plan rows (detects a changed plan)
        # Storage keys: a storage file name or a row marker.
        "documents.storage_key",
        "cv_versions.storage_key",
        "lessons.pdf_key",
        "program_books.pdf_key",
        "program_books.epub_key",
        "portfolio_drafts.html_key",
        "portfolio_drafts.zip_key",
        "oncall_incidents.diagnostic_hash",  # fingerprint of the simulation file
        "podcast_episodes.audio_key",  # location of the WAV in the per-account storage
        "resources.local_key",
        "boards.scribe_key",
        "journal_entries.ref_key",
        "briefs.offer_keys",
        # Language model token counters, and a CV's keywords.
        "llm_calls.tokens_in",
        "llm_calls.tokens_out",
        "sessions.tokens_in",
        "sessions.tokens_out",
        "memory_chunks.token_count",
        "cv_reviews.keywords_to_gap",
        # Phase 10: sha256 of a proposal's file, fingerprint of an error (anti-repetition),
        # the teacher's token counter and the MCP token id (never its value nor its hash:
        # `mcp_tokens.hash` is excluded from the export by its model).
        "ide_notes.base_hash",
        "ide_notes.error_key",
        "ide_runs.error_signature",  # same: fingerprint of an error
        "ide_sessions.teacher_tokens",
        "mcp_calls.token_id",
        "mcp_confirmations.token_id",
        "surprise_interview_settings.token_id",  # row id of the Nod token
        "telegram_review_settings.token_id",  # row id of the Nod token
        "mcp_relay_pairings.token_id",  # row id of the dedicated token
    }
)


def _exported(info: Mapping[Any, Any]) -> bool:
    """Only `False` (the boolean) excludes: `"false"`, `0` or `None` exclude nothing, and the
    guard then sees the column."""
    return info.get(EXPORT, True) is not False


def all_user_tables() -> list[Table]:
    """Every table that has a `user_id` column, in dependency order."""
    return [table for table in Base.metadata.sorted_tables if "user_id" in table.c]


def user_tables() -> list[Table]:
    """The tables to export, in dependency order: those of `Base.metadata` that have a
    `user_id` column, except those their model excludes (`info={"export": False}`)."""
    return [table for table in all_user_tables() if _exported(table.info)]


def exported_columns(table: Table) -> list[Column[Any]]:
    """The columns of `table` that are exported: all, except those their model excludes."""
    return [column for column in table.c if _exported(column.info)]


def unreviewed_secret_columns(metadata: MetaData = Base.metadata) -> list[str]:
    """`table.column` of every exported column whose name suggests a secret and that is not in
    `REVIEWED_NOT_SECRET`: the guard that forces a decision when a column is added."""
    found = [
        f"{table.name}.{column.name}"
        for table in metadata.sorted_tables
        if "user_id" in table.c and _exported(table.info)
        for column in exported_columns(table)
        if SECRET_NAME.search(column.name)
    ]
    return sorted(name for name in found if name not in REVIEWED_NOT_SECRET)


def json_default(value: Any) -> Any:
    """The types `json.dumps` does not know: bytes as base64, decimals and ids as text,
    durations in seconds, sets as lists. An unknown type raises `TypeError` (an export that
    silently loses a column would be worse)."""
    if isinstance(value, bytes | bytearray | memoryview):
        return base64.b64encode(bytes(value)).decode("ascii")
    if isinstance(value, Decimal | UUID):
        return str(value)
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, set | frozenset):
        return sorted(value, key=str)
    raise TypeError(f"{type(value).__name__} is not exportable")


_CONVERTED = (bytes, bytearray, memoryview, Decimal, UUID, timedelta, set, frozenset)


def _cell(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return json_default(value) if isinstance(value, _CONVERTED) else value


def row_json(row: Mapping[str, Any]) -> dict[str, Any]:
    """A row ready for `json.dumps`: dates and times in ISO 8601, the types JSON does not know
    converted (`json_default`), the rest as is (JSON columns are already dicts and lists)."""
    return {name: _cell(value) for name, value in row.items()}
