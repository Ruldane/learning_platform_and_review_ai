import logging
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from typing import Any

REDACTED = "***"
# `sk-…` only at the start of a word (« risk-assessment-framework » stays readable); `tmcp_…`:
# the MCP server tokens, even before their first presentation after a restart.
_KEY_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{16,}|tmcp_[A-Za-z0-9_-]{20,}")
# uvicorn logs: they do not propagate up to the root.
_OWN_HANDLER_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")
# Libraries whose logs would quote a URL or a document extract (spec 17.2):
# httpx writes « HTTP Request: GET <full URL> » at INFO on each request and redirect;
# pdfminer, trafilatura and htmldate quote fragments at WARNING; `httpx2` (the Z.ai SDK)
# writes the API URL at INFO on each call.
_QUIET_LOGGERS = {
    "httpx": logging.WARNING,
    "httpx2": logging.WARNING,
    "httpcore": logging.WARNING,
    "pdfminer": logging.ERROR,
    "trafilatura": logging.ERROR,
    "htmldate": logging.ERROR,
    # « Running job … executed successfully » every 6 h: our tasks log themselves.
    "apscheduler": logging.WARNING,
}


class RedactingFilter(logging.Filter):
    """Replaces the known secrets and key patterns with `***` (message, arguments, traces)."""

    def __init__(self, get_secrets: Callable[[], Iterable[str]]) -> None:
        super().__init__()
        self._get_secrets = get_secrets

    def redact(self, text: str) -> str:
        # The longest first: a secret contained in another must not half-hide it.
        for secret in sorted(set(self._get_secrets()), key=len, reverse=True):
            if secret:
                text = text.replace(secret, REDACTED)
        return _KEY_PATTERN.sub(REDACTED, text)

    def _redact_value(self, value: Any) -> Any:
        """Masks `value` if it contains a secret; otherwise returns it as is (type kept)."""
        if isinstance(value, str):
            return self.redact(value)
        try:
            text = str(value)
        except Exception:  # object whose __str__ fails: the formatting fails the same way
            return value
        redacted = self.redact(text)
        # A dict, a list or an object containing a secret becomes a masked string;
        # without a secret, the argument keeps its type (e.g. `%d` of uvicorn for the HTTP code).
        return value if redacted == text else redacted

    def filter(self, record: logging.LogRecord) -> bool:
        # The structure of `args` is kept: uvicorn's AccessFormatter depends on it (5-tuple).
        record.msg = self._redact_value(record.msg)
        args = record.args
        if isinstance(args, tuple):
            record.args = tuple(self._redact_value(a) for a in args)
        elif isinstance(args, Mapping):
            record.args = {k: self._redact_value(v) for k, v in args.items()}
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = self.redact(record.exc_text)
        if record.stack_info:
            record.stack_info = self.redact(record.stack_info)
        return True


class AccessQueryFilter(logging.Filter):
    """Removes the query string from the path in uvicorn's access log: a filter
    `?tag=…&author=…` is user content (spec 17.2). Set on the `uvicorn.access` logger
    itself, it applies whatever the handler. `args` keeps its shape
    (5-tuple expected by `AccessFormatter`)."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            record.args = (*args[:2], args[2].split("?", 1)[0], *args[3:])
        return True


def _install_access_filter() -> None:
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, AccessQueryFilter) for f in access.filters):
        access.addFilter(AccessQueryFilter())


def _install(handler: logging.Handler, get_secrets: Callable[[], Iterable[str]]) -> None:
    for existing in [f for f in handler.filters if isinstance(f, RedactingFilter)]:
        handler.removeFilter(existing)
    handler.addFilter(RedactingFilter(get_secrets))


def configure_logging(level: str, get_secrets: Callable[[], Iterable[str]]) -> None:
    """Sets the level, masks the secrets on all handlers and removes the query strings from the
    access log. Idempotent."""
    _install_access_filter()
    root = logging.getLogger()
    root.setLevel(level.upper())
    for name, quiet_level in _QUIET_LOGGERS.items():
        logging.getLogger(name).setLevel(quiet_level)
    if not root.handlers:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(stream)
    handlers = list(root.handlers)
    for name in _OWN_HANDLER_LOGGERS:
        handlers.extend(logging.getLogger(name).handlers)
    for handler in handlers:
        _install(handler, get_secrets)
