from pydantic import BaseModel, Field

DELETE_CONFIRMATION = "SUPPRIMER"


class DeleteAccountIn(BaseModel):
    """The "Delete everything" confirmation: `confirm` must be exactly `SUPPRIMER`."""

    # Checked in the route code (422 `confirmation_required`, without echo), not by the schema:
    # a maximum length would return another 422 that does not say what to do.
    confirm: str
    expected_user_id: str | None = Field(
        default=None,
        description=(
            "Id of the displayed account, required in Google mode for a direct call. "
            "In a confirmed MCP request, the identity comes from the token."
        ),
    )
