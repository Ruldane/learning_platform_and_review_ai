"""The context sent to the professor (10.A3), bounded by the code: a single file (never a
second), the window of +/-30 lines around the line at issue (or the cursor), the last 40 lines
of the error output (2,000 characters at most) and the thread of the last 12 messages (4,000
characters at most). Never the whole project or the whole history. Named, adjustable
constants."""

import hashlib
import re
from dataclasses import dataclass, field

from app.agents.tools.ide_port import NoteView, RunView, TeachInputs

WINDOW_LINES = 30  # on each side of the line at issue
LINE_CHARS = 200  # a longer line is cut (minified code, pasted data)
ERROR_LINES = 40
ERROR_CHARS = 2_000
EXCHANGES = 12  # thread messages: January's questions and answers, the most recent
EXCHANGE_CHARS = 400
THREAD_CHARS = 4_000  # the whole thread; the oldest messages drop first
PATHS_CHARS = 2_000

_FRAME = re.compile(r'File "(?P<path>[^"]+)", line (?P<line>\d+)')
_PYTEST = re.compile(r"^(?P<path>[^\s:]+\.py):(?P<line>\d+):")


@dataclass(frozen=True)
class TeacherContext:
    path: str  # the only file shown
    focus: int  # the line at issue (at least 1)
    first_line: int  # first line of the window
    last_line: int
    line_count: int  # lines of the whole file
    window: str  # numbered lines "12 | code"
    base_hash: str  # sha256 of the whole file (fingerprint of a proposal, P9)
    error_tail: str  # end of the last run's output; empty if there is none
    exchanges: list[str]  # the thread, the last 12 messages (the oldest first)
    project_paths: list[str] = field(default_factory=list)


def file_hash(text: str) -> str:
    """The hexadecimal sha256 of the UTF-8 content, the IDE service's one (P9)."""
    return hashlib.sha256(text.encode()).hexdigest()


def lines_of(text: str) -> list[str]:
    """The lines of a file (at least one: an empty file has one line to fill)."""
    parts = text.split("\n")
    if text.endswith("\n"):
        parts.pop()
    return parts or [""]


def _user_file(path: str, names: set[str]) -> str | None:
    normal = path.replace("\\", "/")
    if normal in names:
        return normal
    return max((name for name in names if normal.endswith("/" + name)), key=len, default=None)


def _mentioned_file(question: str | None, names: set[str]) -> str | None:
    if not question:
        return None
    normal = question.replace("\\", "/")
    for name in sorted(names, key=lambda path: (-len(path), path)):
        if re.search(rf"(?<![\w./-]){re.escape(name)}(?![\w/-]|\.[\w])", normal):
            return name
    return None


def _catalog(names: set[str]) -> list[str]:
    seen: list[str] = []
    remaining = PATHS_CHARS
    for path in sorted(names):
        size = len(path) + 3  # list prefix and line break
        if size > remaining:
            break
        seen.append(path)
        remaining -= size
    return seen


def error_place(output: str, names: set[str]) -> tuple[str, int] | None:
    """The last place of January's code in the output: Python traceback frame, otherwise pytest
    failure line."""
    found: tuple[str, int] | None = None
    for text in output.splitlines():
        match = _FRAME.search(text) or _PYTEST.match(text)
        if match and (name := _user_file(match["path"], names)):
            found = (name, int(match["line"]))
    return found


def focus_of(
    inputs: TeachInputs, file_path: str | None, cursor_line: int | None, question: str | None = None
) -> tuple[str, int]:
    """The file and the line: those January shows, otherwise the place of the error, otherwise
    the input file."""
    names = set(inputs.files)
    named = _mentioned_file(question, names)
    if named is not None and named != file_path:
        return named, 1
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
    """The last 40 lines of the output, 2,000 characters at most (the end is kept)."""
    if run is None or not run.output.strip():
        return ""
    tail = "\n".join(run.output.splitlines()[-ERROR_LINES:])
    return tail[-ERROR_CHARS:]


def _exchange(note: NoteView) -> str:
    who = "January" if note.author == "user" else note.author
    return f"{who} ({note.kind}): {' '.join(note.text.split())[:EXCHANGE_CHARS]}"


def _thread(notes: list[NoteView], current_question: str | None) -> list[str]:
    """The thread in order: at most `EXCHANGES` messages and `THREAD_CHARS` characters (the most
    recent is kept). The question being asked is given separately: not twice."""
    kept = [note for note in notes if note.kind != "reference"]
    last = kept[-1] if kept else None
    if last and last.kind == "question" and last.text.strip() == (current_question or "").strip():
        kept = kept[:-1]
    lines = [_exchange(note) for note in kept[-EXCHANGES:]]
    while len(lines) > 1 and sum(len(line) for line in lines) > THREAD_CHARS:
        lines.pop(0)
    return lines


def build_context(
    inputs: TeachInputs,
    *,
    file_path: str | None = None,
    cursor_line: int | None = None,
    question: str | None = None,
) -> TeacherContext:
    """The context of a call: a single window of a single file, the end of the last run's
    output, the thread of the last 12 messages (excluding references)."""
    path, focus = focus_of(inputs, file_path, cursor_line, question)
    text = inputs.files[path]
    window, first, last, count = _window(text, focus)
    return TeacherContext(
        path=path,
        focus=min(max(focus, 1), count),
        first_line=first,
        last_line=last,
        line_count=count,
        window=window,
        base_hash=file_hash(text),
        error_tail=error_tail(inputs.run),
        exchanges=_thread(inputs.notes, question),
        project_paths=_catalog(set(inputs.files)),
    )
