from app.mcp.base import FeatureMcp, McpAction, McpExclusion

MCP = FeatureMcp(
    feature="mentor_reviews",
    actions=(
        McpAction(
            "GET /mentor-reviews/shares",
            1,
            "mentor_reviews_list",
            "Lists the shares started by the account.",
            untrusted=("[].title",),
        ),
        McpAction(
            "GET /mentor-reviews/shares/{share_id}",
            1,
            "mentor_reviews_read",
            "Reads the status and comments of one of the account's shares.",
            untrusted=("title", "comments[].text"),
        ),
        McpAction(
            "PATCH /mentor-reviews/shares/{share_id}/comments/{comment_id}",
            2,
            "mentor_reviews_mark_comment",
            "Marks one of the account's comments as handled or to review.",
            untrusted=("text",),
        ),
        McpAction(
            "DELETE /mentor-reviews/shares/{share_id}",
            3,
            "mentor_reviews_revoke_mentor_share",
            "Revokes the mentor's access to the shared file. Requires confirmation.",
        ),
    ),
    excluded={
        "POST /mentor-reviews/shares": McpExclusion.SHARING_TOKEN,
        "GET /mentor-reviews/shared": McpExclusion.SHARING_TOKEN,
        "POST /mentor-reviews/shared/comments": McpExclusion.SHARING_TOKEN,
    },
)
