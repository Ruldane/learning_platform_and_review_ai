"""Python IDE API (phase 10, P1): exercises, sessions, runs, professor, notes, preferences and
usage. Surface laid down by 10.P; 10.A2 fills in exercises, sessions, runs and notes; 10.A3 fills
in `exercises/generate`, `teach` (the professor's cost gate), `preferences` and `usage`. On behalf
of the current user (404 on another user's object). Decisions on proposals require a
confirmation. MCP rights are set in the interface."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from starlette.requests import HTTPConnection

from app.core.caller import CallerDep
from app.core.deps import CurrentUserDep, Db, get_current_user
from app.core.field_paths import FieldPathsRoute
from app.features.ide.router_deps import Id, Ide
from app.features.ide.router_notebook import router as notebook_router
from app.features.ide.router_project import router as project_router
from app.features.ide.router_terminal import router as terminal_router
from app.features.ide.schemas import (
    ExerciseGenerateIn,
    ExerciseIn,
    ExerciseOut,
    ExercisePatch,
    FilesPutIn,
    IdeSessionOut,
    IdeSessionStarted,
    NoteIn,
    NoteOut,
    PreferencesIn,
    PreferencesOut,
    RunIn,
    RunOut,
    RunProgress,
    SessionCreateIn,
    SessionSummary,
    TeachIn,
    TeachOut,
    UsageOut,
)
from app.features.ide.service.errors import mcp_prefs_forbidden
from app.features.ide.service.teaching import TeachingService
from app.features.ide.service.usage import UsageService

router = APIRouter(
    prefix="/ide",
    tags=["ide"],
    route_class=FieldPathsRoute,
    dependencies=[Depends(get_current_user)],
)

router.include_router(project_router)
router.include_router(terminal_router)
router.include_router(notebook_router)


def teaching_service(conn: HTTPConnection, current: CurrentUserDep, db: Db) -> TeachingService:
    """The professor's cost gate; the session launcher is the application's."""
    return TeachingService(db, current.id, conn.app.state.launcher)


def usage_service(current: CurrentUserDep, db: Db) -> UsageService:
    return UsageService(db, current.id)


Teaching = Annotated[TeachingService, Depends(teaching_service)]
Usage = Annotated[UsageService, Depends(usage_service)]
_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "Not found (or not mine)."}}
_RUN_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`session_not_found`"},
    409: {"description": "`run_in_progress`: a run is already in progress"},
    422: {"description": "`entry_missing`, `run_refused`"},
    503: {"description": "`sandbox_unavailable`: the sandbox is stopped"},
}
_NOTE_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`session_not_found`"},
    409: {"description": "`note_stale`: the file changed since it was read"},
    422: {"description": "`note_invalid`: range, file or hash (re-read `file_hashes`)"},
}
_ACCEPT_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`note_not_found`"},
    409: {
        "description": "`note_stale` (the note becomes `stale`), `note_closed`, `not_a_proposal`"
    },
}


@router.get("/exercises", response_model=list[ExerciseOut])
async def list_exercises(ide: Ide) -> list[ExerciseOut]:
    """My exercises, most recent first."""
    return await ide.list_exercises()


@router.post("/exercises", response_model=ExerciseOut, status_code=201)
async def create_exercise(body: ExerciseIn, ide: Ide) -> ExerciseOut:
    """Adds a hand-written exercise (or one written by Claude: `origin` comes from the caller)."""
    return await ide.create_exercise(body)


@router.patch(
    "/exercises/{exercise_id}",
    response_model=ExerciseOut,
    responses={
        **_NOT_FOUND,
        422: {"description": "`entry_invalid` or fields to fix (`details.fields`)"},
    },
)
async def update_exercise(exercise_id: Id, body: ExercisePatch, ide: Ide) -> ExerciseOut:
    """Edits an exercise (statement, starter files, pytest tests) with no agent and no run."""
    return await ide.update_exercise(exercise_id, body)


@router.post("/exercises/generate", response_model=IdeSessionStarted, status_code=202)
async def generate_exercise(body: ExerciseGenerateIn, teaching: Teaching) -> IdeSessionStarted:
    """Has the agents generate an exercise: returns the session to follow right away. The
    exercise is stored only once its solution has been verified in the sandbox."""
    return await teaching.generate(body)


@router.delete(
    "/exercises/{exercise_id}", status_code=204, response_class=Response, responses=_NOT_FOUND
)
async def delete_exercise(exercise_id: Id, ide: Ide) -> Response:
    """Deletes an exercise (its sessions remain). 404 if it is not mine."""
    await ide.delete_exercise(exercise_id)
    return Response(status_code=204)


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(ide: Ide) -> list[SessionSummary]:
    """My code sessions, most recent first."""
    return await ide.list_sessions()


@router.post("/sessions", response_model=IdeSessionOut, status_code=201, responses=_NOT_FOUND)
async def create_session(body: SessionCreateIn, ide: Ide) -> IdeSessionOut:
    """Opens a session on an exercise, or a free session."""
    return await ide.open_session(body.exercise_id, body.title)


@router.get("/sessions/{session_id}", response_model=IdeSessionOut, responses=_NOT_FOUND)
async def get_session(session_id: Id, ide: Ide) -> IdeSessionOut:
    """A session with its files."""
    return await ide.get_session(session_id)


@router.put(
    "/sessions/{session_id}/files",
    response_model=IdeSessionOut,
    responses={
        403: {
            "description": "`mcp_ide_write_off`: Claude is not allowed to (switch); "
            "`mcp_ide_test_file`: a test file of the exercise"
        },
        404: {"description": "`session_not_found`"},
        409: {
            "description": "`stale_base`: a file changed since it was read "
            "(`details.files` on the interface side)"
        },
        422: {
            "description": "`entry_missing`, `entry_invalid`, `files_too_large`, "
            "`base_hash_required`, `mcp_write_one_file`"
        },
    },
)
async def put_files(session_id: Id, body: FilesPutIn, ide: Ide) -> IdeSessionOut:
    """Saves the session's files (at most 20, 200 KB): the interface replaces them all;
    Claude (MCP, switch on) writes one file with `base_hash`."""
    return await ide.save_files(
        session_id, body.files, body.entry, body.base_hash, body.base_hashes
    )


@router.get("/sessions/{session_id}/runs", response_model=list[RunOut], responses=_NOT_FOUND)
async def list_runs(session_id: Id, ide: Ide) -> list[RunOut]:
    """The session's last 20 runs, most recent first (read every 3 s by the open page: a run
    started by Claude shows up there)."""
    return await ide.list_runs(session_id)


@router.post(
    "/sessions/{session_id}/runs", response_model=RunOut, status_code=202, responses=_RUN_ERRORS
)
async def start_run(session_id: Id, body: RunIn, ide: Ide) -> RunOut:
    """Submits a run or a check to the sandbox (one per user)."""
    return await ide.start_run(session_id, body.kind, body.entry)


@router.get(
    "/runs/{run_id}",
    response_model=RunProgress,
    responses={
        404: {"description": "`run_not_found`"},
        503: {"description": "`sandbox_unavailable`"},
    },
)
async def read_run(run_id: Id, ide: Ide, after: Annotated[int, Query(ge=0)] = 0) -> RunProgress:
    """The run's output from byte `after` onwards (polled every 300 ms)."""
    return await ide.get_run(run_id, after)


