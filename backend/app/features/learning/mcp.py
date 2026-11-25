"""MCP declaration for `learning`: goals, Council proposals and board states."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="learning",
    actions=(
        McpAction(
            "POST /goals",
            2,
            "learning_create_goal",
            "Creates a learning goal and starts the Council, which proposes learning paths.",
            launches="learning_council",
        ),
        McpAction(
            "POST /goals/direct",
            2,
            "learning_write_goal",
            "Direct write, no agent: creates a goal (title, target role, deadline, "
            "hours per week) without starting the Council, so at no API cost; the program "
            "is then written with `program_write_program`.",
        ),
        McpAction("GET /goals", 1, "learning_list_goals", "Lists January's learning goals."),
        McpAction("GET /goals/{goal_id}", 1, "learning_get_goal", "A goal and its state."),
        McpAction(
            "POST /goals/{goal_id}/council",
            2,
            "learning_retry_council",
            "Restarts the Council for a goal whose last session failed.",
            launches="learning_council",
        ),
        McpAction(
            "GET /goals/{goal_id}/proposals",
            1,
            "learning_list_proposals",
            "The learning paths proposed by the Council for a goal.",
        ),
        McpAction(
            "POST /proposals/{proposal_id}/choose",
            3,
            "learning_choose_proposal",
            "Chooses the learning path of a goal and starts building the program: "
            "this is January's decision, asks for confirmation.",
        ),
        McpAction(
            "GET /goals/{goal_id}/boards",
            1,
            "learning_list_boards",
            "The Council board states for a goal.",
        ),
        McpAction(
            "POST /boards/{board_id}/edits",
            2,
            "learning_edit_board",
            "Edits the Council board state (new version of the state).",
        ),
    ),
    graphs=(
        McpGraph(
            "learning_council",
            summary="The Learning Council on a goal (`goal_id`): debate, "
            "framing and learning path proposals.",
        ),
    ),
)
