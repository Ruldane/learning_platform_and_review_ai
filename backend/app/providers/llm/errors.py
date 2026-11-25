"""LLM call errors: which ones are worth retrying, and their readable message.

A single place translates the providers' errors (Anthropic and OpenAI SDKs, httpx) into English
messages: never the SDK's raw message nor the response body (a masked key sometimes appears there).
"""

from collections.abc import Mapping

import anthropic
import httpx
import openai

from app.core.errors import AppError

_TRANSIENT_STATUSES = frozenset({408, 409, 429})

# Messages by error code of the response body (`{"error": {"code": ...}}`), per provider.
PROVIDER_ERROR_CODES: Mapping[str, Mapping[str, str]] = {
    "glm": {  # Z.ai, codes returned with a 429 status
        "1113": "Insufficient Z.ai credit for this model.",
        "1305": "Z.ai is overloaded. Try again later.",
    },
    "openai": {
        "insufficient_quota": "OpenAI credit is exhausted. Top up the account or change models.",
    },
}
# Credit exhausted: a retry would fail the same way, so there is no point waiting.
_CREDIT_CODES = frozenset({"1113", "insufficient_quota"})
# Service overload returned as 429 (Z.ai 1305): retried like any 429, but reported as
# `llm_unavailable` (temporary outage), not as `llm_rate_limited` (limit or quota).
_OVERLOAD_CODES = frozenset({"1305"})

_TIMEOUTS = (
    anthropic.APITimeoutError,
    openai.APITimeoutError,
    httpx.TimeoutException,
    TimeoutError,
)
_CONNECTION = (
    anthropic.APIConnectionError,
    openai.APIConnectionError,
    httpx.TransportError,
    ConnectionError,
)


def is_timeout(exc: BaseException) -> bool:
    """Deadline exceeded (SDK, httpx, deadline): the request may have been processed, so it is
    billed."""
    return isinstance(exc, _TIMEOUTS)


def _transient_status(status: int) -> bool:
    return status in _TRANSIENT_STATUSES or status >= 500


def _status(exc: BaseException) -> int | None:
    if isinstance(exc, anthropic.APIStatusError | openai.APIStatusError):
        return exc.status_code
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return None


def _as_code(code: object) -> str | None:
    """An error code is a string, whatever type the SDK or the server gives."""
    if isinstance(code, bool) or not isinstance(code, str | int):
        return None
    return str(code)


def _body_code(exc: BaseException) -> str | None:
    """Error code of the response body (`error.code`) as a string, never its message.

    Never raises: an unread body (streamed response), an unreadable one, or one of another
    shape, gives `None`.
    """
    if isinstance(exc, openai.APIStatusError):
        return _as_code(exc.code)  # the SDK extracts it from `{"error": {...}}`
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            return _as_code(exc.response.json()["error"]["code"])
        except (ValueError, KeyError, TypeError, httpx.ResponseNotRead):
            return None
    return None


def is_transient(exc: BaseException) -> bool:
    """Network timeout, dropped connection, 429 (limit), 408/409 or 5xx: the same call may succeed
    later. A refused key, exhausted credit, an invalid request or a programming error cannot,
    so they are not retried."""
    if isinstance(exc, anthropic.APIConnectionError | openai.APIConnectionError):
        return True  # includes deadlines exceeded (APITimeoutError is a subclass of it)
    status = _status(exc)
    if status is not None:
        return _transient_status(status) and _body_code(exc) not in _CREDIT_CODES
    return isinstance(
        exc, httpx.TimeoutException | httpx.TransportError | ConnectionError | TimeoutError
    )


def _by_status(status: int, label: str, known: str | None, code: str | None) -> AppError:
    details = {"provider": label, "status": status}
    if status in (401, 403):
        message = f"{label} rejected the API key. Check it in Settings > Models and keys."
        return AppError("llm_key_rejected", message, 502, details)
    if status == 429:
        if code in _OVERLOAD_CODES:  # temporary overload, not a limit: D115 no. 17
            message = known or f"{label} is overloaded. Try again later."
            return AppError("llm_unavailable", message, 502, details)
        if code in _CREDIT_CODES:
            message = known or f"{label} credit is exhausted."
            return AppError("llm_credit_exhausted", message, 502, details)
        message = known or (
            f"{label}'s request limit or credit limit was reached. Try again later."
        )
        return AppError("llm_rate_limited", message, 502, details)
    if status >= 500:
        message = known or f"{label} is unavailable ({status}). Try again later."
        return AppError("llm_unavailable", message, 502, details)
    message = known or f"{label} rejected the request ({status})."
    return AppError("llm_request_rejected", message, 502, details)


def describe_provider_error(
    exc: BaseException, *, provider: str | None, label: str
) -> AppError | None:
    """Readable error for an outage of the `provider` provider (name, e.g. « glm ») shown as
    `label`;
    `None` if `exc` is not a provider error (it then follows its usual path).

    The message repeats neither the text of the exception nor the response body: only the HTTP
    status and the error code are used to choose a known message.
    """
    if isinstance(exc, _TIMEOUTS):  # before the connection: SDK timeouts are one case
        message = f"{label} did not respond in time. Try again later."
        return AppError("llm_timeout", message, 504, {"provider": label})
    if isinstance(exc, _CONNECTION):
        message = f"Could not reach {label}. Check your connection."
        return AppError("llm_unavailable", message, 502, {"provider": label})
    status = _status(exc)
    if status is None:
        return None
    code = _body_code(exc)
    known = PROVIDER_ERROR_CODES.get(provider or "", {}).get(code or "")
    return _by_status(status, label, known, code)
