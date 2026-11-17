from pydantic import BaseModel, Field

DELETE_CONFIRMATION = "SUPPRIMER"


class DeleteAccountIn(BaseModel):
    """La confirmation de « Tout supprimer » : `confirm` doit être exactement `SUPPRIMER`."""

    confirm: str = Field(max_length=32)
