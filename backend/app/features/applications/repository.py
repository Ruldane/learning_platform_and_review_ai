"""Fiches de candidature, leur fil, leurs contacts et leurs relances (D138, D139). Chaque requête
filtre par `user_id` ; les écritures font un `flush`, le commit appartient à l'appelant."""

import builtins
from collections.abc import Collection
from datetime import date

from sqlalchemy import delete, func, literal_column, select

from app.db.models.applications import Application, ApplicationEvent, Contact, Reminder
from app.db.repository import UserScopedRepository


class ApplicationRepository(UserScopedRepository[Application]):
    model = Application

    async def get_fresh(self, application_id: str) -> Application | None:
        """La fiche relue en base (jamais l'objet gardé par la session)."""
        stmt = (
            select(Application)
            .where(Application.id == application_id, Application.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def recent(
        self, *, status: str | None = None, posting_id: str | None = None
    ) -> builtins.list[Application]:
        """Les fiches, la plus récente d'abord (création décroissante)."""
        stmt = select(Application).where(Application.user_id == self.user_id)
        if status is not None:
            stmt = stmt.where(Application.status == status)
        if posting_id is not None:
            stmt = stmt.where(Application.posting_id == posting_id)
        stmt = stmt.order_by(Application.created_at.desc(), literal_column("rowid").desc())
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def by_posting(self, posting_id: str) -> Application | None:
        """La plus ancienne fiche de l'offre."""
        stmt = (
            select(Application)
            .where(Application.user_id == self.user_id, Application.posting_id == posting_id)
            .order_by(Application.created_at, literal_column("rowid"))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_postings(self, posting_ids: Collection[str]) -> dict[str, Application]:
        """`offre → fiche` (la plus ancienne) des offres données qui ont une fiche, quel que
        soit son statut (une fiche « Retirée » compte)."""
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
        """`fiche → nombre de relances dues` (en attente, échéance au plus aujourd'hui)."""
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
        """Le fil de la fiche, du plus ancien au plus récent."""
        stmt = (
            select(ApplicationEvent)
            .where(
                ApplicationEvent.user_id == self.user_id,
                ApplicationEvent.application_id == application_id,
            )
            .order_by(ApplicationEvent.at, literal_column("rowid"))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class ContactRepository(UserScopedRepository[Contact]):
    model = Contact

    async def of_application(self, application_id: str) -> builtins.list[Contact]:
        """Les contacts de la fiche, dans l'ordre où January les a donnés."""
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
