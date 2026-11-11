import re
from pathlib import Path

ENV_EXAMPLE = Path(__file__).resolve().parents[3] / ".env.example"
KEY_VALUE = re.compile(r"^[A-Z][A-Z0-9_]*=[^\s#]*$")


def _assignments() -> list[str]:
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    return [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def test_env_example_has_no_inline_comments() -> None:
    # Docker Compose lit « KEY=   # texte » comme la valeur « # texte ».
    for line in _assignments():
        assert "#" not in line.partition("=")[2], line


def test_env_example_lines_are_key_value() -> None:
    lines = _assignments()
    assert lines
    for line in lines:
        assert KEY_VALUE.match(line), line
