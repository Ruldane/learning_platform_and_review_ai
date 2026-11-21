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
            "Écriture directe, aucun agent : écrit la leçon d'un module (`title` facultatif, "
            "`markdown`, `resources` facultatives avec suivi de lecture). La leçon est prête "
            "aussitôt, sans PDF.",
            untrusted=_LESSON_RESOURCE_TEXT,
        ),
        McpAction(
            "PATCH /lessons/{lesson_id}",
            2,
            "lessons_update_lesson",
            "Écriture directe, aucun agent : retouche une leçon prête (titre, Markdown, "
            "ou ajout de `resources` suivies dans la Bibliothèque).",
            untrusted=_LESSON_RESOURCE_TEXT,
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
    excluded={
        "GET /lessons/{lesson_id}/pdf": (
            "Réponse en PDF, pas du JSON : le MCP lit la leçon par `lessons_get_lesson`."
        ),
        "GET /resources/{resource_id}/file": (
            "Copie locale d'un PDF tiers en fichier binaire, pas du JSON ; la fiche de la "
            "ressource se lit par `lessons_list_resources`."
        ),
    },
)
