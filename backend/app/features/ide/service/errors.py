"""Les erreurs de la feature `ide` (messages en français, jamais une sortie ni un fichier)."""

from typing import Any

from app.core.errors import AppError


def session_not_found() -> AppError:
    return AppError("session_not_found", "Séance introuvable.", 404)


def exercise_not_found() -> AppError:
    return AppError("exercise_not_found", "Exercice introuvable.", 404)


def run_not_found() -> AppError:
    return AppError("run_not_found", "Exécution introuvable.", 404)


def note_not_found() -> AppError:
    return AppError("note_not_found", "Note introuvable.", 404)


def run_in_progress(run_id: str) -> AppError:
    return AppError(
        "run_in_progress",
        "Une exécution est déjà en cours : attends sa fin.",
        409,
        {"run_id": run_id},
    )


def sandbox_unavailable() -> AppError:
    return AppError(
        "sandbox_unavailable",
        "Le bac à sable n'est pas disponible pour le moment : réessaie dans un instant.",
        503,
    )


def run_refused() -> AppError:
    return AppError(
        "run_refused", "Ces fichiers ne peuvent pas être exécutés (taille, nombre ou noms).", 422
    )


def entry_missing() -> AppError:
    return AppError(
        "entry_missing", "Le fichier d'entrée doit faire partie des fichiers de la séance.", 422
    )


def files_too_large() -> AppError:
    return AppError("files_too_large", "Les fichiers dépassent la taille permise.", 422)


def note_invalid(message: str, details: dict[str, Any] | None = None) -> AppError:
    return AppError("note_invalid", message, 422, details)


def note_stale(file_hash: str | None) -> AppError:
    """`details.file_hash` : l'empreinte actuelle du fichier (sha256), pour recommencer."""
    return AppError(
        "note_stale",
        "Le code a changé depuis cette proposition : elle ne s'applique plus.",
        409,
        {"file_hash": file_hash},
    )


def note_closed() -> AppError:
    return AppError("note_closed", "Cette proposition est déjà traitée.", 409)


def not_a_proposal() -> AppError:
    return AppError("not_a_proposal", "Cette note n'est pas une proposition.", 409)


def entry_invalid() -> AppError:
    return AppError("entry_invalid", "Le nom du fichier d'entrée n'est pas permis.", 422)
