"""Passages déterministes et bornés d'une copie Python du projet."""

from collections.abc import Iterator
from itertools import zip_longest
from pathlib import PurePosixPath

from app.agents.tools.code_trial_port import CodePassage

MAX_PASSAGE_BYTES = 1000
MAX_CONTEXT_BYTES = 12_000
MAX_PASSAGES = 24
PASSAGE_LINES = 12


def python_files(files: dict[str, str]) -> dict[str, str]:
    return {
        path: text
        for path, text in sorted(files.items())
        if PurePosixPath(path).suffix.casefold() == ".py"
        and all(not part.startswith(".") for part in PurePosixPath(path).parts)
        and text.strip()
    }


def _chunks(path: str, text: str) -> Iterator[CodePassage]:
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    for start in range(0, len(lines), PASSAGE_LINES):
        block = lines[start : start + PASSAGE_LINES]
        quote = "\n".join(block)
        if quote.strip() and len(quote.encode()) <= MAX_PASSAGE_BYTES:
            yield CodePassage(
                path=path, start_line=start + 1, end_line=start + len(block), text=quote
            )


def excerpts(files: dict[str, str]) -> list[CodePassage]:
    result: list[CodePassage] = []
    used = 0
    for group in zip_longest(*(_chunks(path, text) for path, text in files.items())):
        for item in group:
            if item is None:
                continue
            weight = len(item.model_dump_json().encode()) + 16
            if used + weight > MAX_CONTEXT_BYTES:
                continue
            result.append(item)
            used += weight
            if len(result) == MAX_PASSAGES:
                return result
    return result
