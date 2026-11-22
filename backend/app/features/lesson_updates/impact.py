"""Correspondance statique des API de Python et remplacement ciblé des clôtures Markdown."""

import ast
from dataclasses import dataclass

from markdown_it import MarkdownIt

_PARSER = MarkdownIt("commonmark", {"html": True})
_PYTHON = frozenset({"python", "python3", "py"})
MAX_EXAMPLE_CHARS = 3500


@dataclass(frozen=True)
class Example:
    block: int
    start: int
    stop: int
    code: str
    symbols: frozenset[str]


def _imports(tree: ast.Module) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                aliases[alias.asname or root] = alias.name if alias.asname else root
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                if alias.name != "*":
                    aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    for child in ast.walk(tree):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store | ast.Del):
            aliases.pop(child.id, None)
        elif isinstance(child, ast.arg):
            aliases.pop(child.arg, None)
        elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            aliases.pop(child.name, None)
    return aliases


def _resolve(node: ast.AST, aliases: dict[str, str]) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name) and (origin := aliases.get(node.id)):
        return ".".join([origin, *reversed(parts)])
    return None


def python_symbols(code: str) -> frozenset[str]:
    if len(code) > MAX_EXAMPLE_CHARS:
        return frozenset()
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return frozenset()
    aliases = _imports(tree)
    return frozenset(
        path
        for node in ast.walk(tree)
        if isinstance(node, ast.Name | ast.Attribute)
        and isinstance(node.ctx, ast.Load)
        and (path := _resolve(node, aliases)) is not None
    )


def examples_in(markdown: str) -> list[Example]:
    lines = markdown.splitlines()
    examples = []
    block = 0
    for token in _PARSER.parse(markdown):
        if token.type != "fence" or token.level != 0 or token.info.strip().lower() not in _PYTHON:
            continue
        block += 1
        if token.map is not None and token.content.strip():
            start, stop = token.map
            if not lines[stop - 1].lstrip().startswith(token.markup):
                continue
            code = token.content.rstrip("\n")
            examples.append(Example(block, start + 1, stop - 1, code, python_symbols(code)))
    return examples


def replace_examples(markdown: str, examples: list[Example], replacements: dict[int, str]) -> str:
    lines = markdown.splitlines(keepends=True)
    for block in reversed(examples):
        if block.block in replacements:
            lines[block.start : block.stop] = [replacements[block.block].rstrip() + "\n"]
    return "".join(lines)
