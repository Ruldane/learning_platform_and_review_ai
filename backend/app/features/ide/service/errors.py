"""Errors of the `ide` feature (messages never include an output or a file)."""

from app.core.errors import AppError


def session_not_found() -> AppError:
    return AppError("session_not_found", "Session not found.", 404)


def exercise_not_found() -> AppError:
    return AppError("exercise_not_found", "Exercise not found.", 404)


def run_not_found() -> AppError:
    return AppError("run_not_found", "Run not found.", 404)


def note_not_found() -> AppError:
    return AppError("note_not_found", "Note not found.", 404)


def run_in_progress(run_id: str) -> AppError:
    return AppError(
        "run_in_progress",
        "A run is already in progress: wait for it to finish.",
        409,
        {"run_id": run_id},
    )


def sandbox_unavailable() -> AppError:
    return AppError(
        "sandbox_unavailable",
        "The sandbox is not available right now: try again in a moment.",
        503,
    )


def run_refused() -> AppError:
    return AppError("run_refused", "These files cannot be run (size, count or names).", 422)


def entry_missing() -> AppError:
    return AppError("entry_missing", "The entry file must be one of the session's files.", 422)


def files_too_large() -> AppError:
    return AppError("files_too_large", "The files exceed the allowed size.", 422)


def note_invalid(message: str) -> AppError:
    return AppError("note_invalid", message, 422)


def note_stale() -> AppError:
    """The file changed: the hash is not returned, the caller re-reads the session
    (`file_hashes`)."""
    return AppError(
        "note_stale",
        "The code changed since this proposal: re-read the session (file_hashes) before "
        "proposing another one.",
        409,
    )


def note_closed() -> AppError:
    return AppError("note_closed", "This proposal has already been handled.", 409)


def not_a_proposal() -> AppError:
    return AppError("not_a_proposal", "This note is not a proposal.", 409)


def entry_invalid() -> AppError:
    return AppError("entry_invalid", "The entry file name is not allowed.", 422)


def mcp_ide_write_off() -> AppError:
    """Claude writes to the files only if January turned the switch on (never any content in
    the message)."""
    return AppError(
        "mcp_ide_write_off",
        "January has not allowed Claude to write to her files: the IDE switch is off. "
        "Propose a fix in a note instead.",
        403,
    )


def mcp_ide_test_file() -> AppError:
    """An exercise's tests belong to January: Claude does not rewrite them (the check would pass
    without the code being right)."""
    return AppError(
        "mcp_ide_test_file",
        "The exercise's tests belong to January: Claude does not write to them. Fix the code, "
        "or propose a fix in a note.",
        403,
    )


def base_hash_required() -> AppError:
    return AppError(
        "base_hash_required",
        "Writing a file requires base_hash: the sha256 of the file's current content, read from "
        "the session's file_hashes (the hash of the empty text for a new file).",
        422,
    )


def stale_base() -> AppError:
    """The given hash no longer matches the file: January wrote since it was read."""
    return AppError(
        "stale_base",
        "The file changed since you read it: re-read the session before rewriting this file.",
        409,
    )


def files_changed(names: list[str]) -> AppError:
    """The interface save hits files Claude changed since the last read: only the names are
    returned, nothing is written."""
    return AppError(
        "stale_base",
        "Claude changed files since your last read: nothing was saved.",
        409,
        {"files": names},
    )


def mcp_write_one_file() -> AppError:
    return AppError("mcp_write_one_file", "Write one file at a time.", 422)


def mcp_prefs_forbidden() -> AppError:
    return AppError(
        "mcp_prefs_forbidden",
        "IDE preferences are set in the interface, never through MCP.",
        403,
    )


def mcp_gesture_forbidden() -> AppError:
    """Accepting or rejecting a proposal is January's gesture (it writes to her files)."""
    return AppError(
        "mcp_gesture_forbidden",
        "This gesture is reserved to January in the interface: propose a fix in a note.",
        403,
    )
