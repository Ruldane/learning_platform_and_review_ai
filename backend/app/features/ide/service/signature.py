"""La signature d'une erreur (P8, anti-répétition du professeur) : le type de l'exception et le
dernier cadre du code de l'utilisatrice, jamais le message (il change avec les valeurs)."""

import hashlib
import re

_TRACEBACK = "Traceback (most recent call last):"
_FRAME = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+)')
_EXCEPTION = re.compile(r"^(?P<type>[A-Za-z_][\w.]*)(?::|$)")
# Une défaillance de pytest (`-q`) : « tests/test_a.py:12: AssertionError ».
_PYTEST = re.compile(r"^(?P<path>[^\s:]+\.py):(?P<line>\d+): (?P<type>[A-Z][\w.]*)\b")


def _user_file(path: str, user_files: set[str]) -> str | None:
    """Le fichier de l'utilisatrice que ce chemin désigne (`/work/<id>/main.py` ou `main.py`)."""
    normal = path.replace("\\", "/")
    if normal in user_files:
        return normal
    for name in user_files:
        if normal.endswith("/" + name):
            return name
    return None


def _digest(kind: str, file: str, line: str) -> str:
    return hashlib.sha1(f"{kind}|{file}:{line}".encode()).hexdigest()  # noqa: S324  (empreinte)


def error_signature(output: str, user_files: set[str]) -> str | None:
    """sha1 de `type|fichier:ligne` du dernier cadre du code de l'utilisatrice dans la dernière
    trace de la sortie ; `None` sans trace, ou sans cadre dans ses fichiers."""
    lines = output.splitlines()
    frames: list[tuple[int, str, str]] = []  # (rang de la ligne, fichier, ligne)
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
