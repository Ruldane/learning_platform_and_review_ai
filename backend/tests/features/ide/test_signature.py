"""La signature d'une erreur (anti-répétition du professeur) : type, fichier et ligne du dernier
cadre du code de l'utilisatrice, jamais le message."""

import re

from app.features.ide.service import error_signature
from tests.features.ide.support import TRACE

USER_FILES = {"main.py", "test_main.py"}


def test_signature_ignores_variable_parts_of_message() -> None:
    other = TRACE.replace("division by zero", "unsupported value 42 at 0x7f3a")
    assert error_signature(TRACE, USER_FILES) == error_signature(other, USER_FILES)
    # le dossier de travail change à chaque exécution : pas de différence non plus
    moved = TRACE.replace("/work/9c1/", "/work/ab7/")
    assert error_signature(moved, USER_FILES) == error_signature(TRACE, USER_FILES)


def test_signature_depends_on_type_file_and_line() -> None:
    base = error_signature(TRACE, USER_FILES)
    assert base is not None and re.fullmatch(r"[0-9a-f]{40}", base)
    assert error_signature(TRACE.replace("line 3,", "line 4,"), USER_FILES) != base
    assert error_signature(TRACE.replace("ZeroDivisionError", "TypeError"), USER_FILES) != base
    assert error_signature(TRACE.replace("main.py", "test_main.py"), USER_FILES) != base


def test_signature_none_without_traceback() -> None:
    assert error_signature("bonjour\n", USER_FILES) is None
    assert error_signature("", USER_FILES) is None
    # une trace qui ne passe par aucun fichier de l'utilisatrice
    stdlib = TRACE.replace("/work/9c1/main.py", "/usr/lib/python3.12/json/__init__.py")
    assert error_signature(stdlib, USER_FILES) is None


def test_signature_takes_last_user_frame_and_last_traceback() -> None:
    deeper = (
        TRACE.replace(
            "ZeroDivisionError",
            '  File "/usr/lib/python3.12/json/__init__.py", line 346, in loads\n'
            "    return _default_decoder.decode(s)\n"
            "ZeroDivisionError",
        )
        + "\n"
    )
    assert error_signature(deeper, USER_FILES) == error_signature(TRACE, USER_FILES)
    chained = (
        "Traceback (most recent call last):\n"
        '  File "main.py", line 1, in <module>\n'
        "    boom()\n"
        "KeyError: 'a'\n"
        "\nDuring handling of the above exception, another exception occurred:\n\n" + TRACE
    )
    assert error_signature(chained, USER_FILES) == error_signature(TRACE, USER_FILES)


def test_signature_of_syntax_error_and_pytest_failure() -> None:
    syntax = (
        '  File "/work/x/main.py", line 3\n    print(\n         ^\n'
        "SyntaxError: '(' was never closed\n"
    )
    assert error_signature(syntax, USER_FILES) is not None
    failure = "FAILED test_main.py::test_a\ntest_main.py:12: AssertionError\n1 failed in 0.1s\n"
    one = error_signature(failure, USER_FILES)
    assert one is not None
    assert one != error_signature(failure.replace(":12:", ":13:"), USER_FILES)
    assert error_signature("main.py:3: in helper\n", USER_FILES) is None
