"""Validation lexicale des racines et chemins du relais. Le serveur ne les ouvre jamais."""

import re
from pathlib import PurePosixPath, PureWindowsPath

from app.core.errors import AppError

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_WINDOWS_ROOT = re.compile(r"^[A-Za-z]:[\\/]")
_TECHNICAL = frozenset(
    {
        ".obsidian",
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".pnpm-store",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".ipynb_checkpoints",
        ".idea",
        ".vscode",
        ".tox",
        ".nox",
        ".next",
    }
)


def root_path(path: str) -> str:
    root = PureWindowsPath(path) if _WINDOWS_ROOT.match(path) else PurePosixPath(path)
    if (
        not root.is_absolute()
        or path.startswith("//")
        or _CONTROL.search(path)
        or ".." in root.parts
        or root.name.lower() in _TECHNICAL
    ):
        raise AppError("brain_root_invalid", "Le dossier doit avoir un chemin local absolu.", 422)
    return str(root)


def relative_path(path: str) -> str:
    if (
        "\\" in path
        or ":" in path
        or _CONTROL.search(path)
        or any(
            not part or part in (".", "..") or part.lower() in _TECHNICAL
            for part in path.split("/")
        )
    ):
        raise AppError("brain_path_invalid", "Le chemin relatif de la note est refusé.", 422)
    return path
