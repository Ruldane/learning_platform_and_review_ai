"""Application records, their timeline, contacts and follow-ups (D138, D139). Every query
filters by `user_id`; writes `flush`, the commit belongs to the caller."""

import builtins
from collections.abc import Collection
from datetime import date

from sqlalchemy import delete, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import User
from app.db.models.applications import (
    Application,
    ApplicationEvent,
    Contact,
    KitItem,
    Reminder,
)
from app.db.models.postings import Company
from app.db.repository import UserScopedRepository


class ApplicationRepository(UserScopedRepository[Application]):
    model = Application

    async def get_fresh(self, application_id: str) -> Application | None:
        """The record re-read from the database (never the object held by the session)."""
        stmt = (
            select(Application)
            .where(Application.id == application_id, Application.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def recent(
        self, *, status: str | None = None, posting_id: str | None = None
    ) -> builtins.list[Application]:
        """The records, most recent first (descending creation)."""
        stmt = select(Application).where(Application.user_id == self.user_id)
        if status is not None:
            stmt = stmt.where(Application.status == status)
        if posting_id is not None:
            stmt = stmt.where(Application.posting_id == posting_id)
        stmt = stmt.order_by(Application.created_at.desc(), literal_column("rowid").desc())
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def by_posting(self, posting_id: str) -> Application | None:
        """The oldest record for the posting."""
        stmt = (
            select(Application)
            .where(Application.user_id == self.user_id, Application.posting_id == posting_id)
            .order_by(Application.created_at, literal_column("rowid"))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_postings(self, posting_ids: Collection[str]) -> dict[str, Application]:
        """`posting → record` (the oldest) for the given postings that have a record, whatever
        its status (a "Withdrawn" record counts)."""
        if not posting_ids:
            return {}
        stmt = (
            select(Application)
            .where(
                Application.user_id == self.user_id,
                Application.posting_id.in_(builtins.list(posting_ids)),
            )
            .order_by(Application.created_at.desc(), literal_column("rowid").desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return {row.posting_id: row for row in rows if row.posting_id is not None}

    async def by_ids(self, ids: Collection[str]) -> dict[str, Application]:
        if not ids:
            return {}
        stmt = select(Application).where(
            Application.user_id == self.user_id, Application.id.in_(builtins.list(ids))
        )
        return {row.id: row for row in (await self.session.execute(stmt)).scalars()}

    async def due_counts(self, today: date) -> dict[str, int]:
        """`record → number of due follow-ups` (pending, due today at the latest)."""
        stmt = (
            select(Reminder.application_id, func.count())
            .where(
                Reminder.user_id == self.user_id,
                Reminder.status == "pending",
                Reminder.due_on <= today,
            )
            .group_by(Reminder.application_id)
        )
        return {app_id: int(count) for app_id, count in (await self.session.execute(stmt)).all()}

    async def reminders(self, application_id: str) -> builtins.list[Reminder]:
        stmt = (
            select(Reminder)
            .where(Reminder.user_id == self.user_id, Reminder.application_id == application_id)
            .order_by(Reminder.due_on, literal_column("rowid"))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class EventRepository(UserScopedRepository[ApplicationEvent]):
    model = ApplicationEvent

    async def of_application(self, application_id: str) -> builtins.list[ApplicationEvent]:
        """The record's timeline, oldest to newest."""
        stmt = (
            select(ApplicationEvent)
            .where(
                ApplicationEvent.user_id == self.user_id,
                ApplicationEvent.application_id == application_id,
            )
            .order_by(ApplicationEvent.at, literal_column("rowid"))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def created_by(self, session_id: str) -> str | None:
        """The record created by this Tracking Assistant session (`ref_id` of its `created`
        event), `None` if there is none."""
        stmt = select(ApplicationEvent.application_id).where(
            ApplicationEvent.user_id == self.user_id,
            ApplicationEvent.kind == "created",
            ApplicationEvent.ref_id == session_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def kit_ended(self, session_id: str) -> bool:
        """The "kit finished" event of this session is already in the timeline."""
        stmt = select(ApplicationEvent.id).where(
            ApplicationEvent.user_id == self.user_id,
            ApplicationEvent.kind == "kit",
            ApplicationEvent.ref_id == session_id,
            ApplicationEvent.text.like("Kit de candidature terminé%"),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def version_frozen(self) -> set[str]:
        """The records whose CV version is frozen (they have a `version` event)."""
        stmt = select(ApplicationEvent.application_id).where(
            ApplicationEvent.user_id == self.user_id, ApplicationEvent.kind == "version"
        )
        return set((await self.session.execute(stmt)).scalars())


class ContactRepository(UserScopedRepository[Contact]):
    model = Contact

    async def of_application(self, application_id: str) -> builtins.list[Contact]:
        """The record's contacts, in the order January gave them."""
        stmt = (
            select(Contact)
            .where(Contact.user_id == self.user_id, Contact.application_id == application_id)
            .order_by(literal_column("rowid"))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def clear(self, application_id: str) -> None:
        await self.session.execute(
            delete(Contact).where(
                Contact.user_id == self.user_id, Contact.application_id == application_id
            )
        )

    async def of_applications(
        self, application_ids: Collection[str]
    ) -> dict[str, builtins.list[Contact]]:
        """`record → contacts` (in the order January gave them) for the given records."""
        if not application_ids:
            return {}
        stmt = (
            select(Contact)
            .where(
                Contact.user_id == self.user_id,
                Contact.application_id.in_(builtins.list(application_ids)),
            )
            .order_by(literal_column("rowid"))
        )
        found: dict[str, builtins.list[Contact]] = {}
        for row in (await self.session.execute(stmt)).scalars():
            found.setdefault(row.application_id, []).append(row)
        return found


class ReminderRepository(UserScopedRepository[Reminder]):
    model = Reminder

    async def listing(self, *, due_on: date | None) -> builtins.list[Reminder]:
        """The follow-ups, by ascending due date: pending and due by `due_on` at the latest, or all
        of them (`due_on` empty)."""
        stmt = select(Reminder).where(Reminder.user_id == self.user_id)
        if due_on is not None:
            stmt = stmt.where(Reminder.status == "pending", Reminder.due_on <= due_on)
        stmt = stmt.order_by(Reminder.due_on, literal_column("rowid"))
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def of_applications(
        self, application_ids: Collection[str] | None = None
    ) -> builtins.list[Reminder]:
        """The follow-ups of all records, or of the given records."""
        stmt = select(Reminder).where(Reminder.user_id == self.user_id)
        if application_ids is not None:
            stmt = stmt.where(Reminder.application_id.in_(builtins.list(application_ids)))
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def get_fresh(self, reminder_id: str) -> Reminder | None:
        stmt = (
            select(Reminder)
            .where(Reminder.id == reminder_id, Reminder.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class KitRepository(UserScopedRepository[KitItem]):
    model = KitItem

    async def ready_followups(self, application_ids: Collection[str]) -> dict[str, str]:
        """`record → text` of the ready "follow-ups" piece (never "to check" nor failed)."""
        if not application_ids:
            return {}
        stmt = select(KitItem.application_id, KitItem.content).where(
            KitItem.user_id == self.user_id,
            KitItem.kind == "followups",
            KitItem.status == "ready",
            KitItem.application_id.in_(builtins.list(application_ids)),
        )
        return {app_id: content for app_id, content in (await self.session.execute(stmt)).all()}

    async def of_application(self, application_id: str) -> builtins.list[KitItem]:
        """The record's pieces (at most one per kind), re-read from the database."""
        stmt = (
            select(KitItem)
            .where(KitItem.user_id == self.user_id, KitItem.application_id == application_id)
            .order_by(literal_column("rowid"))
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def of_kind(self, application_id: str, kind: str) -> KitItem | None:
        for row in await self.of_application(application_id):
            if row.kind == kind:
                return row
        return None


class CompanyRepository(UserScopedRepository[Company]):
    """Company records, for the kit's company file (the record is shared with CV reviews: only
    the `dossier*` columns are written here)."""

    model = Company

    async def by_key(self, name_norm: str) -> Company | None:
        stmt = (
            select(Company)
            .where(Company.user_id == self.user_id, Company.name_norm == name_norm)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()


async def user_ids(session: AsyncSession) -> builtins.list[str]:
    """The ids of ALL accounts: the ONLY read without `user_id` in applications (like D18, D75
    and D91), reserved for the scheduled follow-up job, which then works account by account
    (every following read filters by `user_id`)."""
    stmt = select(User.id).order_by(User.created_at, literal_column("rowid"))
    return builtins.list((await session.execute(stmt)).scalars().all())


async def user_language(session: AsyncSession, user_id: str) -> str:
    """The language of January's interface (`fr` by default)."""
    stmt = select(User.language).where(User.id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none() or "fr"
