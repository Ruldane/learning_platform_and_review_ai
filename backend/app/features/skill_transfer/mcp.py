"""An authorized MCP client can re-read and schedule a check."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_VIEW = frozenset({"id", "proof", "due_on", "available", "stage", "exercise", "assessment"})
_CONTENT = (
    "proof.label",
    "proof.skill_name",
    "exercise.title",
    "exercise.prompt",
    "assessment.feedback",
    "assessment.criteria[]",
)

MCP = FeatureMcp(
    feature="skill_transfer",
    actions=(
        McpAction(
            "GET /skill-transfers/proofs",
            1,
            "skill_transfer_list_proofs",
            "Lists the account's skill proofs.",
            untrusted=("[].label", "[].skill_name"),
        ),
        McpAction(
            "GET /skill-transfers",
            1,
            "skill_transfer_list",
            "Reads the log of transfer checks.",
            response_fields=_VIEW,
            untrusted=tuple(f"[].{path}" for path in _CONTENT),
        ),
        McpAction(
            "GET /skill-transfers/{transfer_id}",
            1,
            "skill_transfer_read",
            "Reads the exercise and, once answered, the assessment.",
            response_fields=_VIEW,
            untrusted=_CONTENT,
        ),
        McpAction(
            "POST /skill-transfers",
            2,
            "skill_transfer_schedule",
            "Schedules a transfer check from a proof the user holds.",
            response_fields=_VIEW,
            untrusted=_CONTENT,
        ),
        McpAction(
            "POST /skill-transfers/{transfer_id}/prepare",
            3,
            "skill_transfer_prepare_transfer",
            "Prepares the transfer check. Asks for confirmation.",
            launches="skill_transfer",
        ),
        McpAction(
            "POST /skill-transfers/{transfer_id}/answer",
            3,
            "skill_transfer_submit_transfer_answer",
            "Submits the answer to the transfer check. Asks for confirmation.",
            launches="skill_transfer",
        ),
    ),
    graphs=(McpGraph("skill_transfer", follow_only=True),),
)
