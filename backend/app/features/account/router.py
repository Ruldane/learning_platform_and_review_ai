"""Mes données (SPEC 17.1, phase 9) : l'export de toutes les données de l'utilisatrice et « Tout
supprimer ». Au nom de l'utilisatrice courante, jamais d'un autre compte ; une 422 nomme les
champs, sans jamais recopier la confirmation reçue."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from starlette.requests import HTTPConnection

from app.agents.runtime.handle import AgentRuntime
from app.core.deps import CurrentUserDep, Db
from app.core.errors import AppError
from app.core.field_paths import FieldPathsRoute
from app.core.providers import MemoryProviders
from app.features.account.schemas import DELETE_CONFIRMATION, DeleteAccountIn
from app.features.account.service import (
    AccountRuntime,
    archive_size,
    build_export,
    export_filename,
    export_lock,
    stream_export,
    user_export_zone,
)
from app.features.account.service import (
    delete_account as erase_account,
)
from app.features.auth.service.cookies import clear_session_cookie
from app.features.postings.service.runtime import KeyLocks

router = APIRouter(prefix="/account", tags=["account"], route_class=FieldPathsRoute)

_ZIP: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {"application/zip": {}},
        "description": "L'archive de toutes les données",
        "headers": {
            "Content-Disposition": {
                "description": (
                    '`attachment; filename="tremplin-export-AAAAMMJJ.zip"` : le nom proposé au'
                    " téléchargement, le jour étant celui de l'utilisatrice."
                ),
                "schema": {"type": "string"},
            }
        },
    }
}


def get_account_runtime(conn: HTTPConnection) -> AccountRuntime:
    """Stockage, index vectoriel et moteur d'agents du démarrage (`app.state`), plus les verrous
    par compte, créés à la première demande et gardés pour la vie de l'application."""
    state = conn.app.state
    locks: KeyLocks | None = getattr(state, "account_locks", None)
    if locks is None:
        locks = state.account_locks = KeyLocks()
    memory: MemoryProviders = state.memory_providers
    runtime: AgentRuntime = state.runtime
    return AccountRuntime(
        session_factory=state.session_factory,
        storage=memory.storage,
        index=memory.index,
        runtime=runtime,
        locks=locks,
    )


AccountDep = Annotated[AccountRuntime, Depends(get_account_runtime)]


@router.get("/export", response_class=Response, responses=_ZIP)
async def export_account(current: CurrentUserDep, db: Db, rt: AccountDep) -> Response:
    """Toutes les données de l'utilisatrice dans une archive zip `tremplin-export-AAAAMMJJ.zip`
    (téléchargement) : `manifest.json`, une table par fichier JSON (`tables/<table>.json`) et les
    fichiers déposés (`files/…`). Les clés d'API n'y sont jamais (seulement leurs quatre derniers
    caractères) ; ni vecteurs ni points de reprise des agents (recalculables)."""
    now = datetime.now(UTC)
    filename = export_filename(now, await user_export_zone(db, current.id))
    async with export_lock(rt.locks, current.id):
        archive = await build_export(db, rt.storage, current.id, now)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(archive_size(archive)),
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    return StreamingResponse(stream_export(archive), media_type="application/zip", headers=headers)


@router.post(
    "/delete",
    status_code=204,
    response_class=Response,
    responses={
        422: {"description": "`confirmation_required` : `details.fields` : `confirm`"},
        503: {
            "description": (
                "`vector_store_unavailable` : Qdrant ne répond pas ; rien n'est supprimé en base,"
                " un nouvel appel reprend."
            )
        },
    },
)
async def delete_account(
    request: Request, body: DeleteAccountIn, current: CurrentUserDep, rt: AccountDep
) -> Response:
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
    auth_mode = request.app.state.settings.auth_mode
    await erase_account(rt, current.id, auth_mode=auth_mode)
    response = Response(status_code=204)
    if auth_mode == "google":
        clear_session_cookie(response)  # la session a disparu avec le compte
    return response
