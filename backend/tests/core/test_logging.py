import logging

import pytest

from app.core.logging import RedactingFilter, configure_logging
from app.core.security import KnownSecrets


def test_known_secret_is_redacted(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging("INFO", lambda: ["ma-cle-tres-secrete"])
    logging.getLogger("t").info("appel avec %s", "ma-cle-tres-secrete")
    assert "ma-cle-tres-secrete" not in caplog.text and "***" in caplog.text


def test_key_pattern_is_redacted(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging("INFO", lambda: [])
    logging.getLogger("t").error("Erreur: sk-ant-api03-ABCDEFGHIJKLMNOPQRST")
    assert "ABCDEFGHIJKLMNOPQRST" not in caplog.text


def test_secret_in_exception_traceback_is_redacted(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging("INFO", lambda: ["ma-cle-tres-secrete"])
    try:
        raise ValueError("échec avec ma-cle-tres-secrete")
    except ValueError:
        logging.getLogger("t").exception("boum")
    assert "boum" in caplog.text and "ValueError" in caplog.text
    assert "ma-cle-tres-secrete" not in caplog.text


def test_secret_in_mapping_or_extra_args_is_redacted(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging("INFO", lambda: ["ma-cle-tres-secrete"])
    logging.getLogger("t").info("a=%s b=%s", "x", ["ma-cle-tres-secrete"])
    assert "ma-cle-tres-secrete" not in caplog.text


def test_configure_logging_is_idempotent() -> None:
    root = logging.getLogger()
    configure_logging("INFO", lambda: [])
    handler_count = len(root.handlers)
    configure_logging("INFO", lambda: [])
    assert len(root.handlers) == handler_count
    for handler in root.handlers:
        assert sum(isinstance(f, RedactingFilter) for f in handler.filters) <= 1


def test_secrets_are_read_lazily(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging("INFO", KnownSecrets.values)
    KnownSecrets.add("cle-ajoutee-apres-coup")
    logging.getLogger("t").info("voici cle-ajoutee-apres-coup")
    assert "cle-ajoutee-apres-coup" not in caplog.text
