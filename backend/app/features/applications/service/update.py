"""Retouche d'une fiche (SPEC 6.1, D139) : les champs envoyés changent (`null` efface un champ
facultatif), les contacts sont remplacés s'ils sont fournis. Le statut n'est pas un champ de la
retouche (voir `events`). `update_locked` : sous le verrou des candidatures, dans sa propre
transaction (la synchronisation des relances qui suit l'exige)."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models.applications import Application
from app.features.applications.repository import ContactRepository
from app.features.applications.schemas import ApplicationDetail, ApplicationPatch
from app.features.applications.service.create import link_key
from app.features.applications.service.queries import today_of
from app.features.applications.service.reminder_sync import sync_user
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import detail_out, get_application, invalid
from app.features.postings.service.rules import company_key

_PLAIN = ("channel", "applied_on", "interview_on", "next_action_on")
_TEXTS = ("letter", "notes", "next_action")  # un texte vide efface le champ


def _required(body: ApplicationPatch, row: Application) -> None:
    """Entreprise et intitulé : jamais vides ; l'entreprise refait sa clé de comparaison."""
    for name in ("company", "title"):
        if name not in body.model_fields_set:
            continue
        value = getattr(body, name)
        if not value:
            raise invalid(name)
        setattr(row, name, value)
        if name == "company":
            row.company_norm = company_key(value)


def _apply(body: ApplicationPatch, row: Application) -> None:
    _required(body, row)
    sent = body.model_fields_set
    if "url" in sent:
        row.url = body.url or None
        row.url_norm = link_key(row.url)
    for name in _PLAIN:
        if name in sent:
            setattr(row, name, getattr(body, name))
    for name in _TEXTS:
        if name in sent:
            setattr(row, name, getattr(body, name) or None)


async def update_application(
    db: AsyncSession, user_id: str, application_id: str, body: ApplicationPatch, today: date
) -> ApplicationDetail:
    """Applique la retouche. 404 `application_not_found` ; 422 `company`, `title`, `url` ou
    `contacts` (vide ou refusé), sans écho."""
    row = await get_application(db, user_id, application_id)
    sent = body.model_fields_set
    if "contacts" in sent and body.contacts is None:
        raise invalid("contacts")
    _apply(body, row)
    if body.contacts is not None:
        contacts = ContactRepository(db, user_id)
        await contacts.clear(row.id)
        for contact in body.contacts:
            await contacts.add(
                application_id=row.id, name=contact.name, role=contact.role, url=contact.url
            )
    row.updated_at = utcnow()
    await db.flush()
    await sync_user(db, user_id, today, application_id=row.id)
    return await detail_out(db, user_id, row, today)


async def update_locked(
    rt: ApplicationsRuntime, user_id: str, application_id: str, body: ApplicationPatch
) -> ApplicationDetail:
    """`update_application` sous le verrou des candidatures, validé avant de le rendre."""
    async with rt.lock(user_id), rt.session_factory() as db:
        today = await today_of(db, user_id, rt.now())
        detail = await update_application(db, user_id, application_id, body, today)
        await db.commit()
        return detail
