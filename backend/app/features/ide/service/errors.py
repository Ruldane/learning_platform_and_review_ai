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


def mcp_ide_write_off() -> AppError:
    """Claude n'écrit dans les fichiers que si January a allumé l'interrupteur (jamais de contenu
    dans le message)."""
    return AppError(
        "mcp_ide_write_off",
        "January n'a pas autorisé Claude à écrire dans ses fichiers : l'interrupteur de l'IDE "
        "est éteint. Propose plutôt une correction dans une note.",
        403,
    )


def base_hash_required() -> AppError:
    return AppError(
        "base_hash_required",
        "Écrire un fichier demande base_hash : le sha256 du contenu actuel de ce fichier, lu dans "
        "file_hashes de la séance (l'empreinte du texte vide pour un nouveau fichier).",
        422,
    )


def stale_base() -> AppError:
    """L'empreinte donnée n'est plus celle du fichier : January a écrit depuis la lecture."""
    return AppError(
        "stale_base",
        "Le fichier a changé depuis ta lecture : relis la séance avant de réécrire ce fichier.",
        409,
    )


def mcp_write_one_file() -> AppError:
    return AppError("mcp_write_one_file", "Écris un seul fichier à la fois.", 422)


def mcp_prefs_forbidden() -> AppError:
    return AppError(
        "mcp_prefs_forbidden",
        "Les préférences de l'IDE se règlent dans l'interface, jamais par le MCP.",
        403,
    )
