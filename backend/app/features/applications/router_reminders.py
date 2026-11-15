"""API des relances (SPEC 6.2, D140) : la liste (synchronisée d'abord, brouillons prêts à copier) et
les actions Fait, Reporter de 3 jours, Ignorer. Rien n'est envoyé par l'application. Une 422 nomme
les champs, sans valeur."""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query

from app.core.deps import CurrentUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.applications.router import ApplicationsDep
from app.features.applications.schemas import ReminderOut, ReminderPatch
from app.features.applications.service.reminders import act_on_reminder, list_reminders

router = APIRouter(prefix="/reminders", tags=["applications"], route_class=FieldPathsRoute)

_PATCH_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`reminder_not_found`"},
    409: {"description": "`reminder_closed` : la relance est déjà faite ou ignorée"},
}


@router.get("", response_model=list[ReminderOut])
async def get_reminders(
    current: CurrentUserDep,
    rt: ApplicationsDep,
    due: Annotated[bool, Query()] = True,
) -> list[ReminderOut]:
    """Les relances, échéance croissante, après synchronisation avec les fiches : `due=true`
    (défaut) : en attente et dues aujourd'hui ; `due=false` : toutes (à venir, faites, ignorées)."""
    return await list_reminders(rt, current.id, due=due)


@router.patch("/{reminder_id}", response_model=ReminderOut, responses=_PATCH_ERRORS)
async def patch_reminder(
    reminder_id: Annotated[str, Path(min_length=1, max_length=36)],
    body: ReminderPatch,
    current: CurrentUserDep,
    rt: ApplicationsDep,
) -> ReminderOut:
    """`done` (la relance faite ; « Relancée » ou « Sans réponse » selon le type), `postpone`
    (+3 jours, reste en attente), `ignore`."""
    return await act_on_reminder(rt, current.id, reminder_id, body.action)
