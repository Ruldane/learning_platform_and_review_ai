"""Le contexte envoyé au professeur (10.A3), borné par le code : un seul fichier (jamais un
second), la fenêtre de ±30 lignes autour de la ligne en cause (ou du curseur), les 40 dernières
lignes de la sortie d'erreur (2 000 caractères au plus) et les 4 derniers échanges. Jamais tout le
projet ni tout l'historique. Constantes nommées, réglables."""

import hashlib
import re
from dataclasses import dataclass

from app.agents.tools.ide_port import NoteView, RunView, TeachInputs

WINDOW_LINES = 30  # de chaque côté de la ligne en cause
LINE_CHARS = 200  # une ligne plus longue est coupée (code minifié, donnée collée)
ERROR_LINES = 40
ERROR_CHARS = 2_000
EXCHANGES = 4
EXCHANGE_CHARS = 400

_FRAME = re.compile(r'File "(?P<path>[^"]+)", line (?P<line>\d+)')
_PYTEST = re.compile(r"^(?P<path>[^\s:]+\.py):(?P<line>\d+):")


@dataclass(frozen=True)
class TeacherContext:
    path: str  # le seul fichier montré
    focus: int  # la ligne en cause (au moins 1)
    first_line: int  # première ligne de la fenêtre
    last_line: int
    line_count: int  # lignes du fichier entier
    window: str  # lignes numérotées « 12 | code »
    base_hash: str  # sha256 du fichier entier (empreinte d'une proposition, P9)
    error_tail: str  # fin de la sortie de la dernière exécution ; vide s'il n'y en a pas
    exchanges: list[str]  # les 4 dernières notes (les plus anciennes d'abord)


def file_hash(text: str) -> str:
    """Le sha256 hexadécimal du contenu en UTF-8, celui du service de l'IDE (P9)."""
    return hashlib.sha256(text.encode()).hexdigest()


def lines_of(text: str) -> list[str]:
    """Les lignes d'un fichier (au moins une : un fichier vide a une ligne à remplir)."""
    parts = text.split("\n")
    if text.endswith("\n"):
        parts.pop()
    return parts or [""]


def _user_file(path: str, names: set[str]) -> str | None:
    normal = path.replace("\\", "/")
    if normal in names:
        return normal
    return next((name for name in sorted(names) if normal.endswith("/" + name)), None)


def error_place(output: str, names: set[str]) -> tuple[str, int] | None:
    """Le dernier endroit du code de January dans la sortie : cadre d'une trace Python, sinon
    ligne d'échec de pytest."""
    found: tuple[str, int] | None = None
    for text in output.splitlines():
        match = _FRAME.search(text) or _PYTEST.match(text)
        if match and (name := _user_file(match["path"], names)):
            found = (name, int(match["line"]))
    return found


def focus_of(
    inputs: TeachInputs, file_path: str | None, cursor_line: int | None
) -> tuple[str, int]:
    """Le fichier et la ligne : ceux que January montre, sinon l'endroit de l'erreur, sinon le
    fichier d'entrée."""
    names = set(inputs.files)
    if file_path in names:
        return str(file_path), cursor_line or 1
    if inputs.run is not None and (place := error_place(inputs.run.output, names)):
        return place
    return (inputs.entry if inputs.entry in names else sorted(names)[0]), cursor_line or 1


def _window(text: str, focus: int) -> tuple[str, int, int, int]:
    lines = lines_of(text)
    focus = min(max(focus, 1), len(lines))
    first, last = max(1, focus - WINDOW_LINES), min(len(lines), focus + WINDOW_LINES)
    width = len(str(last))
    body = "\n".join(
        f"{number:>{width}} | {lines[number - 1][:LINE_CHARS]}" for number in range(first, last + 1)
    )
    return body, first, last, len(lines)


def error_tail(run: RunView | None) -> str:
    """Les 40 dernières lignes de la sortie, 2 000 caractères au plus (la fin est gardée)."""
    if run is None or not run.output.strip():
        return ""
    tail = "\n".join(run.output.splitlines()[-ERROR_LINES:])
    return tail[-ERROR_CHARS:]


def _exchange(note: NoteView) -> str:
    return f"{note.author} ({note.kind}) : {' '.join(note.text.split())[:EXCHANGE_CHARS]}"


def build_context(
    inputs: TeachInputs, *, file_path: str | None = None, cursor_line: int | None = None
) -> TeacherContext:
    """Le contexte d'un appel : une seule fenêtre d'un seul fichier, la fin de la sortie de la
    dernière exécution, les 4 dernières notes qui ne sont pas des renvois."""
    path, focus = focus_of(inputs, file_path, cursor_line)
    text = inputs.files[path]
    window, first, last, count = _window(text, focus)
    notes = [note for note in inputs.notes if note.kind != "reference"][-EXCHANGES:]
    return TeacherContext(
        path=path,
        focus=min(max(focus, 1), count),
        first_line=first,
        last_line=last,
        line_count=count,
        window=window,
        base_hash=file_hash(text),
        error_tail=error_tail(inputs.run),
        exchanges=[_exchange(note) for note in notes],
    )
