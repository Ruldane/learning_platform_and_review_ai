"""Build reminders for the API (SPEC 6.2, D140) with the contact, channel and draft.
Prefer a recruiter when present. When there is no contact, include a LinkedIn search link.
Load contacts and ready kit follow-ups in batches."""

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
from app.features.applications.service.drafts import draft_for, kit_followup, linkedin_search_url

_RECRUITER = re.compile(r"\b(recrut\w*|recruit\w*|talent|rh|hr)\b", re.IGNORECASE)


def pick_contact(contacts: Sequence[Contact]) -> Contact | None:
    """The contact to write to: a recruiting role first, otherwise the first one given."""
    for contact in contacts:
        if contact.role and _RECRUITER.search(contact.role):
            return contact
    return contacts[0] if contacts else None


def channel_of(kind: str, contact: Contact | None) -> ReminderChannel:
    """LinkedIn for the 7-day reminder, email for the 14-day one, nothing for the ranking
    proposal; after an interview: LinkedIn if the contact has a LinkedIn link, otherwise email."""
    if kind == "linkedin_7":
        return "linkedin"
    if kind == "close_21":
        return "none"
    if kind == "email_14":
        return "email"
    linkedin = contact is not None and "linkedin." in (contact.url or "").lower()
    return "linkedin" if linkedin else "email"


def reminder_out(
    row: Reminder,
    app: Application,
    contacts: Sequence[Contact],
    kit_text: str | None,
) -> ReminderOut:
    contact = pick_contact(contacts)
    kind: str = row.kind
    draft = draft_for(
        row.kind,  # type: ignore[arg-type]  # text column; values: ReminderKind
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
    """The reminders for the API, in the order given."""
    ids = list({row.application_id for row in rows})
    if not ids:
        return []
    apps = await ApplicationRepository(db, user_id).by_ids(ids)
    contacts = await ContactRepository(db, user_id).of_applications(ids)
    kits = await KitRepository(db, user_id).ready_followups(ids)
    return [
        reminder_out(
            row,
            apps[row.application_id],
            contacts.get(row.application_id, []),
            kits.get(row.application_id),
        )
        for row in rows
    ]
