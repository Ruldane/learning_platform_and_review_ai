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
            "Les leçons d'un programme.",
        ),
        McpAction(
            "GET /lessons/{lesson_id}",
            1,
            "lessons_get_lesson",
            "Le contenu d'une leçon.",
            untrusted=_LESSON_RESOURCE_TEXT,
        ),
        McpAction(
            "GET /resources",
            1,
            "lessons_list_resources",
            "La Bibliothèque : ressources filtrables par programme, type, langue et statut.",
            untrusted=tuple(f"[].{name}" for name in _RESOURCE_TEXT),
        ),
        McpAction(
            "PATCH /resources/{resource_id}",
            2,
            "lessons_update_resource",
            "Change le statut de lecture d'une ressource.",
            untrusted=_RESOURCE_TEXT,
        ),
        McpAction(
            "POST /modules/{module_id}/lesson",
            2,
            "lessons_write_lesson",
            "Soumet le Markdown d'un module à la Fabrique (`title` et `resources` facultatifs). "
            "Suis `verification_session_id` : après contrôle, la Fabrique publie la leçon.",
            launches="lesson_factory",
            untrusted=_LESSON_RESOURCE_TEXT,
        ),
        McpAction(
            "PATCH /lessons/{lesson_id}",
            2,
            "lessons_update_lesson",
            "Soumet le titre ou le Markdown d'une leçon prête à la Fabrique. L'ajout seul de "
            "`resources` est immédiat. La version publiée reste lisible pendant le contrôle.",
            launches="lesson_factory",
            untrusted=_LESSON_RESOURCE_TEXT,
        ),
        McpAction(
            "GET /lessons/{lesson_id}/pdf",
            1,
            "lessons_get_lesson_pdf",
            "Lit les métadonnées du PDF. Le texte se lit avec lessons_get_lesson.",
            artifact=True,
        ),
        McpAction(
            "GET /resources/{resource_id}/file",
            1,
            "lessons_get_resource_file",
            "Lit les métadonnées du fichier tiers téléchargé et donne le lien local.",
            artifact=True,
        ),
    ),
    graphs=(
        McpGraph(
            "lesson_factory",
            summary="Écrit la leçon d'un module (`program_id`, `module_id`) : recherche, "
            "lecture, ressources et rédaction.",
            untrusted=("result",),
        ),
    ),
)
