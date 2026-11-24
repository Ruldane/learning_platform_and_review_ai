"""Errors of the `projects` feature (never a piece of submission data)."""

from app.core.errors import AppError


def project_not_found() -> AppError:
    return AppError("project_not_found", "Project not found.", 404)


def project_not_ready() -> AppError:
    return AppError(
        "project_not_ready",
        "This project's brief is not written yet: wait for it before submitting your work.",
        409,
    )


def review_in_progress(session_id: str | None, message: str | None = None) -> AppError:
    return AppError(
        "review_in_progress",
        message or "Your submission is being reviewed: wait for the result.",
        409,
        {"session_id": session_id},
    )


def project_validated() -> AppError:
    return AppError(
        "project_validated",
        "This project is already validated: it cannot be submitted a second time.",
        409,
    )


def invalid_submission(fields: list[str]) -> AppError:
    """422: the submission fields to fix, never their value."""
    return AppError(
        "validation_error",
        "Invalid request: check the flagged fields.",
        422,
        {"fields": fields},
    )


def screenshot_too_large() -> AppError:
    return AppError("file_too_large", "Screenshot too large: 5 MB at most per image.", 413)


def screenshot_not_found() -> AppError:
    return AppError("screenshot_not_found", "Screenshot not found.", 404)


def review_unavailable() -> AppError:
    return AppError(
        "review_unavailable",
        "The review could not start: your submission was not kept, try again in a moment.",
        503,
    )


def brief_unavailable() -> AppError:
    return AppError(
        "brief_unavailable",
        "The brief could not be restarted: try again in a moment.",
        503,
    )


def brief_not_failed() -> AppError:
    return AppError("brief_not_failed", "This project's brief has not failed.", 409)


def draft_not_found() -> AppError:
    return AppError("draft_not_found", "This draft does not exist for this project.", 404)


def project_not_validated(
    message: str = "Only a validated project can enter your profile.",
) -> AppError:
    return AppError("project_not_validated", message, 409)


def entry_already_added() -> AppError:
    return AppError("entry_already_added", "This project is already in your master profile.", 409)


def profile_required() -> AppError:
    return AppError(
        "profile_required",
        "Validate your master profile first: the project is added to it as a new version.",
        409,
    )


def profile_projects_full() -> AppError:
    return AppError(
        "profile_projects_full",
        "Your master profile already has 20 projects: remove one before adding another.",
        409,
    )


def drafts_present() -> AppError:
    return AppError("drafts_present", "This project already has its drafts.", 409)


def drafts_unavailable() -> AppError:
    return AppError(
        "drafts_unavailable",
        "The drafts could not be restarted: try again in a moment.",
        503,
    )


def project_exists() -> AppError:
    return AppError(
        "project_exists", "This module already has its project: edit its brief (PATCH).", 409
    )


def project_not_editable() -> AppError:
    return AppError(
        "project_not_editable",
        "This project's brief can no longer be edited: it is submitted, reviewed or validated.",
        409,
    )


def module_skipped() -> AppError:
    return AppError("module_skipped", "This module is skipped: it has no project.", 409)
