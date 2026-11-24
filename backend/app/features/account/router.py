"""My data (SPEC 17.1, phase 9): export of all the user's data and "Delete everything". On
behalf of the current user, never another account; a 422 names the fields, never echoing the
confirmation received."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from starlette.requests import HTTPConnection

from app.agents.runtime.handle import AgentRuntime
from app.core.caller import MCP_IDENTITY
from app.core.deps import ConfirmedUserDep, CurrentUserDep, Db
from app.core.errors import AppError
from app.core.field_paths import FieldPathsRoute
from app.core.providers import MemoryProviders
from app.features.account.schemas import DELETE_CONFIRMATION, DeleteAccountIn
from app.features.account.service import (
    AccountRuntime,
    archive_size,
    build_export,
    export_filename,
    export_lock,
    stream_export,
    user_export_zone,
)
from app.features.account.service import (
    delete_account as erase_account,
)
from app.features.auth.service.cookies import clear_session_cookie
from app.features.postings.service.runtime import KeyLocks

router = APIRouter(prefix="/account", tags=["account"], route_class=FieldPathsRoute)

_ZIP: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {"application/zip": {}},
        "description": "The archive of all the data",
        "headers": {
            "Content-Disposition": {
                "description": (
                    '`attachment; filename="tremplin-export-YYYYMMDD.zip"`: the suggested'
                    " download name, the day being the user's local day."
                ),
                "schema": {"type": "string"},
            }
        },
    }
}


def get_account_runtime(conn: HTTPConnection) -> AccountRuntime:
    """Storage, vector index and agent engine from startup (`app.state`), plus the per-account
    locks, created on first request and kept for the application's lifetime."""
    state = conn.app.state
    locks: KeyLocks | None = getattr(state, "account_locks", None)
    if locks is None:
        locks = state.account_locks = KeyLocks()
    memory: MemoryProviders = state.memory_providers
    runtime: AgentRuntime = state.runtime
    return AccountRuntime(
        session_factory=state.session_factory,
        storage=memory.storage,
        index=memory.index,
        indexer=state.memory.indexer,
        runtime=runtime,
        locks=locks,
    )


AccountDep = Annotated[AccountRuntime, Depends(get_account_runtime)]


@router.get("/export", response_class=Response, responses=_ZIP)
async def export_account(current: CurrentUserDep, db: Db, rt: AccountDep) -> Response:
    """All the user's data in a zip archive `tremplin-export-YYYYMMDD.zip` (download):
    `manifest.json`, one table per JSON file (`tables/<table>.json`) and the uploaded files
    (`files/…`). API keys are never included (only their last four characters); neither vectors
    nor agent checkpoints (they can be recomputed)."""
    now = datetime.now(UTC)
    filename = export_filename(now, await user_export_zone(db, current.id))
    if MCP_IDENTITY.get() is not None:
        return Response(
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    async with export_lock(rt.locks, current.id):
        archive = await build_export(db, rt.storage, current.id, now)
    try:
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(archive_size(archive)),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        }
    except BaseException:
        archive.close()  # the response will not exist: the stream will never close it
        raise
    # The stream closes the file when done or if the client leaves; the background task
    # guarantees it even if the stream never started.
    return StreamingResponse(
        stream_export(archive),
        media_type="application/zip",
        headers=headers,
        background=BackgroundTask(archive.close),
    )


@router.post(
    "/delete",
    status_code=204,
    response_class=Response,
    responses={
        202: {"description": "Google account erased; the vector purge resumes in the background."},
        409: {"description": "`account_changed`: the identity no longer matches the session."},
        422: {
            "description": (
                "`confirmation_required`: confirm with SUPPRIMER; "
                "`account_identity_required`: give the displayed identity."
            )
        },
        503: {
            "description": (
                "`vector_store_unavailable`: Qdrant does not answer before the rows "
                "are deleted; "
                "`vector_purge_incomplete`: the local space is erased in the database, "
                "run the deletion again to remove the remaining vectors."
            )
        },
    },
)
async def delete_account(
    request: Request, body: DeleteAccountIn, current: ConfirmedUserDep, rt: AccountDep
) -> Response:
    """Delete everything: cancels running sessions, then erases the vectors, files, checkpoints
    and every row of the account. `confirm` must be `SUPPRIMER`, otherwise 422
    `confirmation_required`. The displayed identity must match the authenticated account.
    Local mode: the space stays usable, empty; Google mode: the account and the session
    disappear. The final vector purge may resume in the background (202)."""
    if body.confirm != DELETE_CONFIRMATION:
        raise AppError(
            "confirmation_required",
            "Type SUPPRIMER to confirm.",
            422,
            {"fields": ["confirm"]},
        )
    auth_mode = request.app.state.settings.auth_mode
    if body.expected_user_id is not None and body.expected_user_id != current.id:
        raise AppError("account_changed", "The signed-in account has changed.", 409)
    if body.expected_user_id is None and auth_mode == "google" and MCP_IDENTITY.get() is None:
        raise AppError(
            "account_identity_required",
            "Give the displayed account to confirm its deletion.",
            422,
            {"fields": ["expected_user_id"]},
        )
    complete = await erase_account(rt, current.id, auth_mode=auth_mode)
    response = Response(status_code=204 if complete else 202)
    if auth_mode == "google":
        clear_session_cookie(response)  # the session disappeared with the account
    return response
