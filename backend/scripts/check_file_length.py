"""Contrôle de longueur : 300 lignes max par fichier, 50 par fonction."""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

MAX_FILE_LINES = 300
MAX_FUNCTION_LINES = 50


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    kind: Literal["file", "function"]
    name: str | None
    count: int


def _function_violations(path: Path, source: str, max_function_lines: int) -> list[Violation]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []  # ruff signale déjà les erreurs de syntaxe
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        end = node.end_lineno or node.lineno
        count = end - node.lineno + 1  # `lineno` désigne `def`, pas les décorateurs
        if count > max_function_lines:
            violations.append(Violation(path, node.lineno, "function", node.name, count))
    return violations


def check_paths(
    paths: list[Path],
    max_file_lines: int = MAX_FILE_LINES,
    max_function_lines: int = MAX_FUNCTION_LINES,
) -> list[Violation]:
    violations: list[Violation] = []
    for path in paths:
        if path.suffix != ".py":
            continue
        source = path.read_text(encoding="utf-8")
        count = len(source.splitlines())
        if count > max_file_lines:
            violations.append(Violation(path, 1, "file", None, count))
        violations.extend(_function_violations(path, source, max_function_lines))
    return violations


def _describe(v: Violation) -> str:
    if v.kind == "file":
        return f"{v.path}: fichier de {v.count} lignes (max {MAX_FILE_LINES})"
    return f"{v.path}:{v.line}: fonction {v.name} de {v.count} lignes (max {MAX_FUNCTION_LINES})"


def main(argv: list[str]) -> int:
    violations = check_paths([Path(arg) for arg in argv])
    for violation in violations:
        print(_describe(violation), file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
