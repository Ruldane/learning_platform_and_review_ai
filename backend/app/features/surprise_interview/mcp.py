from app.features.surprise_interview.preferences import FEATURE
from app.mcp.base import FeatureMcp, McpAction, McpExclusion

_ROOT = "/surprise-interviews"
_INVITATION = _ROOT + "/{invitation_id}"

MCP = FeatureMcp(
    feature=FEATURE,
    actions=(
        McpAction(
            f"POST {_ROOT}/invite",
            2,
            "surprise_interview_invite",
            "Reserves the weekly invitation within the consented window. Nod only.",
        ),
        McpAction(
            f"POST {_INVITATION}/accept",
            2,
            "surprise_interview_accept",
            "Starts the interview only after explicit acceptance in the private chat.",
            launches="interview",
        ),
        McpAction(
            f"GET {_INVITATION}",
            1,
            "surprise_interview_state",
            "Reads the pending question or the debrief of this interview. Nod only.",
            untrusted=(
                "question.text",
                "debrief.strengths[]",
                "debrief.fixes[]",
                "debrief.improved_answer",
            ),
        ),
        McpAction(
            f"POST {_INVITATION}/answer",
            2,
            "surprise_interview_answer",
            "Relays the original answer to the given question and its message identifier. "
            "After a failure, read the state again and resend the same message if the question "
            "is still waiting. The answer cannot be undone. Nod only.",
        ),
    ),
    excluded={
        f"GET {_ROOT}/settings": McpExclusion.INTEGRATION_TOKEN,
        f"PUT {_ROOT}/settings": McpExclusion.INTEGRATION_TOKEN,
    },
)
