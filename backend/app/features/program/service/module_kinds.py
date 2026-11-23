"""Sortes de module, sans dépendance : importable par les leçons sans cycle (D309)."""

from app.db.models.program import Module

VALIDATION_KIND = "validation"


def has_lesson(module: Module) -> bool:
    """Un module sauté ou de validation (D220) n'a pas de leçon."""
    return not module.skipped and module.kind != VALIDATION_KIND
