import re
from datetime import datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import KnownSecrets
from app.db.base import utcnow
from app.db.models.mentor_reviews import MentorShare
from app.features.mentor_reviews.repository import MentorComments, MentorShares
from app.features.mentor_reviews.schemas import (
    MentorCommentCreate,
    MentorCommentOut,
    MentorOwnedComment,
    MentorShareCreate,
    MentorShareDetail,
    MentorSharedWork,
    MentorShareIssued,
    MentorShareOut,
    ShareStatus,
)
from app.features.proof_packets import service as packets
from app.features.proof_packets.service import ProofPacketManifest

_TOKEN = re.compile(r"trmentor_([a-zA-Z0-9_-]{1,36})\.[a-zA-Z0-9_-]{43}")


def _unavailable() -> AppError:
    return AppError("mentor_link_unavailable", "Review link unavailable.", 404)


def _not_found() -> AppError:
    return AppError("mentor_share_not_found", "Mentor share not found.", 404)


def _hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _scope(token: str) -> tuple[str, str]:
    match = _TOKEN.fullmatch(token) if len(token) <= 100 else None
    if match is None:
        raise _unavailable()
    return match.group(1), _hash(token)


def _status(row: MentorShare, now: datetime) -> ShareStatus:
    if row.revoked_at is not None:
        return "revoked"
    return "expired" if row.expires_at <= now else "active"


def _view(row: MentorShare, now: datetime) -> MentorShareOut:
    return MentorShareOut(
        id=UUID(row.id),
        packet_id=UUID(row.packet_id),
        title=row.title,
        digest=row.digest,
        created_at=row.created_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        status=_status(row, now),
    )


def _manifest(share: MentorShare) -> ProofPacketManifest:
    if not compare_digest(_hash(share.manifest), share.digest):
        raise _unavailable()
    return ProofPacketManifest.model_validate_json(share.manifest)


async def create(db: AsyncSession, user_id: str, approval: MentorShareCreate) -> MentorShareIssued:
    packet_id = str(approval.packet_id)
    packet = await packets.read(db, user_id, packet_id)
    if not compare_digest(packet.digest, approval.expected_digest):
        raise AppError(
            "mentor_copy_changed", "The copy has changed. Reread it before sharing.", 409
        )
    payload = await packets.export(db, user_id, packet_id)
    token = f"trmentor_{user_id}.{token_urlsafe(32)}"
    KnownSecrets.add(token)
    now = utcnow()
    row = await MentorShares(db, user_id).add(
        packet_id=packet_id,
        title=packet.manifest.title,
        digest=packet.digest,
        manifest=payload.decode("utf-8"),
        token_hash=_hash(token),
        expires_at=now + timedelta(hours=approval.valid_hours),
        revoked_at=None,
    )
    return MentorShareIssued(share=_view(row, now), token=token)


async def list_owned(db: AsyncSession, user_id: str) -> list[MentorShareOut]:
    now = utcnow()
    rows = await MentorShares(db, user_id).history()
    return [_view(row, now) for row in rows]


async def read_owned(db: AsyncSession, user_id: str, share_id: str) -> MentorShareDetail:
    row = await MentorShares(db, user_id).get(share_id)
    if row is None:
        raise _not_found()
    comments = [
        MentorOwnedComment.model_validate(comment, from_attributes=True)
        for comment in await MentorComments(db, user_id).for_share(share_id)
    ]
    return MentorShareDetail(**_view(row, utcnow()).model_dump(), comments=comments)


async def mark_comment(
    db: AsyncSession, user_id: str, share_id: str, comment_id: str, reviewed: bool
) -> MentorOwnedComment:
    row = await MentorComments(db, user_id).get(comment_id)
    if row is None or row.share_id != share_id:
        raise AppError("mentor_comment_not_found", "Mentor comment not found.", 404)
    row.reviewed = reviewed
    return MentorOwnedComment.model_validate(row, from_attributes=True)


async def revoke(db: AsyncSession, user_id: str, share_id: str) -> None:
    if not await MentorShares(db, user_id).revoke(share_id, utcnow()):
        raise _not_found()


async def read_shared(db: AsyncSession, token: str) -> MentorSharedWork:
    user_id, digest = _scope(token)
    row = await MentorShares(db, user_id).active(digest, utcnow())
    if row is None or row.expires_at <= utcnow():
        raise _unavailable()
    return MentorSharedWork(manifest=_manifest(row), digest=row.digest, expires_at=row.expires_at)


async def comment(db: AsyncSession, token: str, body: MentorCommentCreate) -> MentorCommentOut:
    user_id, digest = _scope(token)
    # The reservation and the insert share the transaction. Revocation takes the same SQLite lock.
    row = await MentorShares(db, user_id).claim_for_comment(digest, utcnow())
    if row is None or row.expires_at <= utcnow():
        raise _unavailable()
    if not any(proof.proof_id == body.proof_id for proof in _manifest(row).proofs):
        raise AppError("mentor_proof_not_shared", "This submission is not in the copy.", 422)
    created = await MentorComments(db, user_id).add(
        share_id=row.id, proof_id=str(body.proof_id), text=body.text
    )
    return MentorCommentOut.model_validate(created, from_attributes=True)
