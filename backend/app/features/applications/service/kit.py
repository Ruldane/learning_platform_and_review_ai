"""Le kit de candidature d'une fiche (SPEC 6.4, F16, D143) : lancement du parcours
`application_kit`, lecture des sept pièces et modification d'une pièce par January.

- `start_kit` : sous le verrou de la fiche, une seule session ouverte à la fois (409
  `kit_in_progress`, `details.session_id`), après les contrôles d'entrée (409 `posting_required`,
  409 `profile_required`) ; l'événement `kit` « lancé » entre au fil. Relancer refait les pièces
  que January n'a pas modifiées (`KitContext.keep`).
- `patch_piece` : le texte de January remplace la pièce (`edited`, gardée aux relances) ; une pièce
  « à vérifier » est relue par le code (`kit_items.recheck`).

Journaux : identifiants et statuts seulement, jamais une pièce ni l'entreprise (17.2)."""

import logging

from app.agents.tools.kit_schema import KitContext
from app.core.errors import AppError
from app.features.applications.repository import EventRepository, KitRepository
from app.features.applications.schemas_kit import KIT_ORDER, KitItemOut, KitKind, KitOut
from app.features.applications.service.kit_items import (
    item_out,
    needs_context,
    pending_item,
    recheck,
)
from app.features.applications.service.kit_store import (
    GRAPH,
    SUBJECT,
    AgentKitStore,
    kit_lock,
    posting_inputs,
    profile_required,
)
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import get_application
from app.features.cv.service.versions import validated_profile
from app.features.sessions.service import find_active_session, find_latest_session

logger = logging.getLogger(__name__)


def kit_in_progress(session_id: str) -> AppError:
    return AppError(
        "kit_in_progress",
        "Le kit de cette candidature est déjà en préparation : attends la fin de la session.",
        409,
        {"session_id": session_id},
    )


def piece_not_found() -> AppError:
    return AppError(
        "kit_item_not_found", "Cette pièce n'existe pas encore : lance d'abord le kit.", 404
    )


_EDIT_BLOCKED = {
    "profile_required": "Valide ton profil maître : sans lui, ta modification n'est pas relue.",
    "posting_required": "Cette fiche n'a plus d'offre ni de texte d'offre : ta modification "
    "ne peut pas être relue.",
}


async def _context_for_edit(
    rt: ApplicationsRuntime, user_id: str, application_id: str
) -> KitContext:
    """Le contexte pour relire la modification ; un refus (409) parle de la modification, pas du
    lancement du kit."""
    try:
        return await AgentKitStore(rt).context(user_id, application_id)
    except AppError as exc:
        if exc.code in _EDIT_BLOCKED:
            raise AppError(exc.code, _EDIT_BLOCKED[exc.code], 409) from None
        raise


async def start_kit(rt: ApplicationsRuntime, user_id: str, application_id: str) -> str:
    """Lance le kit de la fiche et rend l'identifiant de la session."""
    async with kit_lock(rt, user_id, application_id), rt.session_factory() as db:
        row = await get_application(db, user_id, application_id)
        await posting_inputs(db, user_id, row)
        if await validated_profile(db, user_id) is None:
            raise profile_required()
        open_id = await find_active_session(
            db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=row.id
        )
        if open_id is not None:
            raise kit_in_progress(open_id)
        session_id = await rt.launcher.start(
            user_id, GRAPH, {"application_id": row.id}, subject_type=SUBJECT, subject_id=row.id
        )
        await EventRepository(db, user_id).add(
            application_id=row.id,
            kind="kit",
            at=rt.now(),
            text="Application kit started.",
            ref_id=session_id,
        )
        await db.commit()
    logger.info(
        "Kit lancé : utilisateur %s, fiche %s, session %s", user_id, application_id, session_id
    )
    return session_id


async def read_kit(rt: ApplicationsRuntime, user_id: str, application_id: str) -> KitOut:
    """Les sept pièces dans l'ordre fixe, `pending` pour celles pas encore rangées."""
    async with rt.session_factory() as db:
        row = await get_application(db, user_id, application_id)
        pieces = {
            piece.kind: piece for piece in await KitRepository(db, user_id).of_application(row.id)
        }
        active = await find_active_session(
            db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=row.id
        )
        session_id = active or await find_latest_session(
            db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=row.id
        )
    items = [item_out(pieces[kind]) if kind in pieces else pending_item(kind) for kind in KIT_ORDER]
    return KitOut(session_id=session_id, running=active is not None, items=items)


async def patch_piece(
    rt: ApplicationsRuntime, user_id: str, application_id: str, kind: KitKind, content: str
) -> KitItemOut:
    """Le texte de January remplace la pièce, marquée `edited`. 404 `application_not_found`, 404
    `kit_item_not_found` (pièce pas encore rangée)."""
    async with kit_lock(rt, user_id, application_id), rt.session_factory() as db:
        await get_application(db, user_id, application_id)
        row = await KitRepository(db, user_id).of_kind(application_id, kind)
        if row is None:
            raise piece_not_found()
        # Une pièce prête n'est pas relue : seul le contexte d'une pièce à relire est lu.
        ctx = None
        if needs_context(row.status, content):
            ctx = await _context_for_edit(rt, user_id, application_id)
        checked = recheck(row, content, ctx)
        row.content, row.status, row.meta = content, checked.status, checked.meta
        row.edited = True
        row.updated_at = rt.now()
        await db.commit()
        out = item_out(row)
    logger.info(
        "Pièce du kit modifiée : utilisateur %s, fiche %s, pièce %s, statut %s",
        user_id,
        application_id,
        kind,
        out.status,
    )
    return out
