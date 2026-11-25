"""Web research errors. No message quotes a query or a URL (SPEC 17.2)."""

from typing import Literal

from app.core.errors import AppError

QUOTA_CODE = "web_quota_reached"
# Brave requests per UTC calendar month and per key, all users combined (SPEC 11.3).
BRAVE_MONTHLY_CAP = 900

_QUOTA_MESSAGES = {
    "queries": "Limit of {cap} queries reached for this session.",
    "pages": "Limit of {cap} pages read reached for this session.",
}


class WebQuotaReached(AppError):
    """Session cap reached (SPEC 10.4): `kind` says which."""

    def __init__(self, cap: int, kind: Literal["queries", "pages"]) -> None:
        message = _QUOTA_MESSAGES[kind].format(cap=cap)
        super().__init__(QUOTA_CODE, message, 429, {"cap": cap, "kind": kind})
        self.cap = cap
        self.kind = kind


class NoSearchProvider(AppError):
    """All the providers of the fallback order failed, or none found a result."""

    def __init__(self) -> None:
        super().__init__("search_unavailable", "No search engine answered.", 503)


def empty_query() -> AppError:
    """Empty query, or empty once cleaned of any personal data: fixed message."""
    return AppError("search_query_empty", "The query is empty after removing personal data.", 422)


def source_not_found() -> AppError:
    return AppError("source_not_found", "Source not found.", 404)
