"""Web research API schemas: the month's Brave counter and a session's sources."""

from pydantic import BaseModel, ConfigDict

from app.db.models.research import PageStatus, SourceKind, SourceVerdict

# The literal types are re-exported: a router does not import `app.db` (contract 1b).
__all__ = [
    "BraveUsageOut",
    "PageStatus",
    "SearchUsageOut",
    "SourceKind",
    "SourceOut",
    "SourceVerdict",
]


class BraveUsageOut(BaseModel):
    """Brave requests of the UTC calendar month (`month`: "YYYY-MM") for the current key."""

    has_key: bool
    used: int
    cap: int
    month: str


class SearchUsageOut(BaseModel):
    brave: BraveUsageOut


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    title: str | None
    author: str | None
    lang: str | None
    published: str | None
    status: PageStatus
    verdict: SourceVerdict
    score: int | None
    reason: str | None
    kind: SourceKind  # `person`: practitioner spotted by the Scout (phase 4, D82)
