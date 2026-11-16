"""Les erreurs de la feature `projects` (messages en français, jamais une donnée du rendu)."""

from app.core.errors import AppError


def project_not_found() -> AppError:
    return AppError("project_not_found", "Projet introuvable.", 404)


def project_not_ready() -> AppError:
    return AppError(
        "project_not_ready",
        "L'énoncé de ce projet n'est pas encore écrit : attends-le avant de rendre ton travail.",
        409,
    )


def review_in_progress(session_id: str | None) -> AppError:
    return AppError(
        "review_in_progress",
        "Ton rendu est en cours d'évaluation : attends son résultat.",
        409,
        {"session_id": session_id},
    )


def project_validated() -> AppError:
    return AppError(
        "project_validated", "Ce projet est déjà validé : il ne se rend pas une seconde fois.", 409
    )


def invalid_submission(fields: list[str]) -> AppError:
    """422 : les champs du rendu à corriger, jamais leur valeur."""
    return AppError(
        "validation_error",
        "Requête invalide : vérifie les champs signalés.",
        422,
        {"fields": fields},
    )


def screenshot_too_large() -> AppError:
    return AppError("file_too_large", "Capture trop volumineuse : 5 Mo au maximum par image.", 413)


def screenshot_not_found() -> AppError:
    return AppError("screenshot_not_found", "Capture introuvable.", 404)


def review_unavailable() -> AppError:
    return AppError(
        "review_unavailable",
        "L'évaluation n'a pas pu démarrer : ton rendu n'est pas gardé, réessaie dans un instant.",
        503,
    )


def brief_unavailable() -> AppError:
    return AppError(
        "brief_unavailable",
        "L'énoncé n'a pas pu être relancé : réessaie dans un instant.",
        503,
    )


def brief_not_failed() -> AppError:
    return AppError("brief_not_failed", "L'énoncé de ce projet n'est pas en échec.", 409)


def draft_not_found() -> AppError:
    return AppError("draft_not_found", "Ce brouillon n'existe pas pour ce projet.", 404)


def project_not_validated() -> AppError:
    return AppError(
        "project_not_validated", "Seul un projet validé peut entrer dans ton profil.", 409
    )


def entry_already_added() -> AppError:
    return AppError("entry_already_added", "Ce projet est déjà dans ton profil maître.", 409)


def profile_required() -> AppError:
    return AppError(
        "profile_required",
        "Valide d'abord ton profil maître : le projet s'y ajoute comme une nouvelle version.",
        409,
    )


def profile_projects_full() -> AppError:
    return AppError(
        "profile_projects_full",
        "Ton profil maître a déjà 20 projets : retires-en un avant d'en ajouter un.",
        409,
    )
