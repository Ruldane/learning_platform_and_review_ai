"""Les relances pour l'API (SPEC 6.2, D140) : qui contacter (le recruteur d'abord si un rôle le
dit, sinon le premier contact de la fiche), le canal, le lien de recherche LinkedIn sans contact,
le brouillon (gabarit fixe ; texte du kit quand il est prêt). Lectures groupées : les contacts,
les offres et les pièces « relances » des fiches sont lus en une fois."""

import re
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.applications import Application, Contact, Reminder
from app.features.applications.repository import (
    ApplicationRepository,
    ContactRepository,
    KitRepository,
)
from app.features.applications.schemas import ContactOut, ReminderChannel, ReminderOut
from app.features.applications.service.drafts import (
    Language,
    draft_for,
    kit_followup,
    linkedin_search_url,
)
from app.features.postings.service.queries import postings_by_ids

_RECRUITER = re.compile(r"\b(recrut\w*|recruit\w*|talent|rh|hr)\b", re.IGNORECASE)


def pick_contact(contacts: Sequence[Contact]) -> Contact | None:
    """Le contact à écrire : un rôle de recrutement d'abord, sinon le premier donné."""
    for contact in contacts:
        if contact.role and _RECRUITER.search(contact.role):
            return contact
    return contacts[0] if contacts else None


def channel_of(kind: str, contact: Contact | None) -> ReminderChannel:
    """LinkedIn pour la relance de 7 jours, email pour celle de 14 jours, rien pour la
    proposition de classer ; après un entretien : LinkedIn si le contact a un lien LinkedIn,
    sinon email."""
    if kind == "linkedin_7":
        return "linkedin"
    if kind == "close_21":
        return "none"
    if kind == "email_14":
        return "email"
    linkedin = contact is not None and "linkedin." in (contact.url or "").lower()
    return "linkedin" if linkedin else "email"


def language_of(analysis: dict[str, object] | None) -> Language:
    """La langue de l'offre (`fr` ou `en`) ; défaut `fr`."""
    value = (analysis or {}).get("language")
    return "en" if value == "en" else "fr"


def reminder_out(
    row: Reminder,
    app: Application,
    contacts: Sequence[Contact],
    language: Language,
    kit_text: str | None,
) -> ReminderOut:
    contact = pick_contact(contacts)
    kind: str = row.kind
    draft = draft_for(
        row.kind,  # type: ignore[arg-type]  # la colonne est un texte, les valeurs sont ReminderKind
        language=language,
        company=app.company,
        title=app.title,
        contact_name=contact.name if contact else None,
        applied_on=app.applied_on,
        interview_on=app.interview_on,
        kit_followup=kit_followup(kit_text, row.kind) if kit_text else None,  # type: ignore[arg-type]
    )
    searching = contact is None and kind != "close_21"
    return ReminderOut.model_validate(
        {
            "id": row.id,
            "application_id": row.application_id,
            "kind": row.kind,
            "due_on": row.due_on,
            "status": row.status,
            "company": app.company,
            "title": app.title,
            "contact": (
                ContactOut(id=contact.id, name=contact.name, role=contact.role, url=contact.url)
                if contact
                else None
            ),
            "linkedin_search_url": linkedin_search_url(app.company, app.title)
            if searching
            else None,
            "channel": channel_of(kind, contact),
            "draft": draft,
        }
    )


async def reminder_outs(
    db: AsyncSession, user_id: str, rows: Sequence[Reminder]
) -> list[ReminderOut]:
    """Les relances pour l'API, dans l'ordre donné."""
    ids = list({row.application_id for row in rows})
    if not ids:
        return []
    apps = await ApplicationRepository(db, user_id).by_ids(ids)
    contacts = await ContactRepository(db, user_id).of_applications(ids)
    kits = await KitRepository(db, user_id).ready_followups(ids)
    posting_ids = {a.posting_id for a in apps.values() if a.posting_id}
    postings = await postings_by_ids(db, user_id, posting_ids)
    result = []
    for row in rows:
        app = apps[row.application_id]
        posting = postings.get(app.posting_id or "")
        result.append(
            reminder_out(
                row,
                app,
                contacts.get(app.id, []),
                language_of(posting.analysis if posting else None),
                kits.get(app.id),
            )
        )
    return result
