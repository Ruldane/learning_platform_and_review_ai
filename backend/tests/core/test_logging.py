import logging

import pytest

from app.core.logging import AccessQueryFilter, RedactingFilter, configure_logging
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


def _access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET", path, "1.1", 200),
        None,
    )


def test_uvicorn_access_formatter_still_works_and_redacts() -> None:
    # Régression : `args` doit rester un 5-tuple, sinon AccessFormatter lève un TypeError.
    from uvicorn.logging import AccessFormatter

    handler = logging.Handler()
    handler.addFilter(RedactingFilter(lambda: ["ma-cle-tres-secrete"]))
    handler.setFormatter(AccessFormatter("%(levelprefix)s %(message)s", use_colors=False))
    record = _access_record("/api/v1/x?key=ma-cle-tres-secrete")
    assert handler.filter(record)
    out = handler.format(record)
    assert "ma-cle-tres-secrete" not in out and "***" in out
    assert out.endswith('"GET /api/v1/x?key=*** HTTP/1.1" 200')


def test_non_secret_args_keep_their_type() -> None:
    record = _access_record("/ok")
    RedactingFilter(lambda: ["ma-cle-tres-secrete"]).filter(record)
    assert record.args == ("127.0.0.1:5000", "GET", "/ok", "1.1", 200)
    assert isinstance(record.args, tuple) and isinstance(record.args[4], int)
    assert record.getMessage().endswith("200")


def test_secret_inside_non_str_args_is_redacted() -> None:
    class Holder:
        def __str__(self) -> str:
            return "Holder(ma-cle-tres-secrete)"

    record = logging.LogRecord(
        "t",
        logging.INFO,
        __file__,
        1,
        "%s %s %s",
        ({"k": "ma-cle-tres-secrete"}, ["ma-cle-tres-secrete"], Holder()),
        None,
    )
    RedactingFilter(lambda: ["ma-cle-tres-secrete"]).filter(record)
    assert "ma-cle-tres-secrete" not in record.getMessage()
    assert len(record.args) == 3  # type: ignore[arg-type]


def test_secret_in_mapping_style_args_is_redacted() -> None:
    record = logging.LogRecord(
        "t", logging.INFO, __file__, 1, "%(a)s %(n)d", ({"a": "ma-cle-tres-secrete", "n": 3},), None
    )
    RedactingFilter(lambda: ["ma-cle-tres-secrete"]).filter(record)
    assert record.getMessage() == "*** 3"


def test_libraries_that_would_quote_urls_or_documents_are_quieted() -> None:
    for name in ("httpx", "httpcore", "pdfminer", "trafilatura", "htmldate"):
        logging.getLogger(name).setLevel(logging.DEBUG)
    configure_logging("DEBUG", lambda: [])
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
    for name in ("pdfminer", "trafilatura", "htmldate"):
        assert logging.getLogger(name).level == logging.ERROR
    assert not logging.getLogger("pdfminer.pdfparser").isEnabledFor(logging.WARNING)


def test_access_log_drops_the_query_string() -> None:
    # Spec 17.2 : une étiquette ou un auteur filtrés (`?tag=…`) sont du contenu de l'utilisateur.
    configure_logging("INFO", lambda: [])
    configure_logging("INFO", lambda: [])  # idempotent : un seul filtre
    access = logging.getLogger("uvicorn.access")
    assert sum(isinstance(f, AccessQueryFilter) for f in access.filters) == 1
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append  # type: ignore[method-assign]
    access.addHandler(handler)
    try:
        record = _access_record("/api/v1/memory/items?tag=sant%C3%A9&author=moi")
        access.handle(record)
    finally:
        access.removeHandler(handler)
    assert [r.getMessage() for r in records] == [
        '127.0.0.1:5000 - "GET /api/v1/memory/items HTTP/1.1" 200'
    ]
    assert isinstance(records[0].args, tuple) and records[0].args[4] == 200


def test_httpx2_logger_is_quiet() -> None:
    """SDK de Z.ai : il journalise l'URL fixe de l'API en INFO à chaque appel."""
    configure_logging("INFO", lambda: [])
    assert logging.getLogger("httpx2").level == logging.WARNING
