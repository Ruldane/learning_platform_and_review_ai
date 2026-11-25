"""Static mapping of Python APIs and targeted replacement of Markdown fences."""

import ast
from collections import Counter
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


def _bindings(tree: ast.Module) -> Counter[str]:
    names: Counter[str] = Counter()
    for child in ast.walk(tree):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store | ast.Del):
            names[child.id] += 1
        elif isinstance(child, ast.arg):
            names[child.arg] += 1
        elif (
            isinstance(
                child,
                ast.FunctionDef
                | ast.AsyncFunctionDef
                | ast.ClassDef
                | ast.ExceptHandler
                | ast.MatchAs
                | ast.MatchStar,
            )
            and child.name
        ):
            names[child.name] += 1
        elif isinstance(child, ast.MatchMapping) and child.rest:
            names[child.rest] += 1
    return names


def _imports(tree: ast.Module, bindings: Counter[str]) -> dict[str, str]:
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
    return {local: path for local, path in aliases.items() if local not in bindings}


def _resolve(
    node: ast.AST,
    aliases: dict[str, str],
    instances: dict[str, tuple[int, str]] | None = None,
) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    if origin := aliases.get(node.id):
        return ".".join([origin, *reversed(parts)])
    if parts and instances and (instance := instances.get(node.id)):
        assigned_at, origin = instance
        if node.lineno > assigned_at:
            return ".".join([origin, *reversed(parts)])
    return None


def _instances(
    tree: ast.Module, aliases: dict[str, str], bindings: Counter[str]
) -> dict[str, tuple[int, str]]:
    instances: dict[str, tuple[int, str]] = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or not isinstance(statement.value, ast.Call):
            continue
        if len(statement.targets) != 1 or not isinstance(target := statement.targets[0], ast.Name):
            continue
        constructor = _resolve(statement.value.func, aliases)
        # Limited to imported constructors, assigned only once at block level.
        if (
            bindings[target.id] == 1
            and constructor
            and constructor.rsplit(".", 1)[-1][:1].isupper()
        ):
            instances[target.id] = (statement.end_lineno or statement.lineno, constructor)
    return instances


def python_symbols(code: str) -> frozenset[str]:
    if len(code) > MAX_EXAMPLE_CHARS:
        return frozenset()
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return frozenset()
    bindings = _bindings(tree)
    aliases = _imports(tree, bindings)
    instances = _instances(tree, aliases, bindings)
    return frozenset(
        path
        for node in ast.walk(tree)
        if isinstance(node, ast.Name | ast.Attribute)
        and isinstance(node.ctx, ast.Load)
        and (path := _resolve(node, aliases, instances)) is not None
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
