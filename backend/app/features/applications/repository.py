"""Fiches de candidature, leur fil, leurs contacts et leurs relances (D138, D139). Chaque requête
filtre par `user_id` ; les écritures font un `flush`, le commit appartient à l'appelant."""

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

    async def created_by(self, session_id: str) -> str | None:
        """La fiche créée par cette session de l'Assistant de suivi (`ref_id` de son événement
        `created`), `None` s'il n'y en a pas."""
        stmt = select(ApplicationEvent.application_id).where(
            ApplicationEvent.user_id == self.user_id,
            ApplicationEvent.kind == "created",
            ApplicationEvent.ref_id == session_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def kit_ended(self, session_id: str) -> bool:
        """L'événement « kit terminé » de cette session est déjà au fil."""
        stmt = select(ApplicationEvent.id).where(
            ApplicationEvent.user_id == self.user_id,
            ApplicationEvent.kind == "kit",
            ApplicationEvent.ref_id == session_id,
            ApplicationEvent.text.like("Kit de candidature terminé%"),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def version_frozen(self) -> set[str]:
        """Les fiches dont la version de CV est figée (elles ont un événement `version`)."""
        stmt = select(ApplicationEvent.application_id).where(
            ApplicationEvent.user_id == self.user_id, ApplicationEvent.kind == "version"
        )
        return set((await self.session.execute(stmt)).scalars())


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

    async def of_applications(
        self, application_ids: Collection[str]
    ) -> dict[str, builtins.list[Contact]]:
        """`fiche → contacts` (dans l'ordre où January les a donnés) des fiches données."""
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
        """Les relances, échéance croissante : en attente et dues au plus `due_on`, ou toutes
        (`due_on` vide)."""
        stmt = select(Reminder).where(Reminder.user_id == self.user_id)
        if due_on is not None:
            stmt = stmt.where(Reminder.status == "pending", Reminder.due_on <= due_on)
        stmt = stmt.order_by(Reminder.due_on, literal_column("rowid"))
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def of_applications(
        self, application_ids: Collection[str] | None = None
    ) -> builtins.list[Reminder]:
        """Les relances de toutes les fiches, ou des fiches données."""
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
        """`fiche → texte` de la pièce « relances » prête (jamais « à vérifier » ni en échec)."""
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
        """Les pièces de la fiche (au plus une par type), relues en base."""
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
    """Fiches d'entreprise, pour le dossier du kit (la fiche est partagée avec les revues de CV :
    seules les colonnes `dossier*` sont écrites ici)."""

    model = Company

    async def by_key(self, name_norm: str) -> Company | None:
        stmt = (
            select(Company)
            .where(Company.user_id == self.user_id, Company.name_norm == name_norm)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()


async def user_ids(session: AsyncSession) -> builtins.list[str]:
    """Les identifiants de TOUS les comptes : SEULE lecture sans `user_id` des candidatures
    (comme D18, D75 et D91), réservée à la tâche planifiée des relances, qui travaille ensuite
    compte par compte (toutes les lectures suivantes filtrent par `user_id`)."""
    stmt = select(User.id).order_by(User.created_at, literal_column("rowid"))
    return builtins.list((await session.execute(stmt)).scalars().all())


async def user_language(session: AsyncSession, user_id: str) -> str:
    """La langue de l'interface de January (`fr` par défaut)."""
    stmt = select(User.language).where(User.id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none() or "fr"