@router.post(
    "/sessions/{session_id}/teach",
    response_model=TeachOut,
    status_code=202,
    responses={
        404: {"description": "`session_not_found`, `run_not_found`"},
        422: {"description": "Unknown trigger, or empty question"},
    },
)
async def teach(session_id: Id, body: TeachIn, teaching: Teaching) -> TeachOut:
    """Wakes the professor: a graph (`session_id`), a pointer to the previous note
    (`reference_note_id`) or nothing (`skipped`). The only route that starts the professor:
    neither saving files nor typing calls it."""
    return await teaching.teach(session_id, body)


@router.get("/sessions/{session_id}/notes", response_model=list[NoteOut], responses=_NOT_FOUND)
async def list_notes(session_id: Id, ide: Ide) -> list[NoteOut]:
    """The session's notes: hints, explanations, annotations, proposals, references."""
    return await ide.list_notes(session_id)


@router.post(
    "/sessions/{session_id}/notes",
    response_model=NoteOut,
    status_code=201,
    responses=_NOTE_ERRORS,
)
async def add_note(session_id: Id, body: NoteIn, ide: Ide) -> NoteOut:
    """Adds a note; the author is the caller (me, the professor, Claude)."""
    return await ide.add_note(session_id, body)


@router.post("/notes/{note_id}/accept", response_model=IdeSessionOut, responses=_ACCEPT_ERRORS)
async def accept_note(note_id: Id, ide: Ide) -> IdeSessionOut:
    """Applies a proposal to the file if it has not changed (otherwise 409 `note_stale`).
    An MCP call requires a confirmation in Tremplin."""
    return await ide.accept_note(note_id)


@router.post("/notes/{note_id}/reject", response_model=NoteOut, responses=_ACCEPT_ERRORS)
async def reject_note(note_id: Id, ide: Ide) -> NoteOut:
    """Rejects a proposal. An MCP call requires a confirmation in Tremplin."""
    return await ide.reject_note(note_id)


@router.get("/preferences", response_model=PreferencesOut)
async def get_preferences(usage: Usage) -> PreferencesOut:
    """Professor mode and style, idle timer, token caps."""
    return await usage.preferences()


@router.put(
    "/preferences",
    response_model=PreferencesOut,
    responses={403: {"description": "`mcp_prefs_forbidden`: never through MCP"}},
)
async def put_preferences(body: PreferencesIn, usage: Usage, caller: CallerDep) -> PreferencesOut:
    """Replaces the preferences (professor, Claude's write switch). An interface gesture:
    never from MCP, which must not set its own budget or its own rights."""
    if caller.kind == "mcp":
        raise mcp_prefs_forbidden()
    return await usage.save_preferences(body)


@router.get("/usage", response_model=UsageOut, responses=_NOT_FOUND)
async def get_usage(
    usage: Usage, session_id: Annotated[str | None, Query(max_length=36)] = None
) -> UsageOut:
    """The professor's tokens: session (if `session_id`), day, caps, on-demand mode."""
    return await usage.usage(session_id)
