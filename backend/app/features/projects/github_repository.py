from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.github_claims import ProjectGithubClaim


class GithubClaimRepository:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self.db, self.user_id = db, user_id

    async def confirmed(self, project_id: str) -> Sequence[ProjectGithubClaim]:
        claims = ProjectGithubClaim
        return (
            await self.db.scalars(
                select(claims)
                .where(
                    claims.user_id == self.user_id,
                    claims.project_id == project_id,
                    claims.verified_at.is_not(None),
                )
                .order_by(claims.verified_at.desc())
                .limit(50)
            )
        ).all()

    async def get(self, project_id: str, claim_id: str) -> ProjectGithubClaim | None:
        claims = ProjectGithubClaim
        return await self.db.scalar(
            select(claims).where(
                claims.user_id == self.user_id,
                claims.project_id == project_id,
                claims.id == claim_id,
            )
        )

    async def confirmed_sha(self, sha: str) -> bool:
        claims = ProjectGithubClaim
        return bool(
            await self.db.scalar(
                select(claims.id).where(
                    claims.user_id == self.user_id,
                    claims.sha == sha,
                    claims.verified_at.is_not(None),
                )
            )
        )

    async def issue(self, project_id: str, **values: Any) -> ProjectGithubClaim:
        claims = ProjectGithubClaim
        await self.db.execute(
            delete(claims).where(
                claims.user_id == self.user_id,
                claims.project_id == project_id,
                claims.verified_at.is_(None),
            )
        )
        row = ProjectGithubClaim(user_id=self.user_id, project_id=project_id, **values)
        self.db.add(row)
        await self.db.flush()
        return row

    async def consume(self, claim: ProjectGithubClaim, session_id: str, moment: datetime) -> bool:
        claims = ProjectGithubClaim
        return bool(
            await self.db.scalar(
                update(claims)
                .where(
                    claims.user_id == self.user_id,
                    claims.project_id == claim.project_id,
                    claims.id == claim.id,
                    claims.challenge_digest == claim.challenge_digest,
                    claims.verified_at.is_(None),
                    claims.expires_at > moment,
                )
                .values(verified_at=moment, session_id=session_id, challenge_digest=None)
                .returning(claims.id)
            )
        )
