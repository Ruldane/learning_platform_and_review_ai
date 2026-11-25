"""Kinds of module, no dependency: importable by the lessons without a cycle (D309)."""

from app.db.models.program import Module

VALIDATION_KIND = "validation"


def has_lesson(module: Module) -> bool:
    """A skipped or validation module (D220) has no lesson."""
    return not module.skipped and module.kind != VALIDATION_KIND
