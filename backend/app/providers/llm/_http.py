"""HTTP calls for key checking and the model list, common to the providers.

Deliberately in plain `httpx` (and not through the providers' SDKs, which rely on
`httpx2` and escape `respx`): these calls are trivial and stay testable without network.
"""

from collections.abc import Mapping
from typing import Any

import httpx

from app.core.errors import AppError
from app.providers.llm.base import KeyTestResult

_TIMEOUT = httpx.Timeout(15.0)
_INVALID_KEY = "The API key contains invalid characters."


def _headers_are_valid(headers: dict[str, str]) -> bool:
    """Header values must be printable ASCII (httpx encodes them as ASCII)."""
    return all(v.isascii() and v.isprintable() for v in headers.values())


def _provider_error_code(response: httpx.Response) -> str | None:
    """Provider error code (`{"error": {"code": ...}}`), or `None` if absent/unreadable."""
    try:
        code = response.json()["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return None
    return str(code) if isinstance(code, str | int) else None


def _error_message(label: str, response: httpx.Response, code_messages: Mapping[str, str]) -> str:
    """English message for a failure: nothing from the response body is copied (the key sometimes
    appears in it), only its error code is used to pick a known message."""
    code = _provider_error_code(response)
    if code is not None and code in code_messages:
        return code_messages[code]
    if response.status_code == 429:
        return f"{label}'s request limit or credit limit was reached. Try again later."
    return f"{label} returned an error ({response.status_code})."


async def check_key(
    label: str,
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
    code_messages: Mapping[str, str] | None = None,
) -> KeyTestResult:
    """Sends the check request. Never raises, never echoes the key back.

    `code_messages`: provider-specific messages, by error code of its response body.
    """
    if not _headers_are_valid(headers):
        return KeyTestResult(ok=False, message=_INVALID_KEY)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.request(method, url, headers=headers, json=body)
    except (httpx.HTTPError, httpx.InvalidURL, UnicodeError, ValueError):
        return KeyTestResult(ok=False, message=f"Could not reach {label}. Check your connection.")
    if response.status_code in (401, 403):
        return KeyTestResult(ok=False, message=f"{label} rejected the API key.")
    if not response.is_success:
        return KeyTestResult(ok=False, message=_error_message(label, response, code_messages or {}))
    return KeyTestResult(ok=True, message="API key is valid.")


def _unavailable(label: str) -> AppError:
    return AppError(
        "llm_models_unavailable",
        f"Could not retrieve the model list from {label}.",
        502,
        {"provider": label},
    )


async def get_model_page(
    label: str, url: str, headers: dict[str, str], params: dict[str, Any]
) -> tuple[list[str], str | None]:
    """A page of `GET /models`: (identifiers, next cursor or `None`).

    Any error (invalid key, network, status, unexpected body) becomes an English `AppError`
    that never contains the key.
    """
    if not _headers_are_valid(headers):
        raise _unavailable(label)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        page = response.json()
        ids = [m["id"] for m in page["data"]]
        if not all(isinstance(i, str) for i in ids):
            raise TypeError("invalid model identifier")
        more = page.get("has_more") and page.get("last_id")
        return ids, str(more) if more else None
    except (
        httpx.HTTPError,
        httpx.InvalidURL,
        UnicodeError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
    ) as exc:
        raise _unavailable(label) from exc
