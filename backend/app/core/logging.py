import logging
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from typing import Any

REDACTED = "***"
_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{16,}")
# Journaux de uvicorn : ils ne se propagent pas jusqu'à la racine.
_OWN_HANDLER_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


class RedactingFilter(logging.Filter):
    """Remplace les secrets connus et les motifs de clés par `***` (message, arguments, traces)."""

    def __init__(self, get_secrets: Callable[[], Iterable[str]]) -> None:
        super().__init__()
        self._get_secrets = get_secrets

    def redact(self, text: str) -> str:
        # Les plus longs d'abord : un secret contenu dans un autre ne doit pas le masquer à moitié.
        for secret in sorted(set(self._get_secrets()), key=len, reverse=True):
            if secret:
                text = text.replace(secret, REDACTED)
        return _KEY_PATTERN.sub(REDACTED, text)

    def _redact_value(self, value: Any) -> Any:
        """Masque `value` s'il contient un secret ; sinon le rend tel quel (type conservé)."""
        if isinstance(value, str):
            return self.redact(value)
        try:
            text = str(value)
        except Exception:  # objet dont __str__ échoue : le formatage échouera de même
            return value
        redacted = self.redact(text)
        # Un dict, une liste ou un objet contenant un secret devient une chaîne masquée ;
        # sans secret, l'argument garde son type (ex. `%d` d'uvicorn pour le code HTTP).
        return value if redacted == text else redacted

    def filter(self, record: logging.LogRecord) -> bool:
        # La structure de `args` est conservée : AccessFormatter d'uvicorn en dépend (5-tuple).
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


def _install(handler: logging.Handler, get_secrets: Callable[[], Iterable[str]]) -> None:
    for existing in [f for f in handler.filters if isinstance(f, RedactingFilter)]:
        handler.removeFilter(existing)
    handler.addFilter(RedactingFilter(get_secrets))


def configure_logging(level: str, get_secrets: Callable[[], Iterable[str]]) -> None:
    """Règle le niveau et masque les secrets sur tous les handlers. Idempotent."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    if not root.handlers:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(stream)
    handlers = list(root.handlers)
    for name in _OWN_HANDLER_LOGGERS:
        handlers.extend(logging.getLogger(name).handlers)
    for handler in handlers:
        _install(handler, get_secrets)
