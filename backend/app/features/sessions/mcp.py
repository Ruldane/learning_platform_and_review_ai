"""Déclaration MCP de `sessions` : suivre une session d'agents et lui répondre. Lancer un parcours
se fait par l'outil de son graphe (`McpGraph`), jamais par `POST /sessions` brut."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="sessions",
    actions=(
        McpAction(
            "GET /sessions/play",
            1,
            "agents_play_list",
            "Lists the playable launches open to this token and the schema of their arguments.",
        ),
        McpAction(
            "POST /sessions/play",
            2,
            "agents_play_start",
            "Starts a workflow with the client's model, through its launch tool.",
        ),
        McpAction(
            "GET /sessions/{session_id}/play",
            1,
            "agents_play_brief",
            "Reads the messages, the role and the schema of the expected answer.",
        ),
        McpAction(
            "POST /sessions/{session_id}/play",
            2,
            "agents_play_submit",
            "Submits a model answer for the given step.",
        ),
        McpAction(
            "GET /sessions",
            1,
            "sessions_list_sessions",
            "Agent sessions, filterable by workflow and status.",
        ),
        McpAction(
            "GET /sessions/{session_id}",
            1,
            "sessions_get_session",
            "State of a session: status, pending question, error, usage.",
        ),
        McpAction(
            "POST /sessions/{session_id}/resume",
            3,
            "sessions_answer_session",
            "Answers the pending question of a session. This is January's decision "
            "(approve a program, accept a replan, confirm a card): asks for confirmation.",
        ),
        McpAction(
            "POST /sessions/{session_id}/message",
            2,
            "sessions_post_message",
            "Sends a message or a command to a running session.",
        ),
        McpAction(
            "POST /sessions/{session_id}/pause",
            2,
            "sessions_pause_session",
            "Pauses a running agent session.",
        ),
        McpAction(
            "POST /sessions/{session_id}/cancel",
            2,
            "sessions_cancel_session",
            "Cancels a running session.",
        ),
    ),
    graphs=(McpGraph("demo_debate", play_only=True),),
    alternatives={
        "POST /sessions": "agents_play_start",
        "WS /sessions/{session_id}/stream": "sessions_get_session",
    },
)
