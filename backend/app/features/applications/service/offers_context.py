from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.applications.repository import ApplicationRepository, ContactRepository


@dataclass(frozen=True)
class ContactFact:
    name: str
    role: str | None


@dataclass(frozen=True)
class ApplicationFact:
    id: str
    status: str
    applied_on: date | None
    contacts: tuple[ContactFact, ...]


async def applications_for_offers_chat(
    db: AsyncSession, user_id: str, posting_ids: Collection[str], detailed_ids: Collection[str]
) -> dict[str, list[ApplicationFact]]:
    """Read facts from linked applications without updating any application records."""
    rows = await ApplicationRepository(db, user_id).recent()
    contacts = await ContactRepository(db, user_id).of_applications(
        [row.id for row in rows if row.posting_id in detailed_ids]
    )
    linked: dict[str, list[ApplicationFact]] = defaultdict(list)
    for row in rows:
        if row.posting_id is None or row.posting_id not in posting_ids:
            continue
        facts = tuple(ContactFact(c.name, c.role) for c in contacts.get(row.id, []))
        linked[row.posting_id].append(ApplicationFact(row.id, row.status, row.applied_on, facts))
    return dict(linked)
