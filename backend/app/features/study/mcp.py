"""MCP declaration for `study`: the guided session with the Tutor."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_TRAINING = "/study-sessions/training"
_TRAINING_SESSION = f"{_TRAINING}/{{study_session_id}}"
_TURN_CONTENT = (
    "conversation.turns[].question",
    "conversation.turns[].answer",
    "conversation.turns[].sources[].title",
    "conversation.turns[].sources[].excerpt",
)

MCP = FeatureMcp(
    feature="study",
    actions=(
        McpAction(
            "POST /study-sessions",
            2,
            "study_start_session",
            "Opens a guided session on a lesson (or the day's block) and starts the Tutor.",
            launches="study_session",
        ),
        McpAction(
            "GET /study-sessions/summary",
            1,
            "study_get_summary",
            "Streak, minutes this week, timer, open session and the day's block.",
        ),
        McpAction(
            "GET /study-sessions/{study_session_id}",
            1,
            "study_get_session",
            "A guided session, with its end screen.",
        ),
        McpAction(
            "PATCH /study-sessions/{study_session_id}",
            3,
            "study_update_session",
            "Finishes (`finish`) or abandons (`cancel`) a guided session. To confirm in Tremplin.",
        ),
        McpAction(
            f"POST {_TRAINING}",
            2,
            "study_start_training",
            "Opens or resumes a training. new_conversation creates a separate thread.",
            untrusted=_TURN_CONTENT,
        ),
        McpAction(
            f"GET {_TRAINING}/open",
            1,
            "study_open_training",
            "Reads the open training session, if any.",
            untrusted=_TURN_CONTENT,
        ),
        McpAction(
            f"GET {_TRAINING_SESSION}",
            1,
            "study_read_training",
            "Reads the training, its exchanges and its sources.",
            untrusted=_TURN_CONTENT,
        ),
        McpAction(
            f"PATCH {_TRAINING_SESSION}/context",
            2,
            "study_update_training_context",
            "Changes the mode or the selected lessons of a training.",
            untrusted=_TURN_CONTENT,
        ),
        McpAction(
            f"PATCH {_TRAINING_SESSION}",
            3,
            "study_update_training",
            "Finishes or abandons a training session. To confirm in Tremplin.",
            untrusted=_TURN_CONTENT,
        ),
        McpAction(
            f"POST {_TRAINING_SESSION}/messages",
            2,
            "study_talk_training",
            "Talks to the Tutor in the thread, even after the review. "
            "Reuse the same request id to replay a message.",
            launches="conversation",
        ),
    ),
    graphs=(
        McpGraph(
            "study_session",
            follow_only=True,
            summary="The Tutor leads a guided session (`study_session_id`).",
        ),
    ),
)
