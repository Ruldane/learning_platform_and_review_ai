from app.features.message_review.preferences import FEATURE
from app.mcp.base import FeatureMcp, McpAction, McpExclusion

_ROOT = "/message-reviews"
_ANSWER = _ROOT + "/{challenge_id}/answer"

MCP = FeatureMcp(
    feature=FEATURE,
    actions=(
        McpAction(
            f"POST {_ROOT}/claim",
            2,
            "message_review_claim",
            "Reserves a due card within the consented window. Same challenge on replay. Nod only.",
            untrusted=("challenge.question",),
        ),
        McpAction(
            f"GET {_ANSWER}",
            1,
            "message_review_reveal",
            "Reads the back of the challenge when the person in the chat asks for it. Nod only.",
            untrusted=("answer",),
        ),
        McpAction(
            f"POST {_ANSWER}",
            2,
            "message_review_answer",
            "Relays only the explicit verdict of the person in the private chat on this "
            "challenge. Passed: ok. To review: fail. Never choose the verdict for them. Nod only.",
        ),
    ),
    excluded={
        f"GET {_ROOT}/settings": McpExclusion.INTEGRATION_TOKEN,
        f"PUT {_ROOT}/settings": McpExclusion.INTEGRATION_TOKEN,
    },
)
