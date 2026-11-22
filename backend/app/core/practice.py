"""Repères agrégés et version du contenu d’un exercice."""

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

RECENT_PRACTICE = 12
MAX_QUIZ_ELAPSED_MS = 24 * 60 * 60 * 1000

VersionRelation = Literal["same", "changed", "unknown"]


class PracticeSummary(BaseModel):
    id: str
    created_at: datetime
    version: VersionRelation
    elapsed_ms: int | None
    errors: int | None
    progress: int | None
    total: int | None
    score_percent: int | None = None


def content_version(*values: object) -> str:
    canonical = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def compare_versions(current: str | None, previous: str | None) -> VersionRelation:
    if current is None or previous is None:
        return "unknown"
    return "same" if current == previous else "changed"
