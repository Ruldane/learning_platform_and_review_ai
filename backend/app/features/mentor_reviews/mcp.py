from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="mentor_reviews",
    actions=(
        McpAction(
            "GET /mentor-reviews/shares",
            1,
            "mentor_reviews_list",
            "Liste les partages lancés par le compte.",
            untrusted=("[].title",),
        ),
        McpAction(
            "GET /mentor-reviews/shares/{share_id}",
            1,
            "mentor_reviews_read",
            "Relit le statut et les commentaires d’un partage du compte.",
            untrusted=("title", "comments[].text"),
        ),
        McpAction(
            "PATCH /mentor-reviews/shares/{share_id}/comments/{comment_id}",
            2,
            "mentor_reviews_mark_comment",
            "Marque un commentaire du compte comme traité ou à relire.",
            untrusted=("text",),
        ),
    ),
    excluded={
        "POST /mentor-reviews/shares": "Consentement et lien réservés à l’interface.",
        "DELETE /mentor-reviews/shares/{share_id}": "Retrait depuis l’interface du propriétaire.",
        "GET /mentor-reviews/shared": "Canal invité protégé par un jeton de partage dédié.",
        "POST /mentor-reviews/shared/comments": "Canal invité à jeton de partage dédié.",
    },
)
