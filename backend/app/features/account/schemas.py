from pydantic import BaseModel

DELETE_CONFIRMATION = "SUPPRIMER"


class DeleteAccountIn(BaseModel):
    """La confirmation de « Tout supprimer » : `confirm` doit être exactement `SUPPRIMER`."""

    # Contrôlé dans le code de la route (422 `confirmation_required`, sans écho), pas par le
    # schéma : une longueur maximale rendrait une autre 422, qui ne dit pas quoi faire.
    confirm: str
