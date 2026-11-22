from sqlalchemy import select

from app.db.models.proof_packets import ProofPacket
from app.db.repository import UserScopedRepository


class ProofPackets(UserScopedRepository[ProofPacket]):
    model = ProofPacket

    async def history(self) -> list[ProofPacket]:
        stmt = (
            select(self.model)
            .where(self.model.user_id == self.user_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
        )
        return list(await self.session.scalars(stmt))
