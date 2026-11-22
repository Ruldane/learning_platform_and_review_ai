from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("lesson_title", "source_markdown", "review_markdown", "reading_steps[]")

MCP = FeatureMcp(
    feature="lesson_variants",
    actions=(
        McpAction(
            "GET /lesson-variants",
            1,
            "lesson_variants_list",
            "Liste les éditions privées du compte et leurs révisions sources.",
            untrusted=("[].lesson_title",),
        ),
        McpAction(
            "POST /lesson-variants",
            2,
            "lesson_variants_prepare",
            "Enregistre deux lectures de la version publiée d’une leçon du compte.",
            untrusted=_TEXT,
        ),
        McpAction(
            "GET /lesson-variants/{edition_id}",
            1,
            "lesson_variants_read",
            "Relit les variantes privées et la version source conservée.",
            untrusted=_TEXT,
        ),
    ),
)
