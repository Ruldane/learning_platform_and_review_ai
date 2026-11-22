"""Accès par compte et réservation atomique des transitions du simulateur."""

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import set_committed_value

from app.core.errors import AppError
from app.db.models.oncall import OncallIncident
from app.db.repository import UserScopedRepository


def diagnostic_in_progress() -> AppError:
    return AppError("diagnostic_in_progress", "Un autre diagnostic est en cours.", 409)


class IncidentRepository(UserScopedRepository[OncallIncident]):
    model = OncallIncident

    async def get_fresh(self, incident_id: str) -> OncallIncident | None:
        stmt = (
            select(OncallIncident)
            .where(OncallIncident.id == incident_id, OncallIncident.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def recent(self) -> list[OncallIncident]:
        stmt = (
            select(OncallIncident)
            .where(OncallIncident.user_id == self.user_id)
            .order_by(OncallIncident.created_at.desc(), OncallIncident.id.desc())
            .limit(50)
        )
        return [row for row in (await self.session.execute(stmt)).scalars()]

    async def running_diagnostic(self) -> OncallIncident | None:
        stmt = (
            select(OncallIncident)
            .where(
                OncallIncident.user_id == self.user_id,
                OncallIncident.diagnostic_state == "running",
            )
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def require(self, incident_id: str) -> OncallIncident:
        row = await self.get_fresh(incident_id)
        if row is None:
            raise AppError("incident_not_found", "Incident introuvable.", 404)
        return row

    async def claim(self, row: OncallIncident) -> None:
        version = row.version
        stmt = (
            update(OncallIncident)
            .where(
                OncallIncident.user_id == self.user_id,
                OncallIncident.id == row.id,
                OncallIncident.version == version,
            )
            .values(version=version + 1)
            .returning(OncallIncident.id)
            .execution_options(synchronize_session=False)
        )
        if (await self.session.execute(stmt)).scalar_one_or_none() is None:
            raise AppError("incident_changed", "L’incident a évolué. Relis son journal.", 409)
        set_committed_value(row, "version", version + 1)

    async def reserve_diagnostic(self, row: OncallIncident, run_id: str, fingerprint: str) -> None:
        await self.claim(row)
        row.diagnostic_run_id, row.diagnostic_state, row.diagnostic_hash = (
            run_id,
            "running",
            fingerprint,
        )
        try:
            # Vérifie l'unicité par compte avant tout dépôt dans le bac.
            await self.session.flush()
        except IntegrityError:
            raise diagnostic_in_progress() from None
