from app.mcp.base import FeatureMcp, McpAction, McpExclusion

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
        McpAction(
            "DELETE /mentor-reviews/shares/{share_id}",
            3,
            "mentor_reviews_revoke_mentor_share",
            "Retire l’accès du mentor au dossier partagé. Demande à confirmer.",
        ),
    ),
    excluded={
        "POST /mentor-reviews/shares": McpExclusion.SHARING_TOKEN,
        "GET /mentor-reviews/shared": McpExclusion.SHARING_TOKEN,
        "POST /mentor-reviews/shared/comments": McpExclusion.SHARING_TOKEN,
    },
)
