from app.agents.tools.conversation_port import CONVERSATION_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

_CHAT = "/conversations/{scope}"
_THREAD = _CHAT + "/{conversation_id}"
_FEYNMAN_CONTENT = (
    "source.title",
    "source.path",
    "report.explanation",
    "report.follow_up",
    "report.clarification",
    "report.summary",
    "report.cards[].front",
    "report.cards[].back",
)

MCP = FeatureMcp(
    feature="conversations",
    actions=(
        McpAction(
            f"GET {_CHAT}",
            1,
            "conversations_list",
            "Lists Brain, training, or Offers conversations, with search by title.",
            untrusted=("[].title",),
        ),
        McpAction(
            f"PATCH {_THREAD}",
            2,
            "conversations_rename",
            "Renames a Brain, training, or Offers conversation.",
            untrusted=("title",),
        ),
        McpAction(
            f"DELETE {_THREAD}/messages",
            3,
            "conversations_clear",
            "Clears a conversation's exchanges. To confirm in Tremplin.",
            side_effects="external",
        ),
        McpAction(
            f"DELETE {_THREAD}",
            3,
            "conversations_delete",
            "Permanently deletes a conversation and its exchanges. To confirm in Tremplin.",
            side_effects="external",
        ),
        McpAction(
            f"DELETE {_CHAT}",
            3,
            "conversations_wipe",
            "Deletes all threads in one Brain, training, or Offers scope. To confirm in Tremplin.",
            side_effects="external",
        ),
        McpAction(
            "POST /conversations/offers",
            2,
            "conversations_create_offers",
            "Creates an empty conversation about saved offers.",
        ),
        McpAction(
            "GET /conversations/offers/{conversation_id}",
            1,
            "conversations_read_offers",
            "Reads an Offers conversation and the citations in its replies.",
            untrusted=("turns[].question", "turns[].answer", "turns[].sources[].title"),
        ),
        McpAction(
            "POST /conversations/offers/{conversation_id}/messages",
            2,
            "conversations_ask_offers",
            "Asks about saved offers and returns the reply session id. "
            "Reuse the same request_id (UUID) to retry the submission.",
            launches=CONVERSATION_GRAPH,
        ),
        McpAction(
            "GET /lessons/{lesson_id}/conversation",
            1,
            "conversations_read_professor",
            "Reads the Professor thread of a published lesson, if any.",
            untrusted=(
                "turns[].question",
                "turns[].passage",
                "turns[].answer",
                "turns[].sources[].title",
                "turns[].sources[].excerpt",
            ),
        ),
        McpAction(
            "POST /lessons/{lesson_id}/conversation/messages",
            2,
            "conversations_ask_professor",
            "Asks the Professor of a published lesson a question and returns the session id. "
            "Reuse the same request_id (UUID) to replay sending the same message.",
            launches=CONVERSATION_GRAPH,
        ),
        McpAction(
            "GET /lessons/{lesson_id}/classroom",
            1,
            "conversations_read_classroom",
            "Reads a published lesson's virtual classroom with the three classmates' answers.",
            untrusted=(
                "turns[].question",
                "turns[].passage",
                "turns[].answer",
                "turns[].classmates[].answer",
                "turns[].sources[].title",
                "turns[].sources[].excerpt",
            ),
        ),
        McpAction(
            "POST /lessons/{lesson_id}/classroom/messages",
            2,
            "conversations_ask_classroom",
            "Shares an explanation with the three classmates of a published lesson. "
            "Reuse the same request_id (UUID) to replay sending the same message.",
            launches=CONVERSATION_GRAPH,
        ),
        McpAction(
            "GET /lessons/{lesson_id}/explain",
            1,
            "conversations_latest_lesson_explanation",
            "Reads the latest Feynman explanation on a lesson.",
            untrusted=_FEYNMAN_CONTENT,
        ),
        McpAction(
            "POST /lessons/{lesson_id}/explain",
            2,
            "conversations_explain_lesson",
            "Opens a Feynman explanation on a lesson.",
            launches=CONVERSATION_GRAPH,
        ),
        McpAction(
            "GET /ide/sessions/{session_id}/explain",
            1,
            "conversations_latest_file_explanation",
            "Reads the latest Feynman explanation on a workshop file.",
            untrusted=_FEYNMAN_CONTENT,
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/explain",
            2,
            "conversations_explain_file",
            "Opens a Feynman explanation on a workshop file.",
            launches=CONVERSATION_GRAPH,
        ),
        McpAction(
            "GET /conversations/explain/{turn_id}",
            1,
            "conversations_read_explanation",
            "Reads the report of a Feynman explanation.",
            untrusted=_FEYNMAN_CONTENT,
        ),
        McpAction(
            "POST /conversations/explain/{turn_id}/accept",
            3,
            "conversations_accept_explanation",
            "Saves what was learned from a Feynman explanation. To confirm in Tremplin.",
        ),
    ),
    graphs=(McpGraph(CONVERSATION_GRAPH, follow_only=True),),
)
