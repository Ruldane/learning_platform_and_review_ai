from app.mcp.base import FeatureMcp, McpAction

_NAMES = tuple(
    f"{position}.{field}" for position in ("first", "second") for field in ("title", "company")
)
_FACTS = (
    _NAMES
    + tuple(
        f"{position}.{field}"
        for position in ("first", "second")
        for field in ("location", "remote")
    )
    + ("preferences.preferred_location",)
)
_SAVED = tuple(f"result.{path}" for path in _FACTS)

MCP = FeatureMcp(
    feature="offer_comparison",
    actions=(
        McpAction(
            "GET /offer-comparisons/postings",
            1,
            "offer_comparison_postings",
            "Lists the private postings ready to be compared.",
            untrusted=("[].title", "[].company"),
        ),
        McpAction(
            "GET /offer-comparisons/preferences",
            1,
            "offer_comparison_preferences",
            "Reads the account's comparison weights and criteria.",
            untrusted=("preferred_location",),
        ),
        McpAction(
            "POST /offer-comparisons/preview",
            2,
            "offer_comparison_preview",
            "Computes scores, missing claims and sensitivity without saving.",
            untrusted=_FACTS,
        ),
        McpAction(
            "POST /offer-comparisons",
            2,
            "offer_comparison_save",
            "Saves a scenario with frozen values and weights.",
            untrusted=_SAVED,
        ),
        McpAction(
            "GET /offer-comparisons",
            1,
            "offer_comparison_list",
            "Lists the saved private comparisons.",
            untrusted=tuple(f"[].{path}" for path in _NAMES),
        ),
        McpAction(
            "GET /offer-comparisons/{scenario_id}",
            1,
            "offer_comparison_read",
            "Reads the frozen result of a posting comparison.",
            untrusted=_SAVED,
        ),
        McpAction(
            "PUT /offer-comparisons/preferences",
            3,
            "offer_comparison_set_comparison_preferences",
            "Changes the personal comparison criteria. Asks for confirmation.",
        ),
    ),
)
