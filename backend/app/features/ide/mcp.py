"""MCP declaration for `ide`: exercises, sessions, runs and notes. Claude reads, runs the code
and writes notes. It writes to January's files only if January has turned on the switch
(`mcp_can_write_files`, set in the interface only, `ide_write_file`, undoable); otherwise a fix
is a proposal that January accepts in the interface. It does not trigger the internal teacher
(API cost: Claude writes its own notes and exercises)."""

from app.mcp.base import FeatureMcp, McpAction, McpExclusion, McpGraph

MCP = FeatureMcp(
    feature="ide",
    actions=(
        McpAction("GET /ide/exercises", 1, "ide_list_exercises", "The Python IDE exercises."),
        McpAction(
            "POST /ide/exercises",
            2,
            "ide_create_exercise",
            "Creates an exercise (title, statement, starter files and tests).",
        ),
        McpAction(
            "PATCH /ide/exercises/{exercise_id}",
            2,
            "ide_update_exercise",
            "Direct write, no agent or run: edits an exercise (title, statement, starter and "
            "pytest test files, entry file).",
        ),
        McpAction(
            "DELETE /ide/exercises/{exercise_id}",
            3,
            "ide_delete_exercise",
            "Deletes an exercise: asks for confirmation.",
        ),
        McpAction("GET /ide/sessions", 1, "ide_list_sessions", "The coding sessions."),
        McpAction(
            "GET /ide/sessions/{session_id}",
            1,
            "ide_get_session",
            "A session: files, exercise, latest run.",
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "POST /ide/sessions",
            2,
            "ide_create_session",
            "Opens a coding session, free or on an exercise.",
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/runs",
            2,
            "ide_start_run",
            "Runs or checks a session's code in the sandbox (no network).",
            bucket="code_run",
        ),
        McpAction(
            "GET /ide/runs/{run_id}",
            1,
            "ide_read_run",
            "Reads a run's output (`after`: offset already read).",
        ),
        McpAction(
            "GET /ide/sessions/{session_id}/notes",
            1,
            "ide_list_notes",
            "A session's notes: hints, explanations, annotations, proposals.",
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/notes",
            2,
            "ide_add_note",
            "Writes a note in a session: hint, explanation, annotation or proposed fix "
            "(which January accepts or rejects in the interface).",
        ),
        McpAction(
            "GET /ide/preferences",
            1,
            "ide_get_preferences",
            "The IDE preferences (teacher mode, timer).",
        ),
        McpAction(
            "GET /ide/usage",
            1,
            "ide_get_usage",
            "The teacher's usage: session, day, caps.",
        ),
        McpAction(
            "GET /ide/sessions/{session_id}/runs",
            1,
            "ide_list_runs",
            "A session's last 20 runs (January's and yours), newest first.",
        ),
        McpAction(
            "PUT /ide/sessions/{session_id}/files",
            2,
            "ide_write_file",
            "Writes ONE session file (the whole content). Only if January has turned on the "
            "'Claude can write to my files' switch (otherwise 403 mcp_ide_write_off: propose "
            "a fix through a note instead). `base_hash` is required: the sha256 of the file's "
            "current content, given by `file_hashes` in `ide_get_session` (hash of the empty "
            "text for a new file). If January has written since your read: 409 stale_base, "
            "re-read the session. Never a test file of an exercise session (`test_*.py`, "
            "`*_test.py`, `conftest.py`): 403 mcp_ide_test_file, those are hers. Can be undone "
            "from 'MCP access'.",
            body_fields=frozenset({"files", "base_hash"}),
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/files",
            2,
            "ide_create_project_file",
            "Adds a file to the project if MCP writing has been allowed. "
            "Use the `files_version` from `ide_get_session`.",
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "PATCH /ide/sessions/{session_id}/files",
            2,
            "ide_rename_project_file",
            "Renames a project file if MCP writing has been allowed. "
            "Use the `files_version` from `ide_get_session`.",
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "DELETE /ide/sessions/{session_id}/files",
            3,
            "ide_delete_project_file",
            "Deletes a project file: asks for confirmation.",
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "POST /ide/notes/{note_id}/accept",
            3,
            "ide_accept_note",
            "Applies the fix proposed in the note. Asks for confirmation.",
        ),
        McpAction(
            "POST /ide/notes/{note_id}/reject",
            3,
            "ide_reject_note",
            "Rejects the fix proposed in the note. Asks for confirmation.",
        ),
        McpAction(
            "PUT /ide/sessions/{session_id}/tabs",
            2,
            "ide_save_project_tabs",
            "Remembers the open tabs and the selected file.",
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/terminal",
            2,
            "ide_open_terminal",
            "Opens the terminal in the network-free sandbox.",
            bucket="code_run",
        ),
        McpAction(
            "GET /ide/terminals/{run_id}",
            1,
            "ide_read_terminal",
            "Reads the terminal output in the sandbox.",
            untrusted=("output",),
        ),
        McpAction(
            "POST /ide/terminals/{run_id}/input",
            2,
            "ide_write_terminal_input",
            "Sends text to the network-free sandbox terminal.",
            bucket="code_run",
        ),
        McpAction(
            "DELETE /ide/terminals/{run_id}",
            3,
            "ide_close_terminal",
            "Closes the terminal. Asks for confirmation.",
            side_effects="external",
        ),
        McpAction(
            "GET /ide/sessions/{session_id}/notebook",
            1,
            "ide_read_notebook",
            "Reads the session notebook's cells.",
            untrusted=("cells[].source", "cells[].output"),
        ),
        McpAction(
            "PUT /ide/sessions/{session_id}/notebook",
            2,
            "ide_save_notebook",
            "Saves the notebook cells if MCP writing is allowed.",
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/notebook/run",
            2,
            "ide_run_notebook_cell",
            "Runs a notebook cell in the sandbox.",
            bucket="code_run",
        ),
        McpAction(
            "GET /ide/notebook-runs/{run_id}",
            1,
            "ide_read_notebook_run",
            "Reads the output of a notebook cell run.",
            untrusted=("output",),
        ),
    ),
    graphs=(McpGraph("ide_teacher", follow_only=True), McpGraph("ide_exercise", follow_only=True)),
    play_actions=(
        McpAction(
            "POST /ide/sessions/{session_id}/teach", 2, "ide_teach_session", launches="ide_teacher"
        ),
        McpAction(
            "POST /ide/exercises/generate", 2, "ide_generate_exercise", launches="ide_exercise"
        ),
    ),
    excluded={
        "PUT /ide/preferences": McpExclusion.IDE_RIGHTS,
    },
)
