from pydantic import BaseModel, Field

DELETE_CONFIRMATION = "SUPPRIMER"


class DeleteAccountIn(BaseModel):
    """La confirmation de « Tout supprimer » : `confirm` doit être exactement `SUPPRIMER`."""

    # Contrôlé dans le code de la route (422 `confirmation_required`, sans écho), pas par le
    # schéma : une longueur maximale rendrait une autre 422, qui ne dit pas quoi faire.
    confirm: str
    expected_user_id: str | None = Field(
        default=None,
        description=(
            "Identifiant du compte affiché, obligatoire en mode Google pour un appel direct. "
            "Dans une demande MCP confirmée, l'identité vient du jeton."
        ),
    )
