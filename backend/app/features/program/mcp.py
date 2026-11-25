"""MCP declaration for `program`: read and edit the program, validate it."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_FILE = (
    "File response (calendar or PDF), not JSON: the MCP reads the program through "
    "`program_get_program`."
)

MCP = FeatureMcp(
    feature="program",
    actions=(
        McpAction("GET /programs", 1, "program_list_programs", "The learning programs."),
        McpAction(
            "GET /programs/{program_id}",
            1,
            "program_get_program",
            "A full program: modules, weeks, tasks.",
        ),
        McpAction(
            "POST /programs/direct",
            2,
            "program_write_program",
            "Direct write, no agent: writes a full program for a goal (`goal_id`, title, start "
            "date, then weeks, modules, tasks) as a draft to validate; same limits and rules as "
            "the Strategist (4 modules per week, 12 tasks per module, 85% of the budget, "
            "practice and a quiz every week: the app schedules the days). Lessons and quizzes "
            "are then written per module.",
        ),
        McpAction(
            "PATCH /programs/{program_id}",
            2,
            "program_update_program",
            "Adds or removes tasks, changes the start date of a program.",
        ),
        McpAction(
            "POST /programs/{program_id}/validate",
            3,
            "program_validate_program",
            "Validates the program: skills in progress, acquired skills in memory, lessons "
            "launched. January's decision, with effects outside the database: needs "
            "confirmation.",
            side_effects="external",
        ),
        McpAction(
            "PATCH /tasks/{task_id}",
            2,
            "program_update_task",
            "Moves or edits a program task.",
        ),
        McpAction(
            "POST /programs/{program_id}/weeks",
            2,
            "program_add_week",
            "Direct write, no agent: adds a week (theme, objective, deliverable) at the end of "
            "the program; its modules and tasks come next.",
        ),
        McpAction(
            "PATCH /weeks/{week_id}",
            2,
            "program_update_week",
            "Direct write, no agent: edits the theme, objective or deliverable of a week.",
        ),
        McpAction(
            "POST /programs/{program_id}/modules",
            2,
            "program_add_module",
            "Direct write, no agent: adds a module (title, skills, prerequisites) to a week of "
            "the program; its tasks are set through `program_update_program`.",
        ),
        McpAction(
            "PATCH /modules/{module_id}",
            2,
            "program_update_module",
            "Direct write, no agent: edits the title, skills or prerequisites of a module.",
        ),
        McpAction(
            "GET /programs/{program_id}/export.ics",
            1,
            "program_get_calendar_file",
            "Reads the program calendar and gives the local link to the file.",
            artifact=True,
            untrusted=("text",),
        ),
        McpAction(
            "GET /programs/{program_id}/export.pdf",
            1,
            "program_get_program_pdf",
            "Reads the metadata of the program PDF and gives its local link.",
            artifact=True,
        ),
    ),
    graphs=(
        McpGraph(
            "program_builder",
            summary="Builds a program from a goal (`goal_id`) and its chosen paths "
            "(`proposal_ids`).",
        ),
    ),
)
