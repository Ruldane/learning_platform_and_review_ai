"""An error's signature (P8, professor anti-repetition): the exception type and the last frame of
the user's code, never the message (it changes with the values)."""

import hashlib
import re

_TRACEBACK = "Traceback (most recent call last):"
_FRAME = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+)')
_EXCEPTION = re.compile(r"^(?P<type>[A-Za-z_][\w.]*)(?::|$)")
# A pytest failure (`-q`): "tests/test_a.py:12: AssertionError".
_PYTEST = re.compile(r"^(?P<path>[^\s:]+\.py):(?P<line>\d+): (?P<type>[A-Z][\w.]*)\b")


def _user_file(path: str, user_files: set[str]) -> str | None:
    """The user's file this path points to (`/work/<id>/main.py` or `main.py`)."""
    normal = path.replace("\\", "/")
    if normal in user_files:
        return normal
    for name in user_files:
        if normal.endswith("/" + name):
            return name
    return None


def _digest(kind: str, file: str, line: str) -> str:
    return hashlib.sha1(f"{kind}|{file}:{line}".encode()).hexdigest()  # noqa: S324  (fingerprint)


def error_signature(output: str, user_files: set[str]) -> str | None:
    """sha1 of `type|file:line` of the last frame of the user's code in the output's last
    traceback; `None` without a traceback, or without a frame in her files."""
    lines = output.splitlines()
    frames: list[tuple[int, str, str]] = []  # (line index, file, line)
    for rank, text in enumerate(lines):
        if text.startswith(_TRACEBACK):
            frames = []
        found = _FRAME.match(text)
        if found and (name := _user_file(found["path"], user_files)):
            frames.append((rank, name, found["line"]))
    if frames:
        rank, name, line = frames[-1]
        kind = "Error"
        for text in lines[rank + 1 :]:
            match = _EXCEPTION.match(text)
            if match:
                kind = match["type"].rsplit(".", 1)[-1]
                break
        return _digest(kind, name, line)
    for text in reversed(lines):
        match = _PYTEST.match(text)
        if match and (name := _user_file(match["path"], user_files)):
            return _digest(match["type"].rsplit(".", 1)[-1], name, match["line"])
    return None
