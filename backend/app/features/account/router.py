"""Mes données (SPEC 17.1, phase 9) : l'export de toutes les données de l'utilisatrice et « Tout
supprimer ». Au nom de l'utilisatrice courante, jamais d'un autre compte ; une 422 nomme les
champs, sans jamais recopier la confirmation reçue."""

from typing import Any

from fastapi import APIRouter, Response

from app.core.deps import CurrentUserDep, Db
from app.core.errors import AppError
from app.core.field_paths import FieldPathsRoute
from app.features.account.schemas import DELETE_CONFIRMATION, DeleteAccountIn

router = APIRouter(prefix="/account", tags=["account"], route_class=FieldPathsRoute)

_ZIP: dict[int | str, dict[str, Any]] = {
    200: {"content": {"application/zip": {}}, "description": "L'archive de toutes les données"}
}


@router.get("/export", response_class=Response, responses=_ZIP)
async def export_account(current: CurrentUserDep, db: Db) -> Response:
    """Toutes les données de l'utilisatrice dans une archive zip `tremplin-export-AAAAMMJJ.zip`
    (téléchargement) : `manifest.json`, une table par fichier JSON (`tables/<table>.json`) et les
    fichiers déposés (`files/…`). Les clés d'API n'y sont jamais (seulement leurs quatre derniers
    caractères) ; ni vecteurs ni points de reprise des agents (recalculables)."""
    raise AppError("not_implemented", "Pas encore disponible.", 501)


@router.post(
    "/delete",
    status_code=204,
    response_class=Response,
    responses={422: {"description": "`confirmation_required` : `details.fields` : `confirm`"}},
)
async def delete_account(body: DeleteAccountIn, current: CurrentUserDep, db: Db) -> Response:
    """Tout supprimer : annule les sessions en cours, puis efface les vecteurs, les fichiers, les
    points de reprise et toutes les lignes du compte. `confirm` doit être `SUPPRIMER`, sinon 422
    `confirmation_required`. Rejouable jusqu'au bout si elle est interrompue. Mode local : l'espace
    reste utilisable, vide ; mode Google : le compte et la session disparaissent."""
    if body.confirm != DELETE_CONFIRMATION:
        raise AppError(
            "confirmation_required",
            "Écris SUPPRIMER pour confirmer.",
            422,
            {"fields": ["confirm"]},
        )
    raise AppError("not_implemented", "Pas encore disponible.", 501)
