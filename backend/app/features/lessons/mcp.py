"""Déclaration MCP de `lessons` : leçons et Bibliothèque de ressources."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_RESOURCE_TEXT = ("title", "author", "reason", "note")
_LESSON_RESOURCE_TEXT = tuple(f"resources[].{name}" for name in _RESOURCE_TEXT)

MCP = FeatureMcp(
    feature="lessons",
    actions=(
        McpAction(
            "GET /programs/{program_id}/lessons",
            1,
            "lessons_list_lessons",
            "The lessons of a program.",
        ),
        McpAction(
            "GET /lessons/{lesson_id}",
            1,
            "lessons_get_lesson",
            "The content of a lesson.",
            untrusted=_LESSON_RESOURCE_TEXT,
        ),
        McpAction(
            "GET /resources",
            1,
            "lessons_list_resources",
            "The Library: resources filterable by program, type, language and status.",
            untrusted=tuple(f"[].{name}" for name in _RESOURCE_TEXT),
        ),
        McpAction(
            "PATCH /resources/{resource_id}",
            2,
            "lessons_update_resource",
            "Changes the reading status of a resource.",
            untrusted=_RESOURCE_TEXT,
        ),
        McpAction(
            "POST /modules/{module_id}/lesson",
            2,
            "lessons_write_lesson",
            "Submits the Markdown of a module to the Lesson Factory (`title` and `resources` "
            "optional). Follow `verification_session_id`: after the check, the Factory "
            "publishes the lesson.",
            launches="lesson_factory",
            untrusted=_LESSON_RESOURCE_TEXT,
        ),
        McpAction(
            "PATCH /lessons/{lesson_id}",
            2,
            "lessons_update_lesson",
            "Submits the title or Markdown of a ready lesson to the Lesson Factory. Adding only "
            "`resources` is immediate. The published version stays readable during the check.",
            launches="lesson_factory",
            untrusted=_LESSON_RESOURCE_TEXT,
        ),
        McpAction(
            "GET /lessons/{lesson_id}/pdf",
            1,
            "lessons_get_lesson_pdf",
            "Reads the PDF metadata. Read the text with lessons_get_lesson.",
            artifact=True,
        ),
        McpAction(
            "GET /resources/{resource_id}/file",
            1,
            "lessons_get_resource_file",
            "Reads the metadata of the downloaded third-party file and gives the local link.",
            artifact=True,
        ),
    ),
    graphs=(
        McpGraph(
            "lesson_factory",
            summary="Writes the lesson of a module (`program_id`, `module_id`): research, "
            "reading, resources and writing.",
            untrusted=("result",),
        ),
    ),
)
