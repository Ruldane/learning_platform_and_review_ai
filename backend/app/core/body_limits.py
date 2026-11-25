"""Size of import bodies, bounded before any parsing (413): one middleware per import path.
Moved out of `app.main` (D139) to keep it short."""

from fastapi import FastAPI

from app.core.limits import BodySizeLimit
from app.features.cv.service.profile_import import MAX_PROFILE_FILE_BYTES, TOO_LARGE_MESSAGE
from app.features.memory.service.upload import MAX_UPLOAD_BYTES
from app.providers.speech.base import RECORDING_LIMIT

# Body of an import: the file (20 MB) plus the multipart envelope and the other fields.
_UPLOAD_BODY_MAX = MAX_UPLOAD_BYTES + 1024 * 1024
# Body of a board edit: full Excalidraw scene (`serializeAsJSON`, `files` may carry an image)
# and its note (D87).
BOARD_BODY_MAX = 2 * 1024 * 1024
# Master profile import: CV and LinkedIn (10 MB each), the note and the envelope (D124).
PROFILE_IMPORT_BODY_MAX = 2 * MAX_PROFILE_FILE_BYTES + 1024 * 1024
TEMPLATE_BODY_MAX = MAX_PROFILE_FILE_BYTES + 1024 * 1024  # template: the CV and its name
# Project submission: five 5 MB screenshots, the description, the link and the envelope (D166).
PROJECT_BODY_MAX = 5 * 5 * 1024 * 1024 + 1024 * 1024


def add_body_limits(app: FastAPI, prefix: str) -> None:
    """Size of import bodies, bounded before any parsing (413); `prefix`: the API routes'
    prefix."""
    app.add_middleware(BodySizeLimit, path=f"{prefix}/documents", max_bytes=_UPLOAD_BODY_MAX)
    app.add_middleware(
        BodySizeLimit, path=f"{prefix}/brain/sync/folders", max_bytes=_UPLOAD_BODY_MAX
    )
    app.add_middleware(
        BodySizeLimit,
        path=f"{prefix}/calendar",
        max_bytes=4096,
        code="calendar_request_too_large",
        message="The Calendar request is too large.",
    )
    app.add_middleware(BodySizeLimit, path=f"{prefix}/oncall/incidents", max_bytes=64 * 1024)
    app.add_middleware(BodySizeLimit, path=f"{prefix}/mcp/relay", max_bytes=1024)
    app.add_middleware(
        BodySizeLimit,
        path=f"{prefix}/voice",
        max_bytes=RECORDING_LIMIT,
        code="voice_recording_too_large",
        message="Recording too large.",
    )
    app.add_middleware(BodySizeLimit, path=f"{prefix}/ide/terminals", max_bytes=32 * 1024)
    app.add_middleware(BodySizeLimit, path=f"{prefix}/ide/sessions", max_bytes=1_500_000)
    app.add_middleware(  # CV and LinkedIn, 10 MB each (D124)
        BodySizeLimit,
        path=f"{prefix}/profile/import",
        max_bytes=PROFILE_IMPORT_BODY_MAX,
        message=TOO_LARGE_MESSAGE,
    )
    app.add_middleware(  # original CV of a template, 10 MB (D126)
        BodySizeLimit,
        path=f"{prefix}/cv/templates",
        max_bytes=TEMPLATE_BODY_MAX,
        message=TOO_LARGE_MESSAGE,
    )
    app.add_middleware(
        BodySizeLimit,
        path=f"{prefix}/boards",
        max_bytes=BOARD_BODY_MAX,
        code="board_too_large",
        message="Board too large: 2 MiB at most.",
    )
    app.add_middleware(  # screenshots of a project submission: 5 x 5 MB (D166)
        BodySizeLimit,
        path=f"{prefix}/projects",
        max_bytes=PROJECT_BODY_MAX,
        message="Submission too large: 5 screenshots of 5 MB at most.",
    )
