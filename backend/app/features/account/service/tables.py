"""Quelles tables partent dans l'export, avec quelles colonnes, et la forme JSON d'une ligne.

Les tables se lisent dans `Base.metadata` : toute table qui a une colonne `user_id` est exportée,
y compris celle qu'une feature ajoutera demain, sans rien changer ici. **Ce qui ne sort jamais se
déclare dans le modèle**, là où la colonne naît : `info={"export": False}` sur la colonne
(`api_keys.encrypted_key`) ou sur la table (`__table_args__ = {"info": {"export": False}}`,
`auth_sessions`). Une garde (`unreviewed_secret_columns`) force cette décision pour toute colonne
dont le nom évoque un secret (limite : un secret rangé dans une colonne JSON n'a pas de nom à
repérer, seule la revue le voit, D185 n° 10 b). `all_user_tables` recense les tables à effacer et
la file technique qui termine la purge de l'ancien compte Google."""

import base64
import re
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Column, MetaData, Table

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from app.db.base import Base

EXPORT = "export"  # clé de `info` : `False` écarte la colonne ou la table de l'export

# Un nom de colonne qui ressemble à un secret oblige à choisir : `info={"export": False}`, ou
# l'écrire ici avec la raison de n'être pas un secret.
SECRET_NAME = re.compile(
    r"key|token|secret|hash|password|passwd|cookie|credential|cipher|encrypted|salt|nonce"
    r"|private|fingerprint|bearer|passphrase|signature|authoriz|totp|mfa"
    r"|(?:^|_)(?:otp|auth|jwt|pwd|pin)(?:_|$)",
    re.I,
)
REVIEWED_NOT_SECRET = frozenset(
    {
        # Empreintes de contenu, d'adresse ou de requête (dédoublonnage), jamais un secret.
        "flashcards.front_hash",
        "job_postings.text_hash",
        "memory_items.content_hash",
        "documents.source_hash",
        "sources.url_hash",
        "resources.url_hash",
        "web_cache.key_hash",
        "web_queries.query_hash",
        "atlas_hypotheses.label_key",  # empreinte du libellé normalisé de l’hypothèse
        "atlas_observations.evidence_key",  # repère stable d’une preuve du compte
        "shared_week_proposals.fingerprint",  # empreinte du planning proposé
        "shared_week_proposals.selection_key",  # empreinte du groupe de programmes
        "plan_versions.base_fingerprint",  # empreinte des lignes du plan (détecte un plan changé)
        # Clés de rangement : un nom de fichier du stockage ou un repère de ligne.
        "documents.storage_key",
        "cv_versions.storage_key",
        "lessons.pdf_key",
        "program_books.pdf_key",
        "program_books.epub_key",
        "portfolio_drafts.html_key",
        "portfolio_drafts.zip_key",
        "oncall_incidents.diagnostic_hash",  # empreinte du fichier de simulation
        "podcast_episodes.audio_key",  # emplacement du WAV dans le stockage par compte
        "resources.local_key",
        "boards.scribe_key",
        "journal_entries.ref_key",
        "briefs.offer_keys",
        # Compteurs de jetons du modèle de langage, et mots-clés d'un CV.
        "llm_calls.tokens_in",
        "llm_calls.tokens_out",
        "sessions.tokens_in",
        "sessions.tokens_out",
        "memory_chunks.token_count",
        "cv_reviews.keywords_to_gap",
        # Phase 10 : sha256 du fichier d'une proposition, empreinte d'une erreur (anti-répétition),
        # compteur de jetons du professeur et identifiant du jeton MCP (jamais sa valeur ni son
        # empreinte : `mcp_tokens.hash` est écartée de l'export par son modèle).
        "ide_notes.base_hash",
        "ide_notes.error_key",
        "ide_runs.error_signature",  # idem : empreinte d'une erreur
        "ide_sessions.teacher_tokens",
        "mcp_calls.token_id",
        "mcp_confirmations.token_id",
        "surprise_interview_settings.token_id",  # identifiant de ligne du jeton Nod
        "telegram_review_settings.token_id",  # identifiant de ligne du jeton Nod
        "mcp_relay_pairings.token_id",  # identifiant de ligne du jeton dédié
    }
)


def _exported(info: Mapping[Any, Any]) -> bool:
    """Seul `False` (le booléen) écarte : `"false"`, `0` ou `None` n'écartent rien, et la garde
    voit alors la colonne."""
    return info.get(EXPORT, True) is not False


def all_user_tables() -> list[Table]:
    """Toutes les tables qui ont une colonne `user_id`, dans l'ordre des dépendances."""
    return [table for table in Base.metadata.sorted_tables if "user_id" in table.c]


def user_tables() -> list[Table]:
    """Les tables à exporter, dans l'ordre des dépendances : celles de `Base.metadata` qui ont
    une colonne `user_id`, sauf celles que leur modèle écarte (`info={"export": False}`)."""
    return [table for table in all_user_tables() if _exported(table.info)]


def exported_columns(table: Table) -> list[Column[Any]]:
    """Les colonnes de `table` qui sortent : toutes, sauf celles que leur modèle écarte."""
    return [column for column in table.c if _exported(column.info)]


def unreviewed_secret_columns(metadata: MetaData = Base.metadata) -> list[str]:
    """`table.colonne` de toute colonne exportée dont le nom évoque un secret et qui n'est pas
    dans `REVIEWED_NOT_SECRET` : la garde qui force une décision à l'ajout d'une colonne."""
    found = [
        f"{table.name}.{column.name}"
        for table in metadata.sorted_tables
        if "user_id" in table.c and _exported(table.info)
        for column in exported_columns(table)
        if SECRET_NAME.search(column.name)
    ]
    return sorted(name for name in found if name not in REVIEWED_NOT_SECRET)


def json_default(value: Any) -> Any:
    """Les types que `json.dumps` ne connaît pas : octets en base64, décimaux et identifiants en
    texte, durées en secondes, ensembles en listes. Un type inconnu lève `TypeError` (un export
    qui perd une colonne en silence serait pire)."""
    if isinstance(value, bytes | bytearray | memoryview):
        return base64.b64encode(bytes(value)).decode("ascii")
    if isinstance(value, Decimal | UUID):
        return str(value)
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, set | frozenset):
        return sorted(value, key=str)
    raise TypeError(f"{type(value).__name__} n'est pas exportable")


_CONVERTED = (bytes, bytearray, memoryview, Decimal, UUID, timedelta, set, frozenset)


def _cell(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return json_default(value) if isinstance(value, _CONVERTED) else value


def row_json(row: Mapping[str, Any]) -> dict[str, Any]:
    """Une ligne prête pour `json.dumps` : dates et heures en ISO 8601, les types que JSON ne
    connaît pas convertis (`json_default`), le reste tel quel (les colonnes JSON sont déjà des
    dictionnaires et des listes)."""
    return {name: _cell(value) for name, value in row.items()}
