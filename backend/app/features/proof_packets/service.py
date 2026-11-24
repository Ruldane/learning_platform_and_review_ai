from hashlib import sha256
from hmac import compare_digest
from json import dumps
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.proof_packets import ProofPacket
from app.features.missions.service import MissionRuntime
from app.features.proof_packets import sources
from app.features.proof_packets.repository import ProofPackets
from app.features.proof_packets.schemas import (
    ProofPacketCreate,
    ProofPacketOut,
    ProofPacketPreview,
    ProofPacketSelection,
    ProofPacketSummary,
)
from app.features.proof_packets.schemas import (
    ProofPacketManifest as ProofPacketManifest,
)

PROCEDURE = (
    "Compare the SHA-256 of the downloaded file with the fingerprint shown in the packet.",
    "Identify each submission by its identifier and revision.",
    "Compute the SHA-256 of the UTF-8 submission text and compare it with its fingerprint.",
    "Review the observed measurement and the target of each recorded criterion.",
)


def _canonical(manifest: ProofPacketManifest) -> bytes:
    data = dumps(
        manifest.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return (data + "\n").encode("utf-8")


async def preview(
    rt: MissionRuntime, user_id: str, selection: ProofPacketSelection
) -> ProofPacketPreview:
    manifest = ProofPacketManifest(
        title=selection.title,
        proofs=await sources.selected(rt, user_id, selection.sources),
        procedure=list(PROCEDURE),
    )
    return ProofPacketPreview(manifest=manifest, digest=sha256(_canonical(manifest)).hexdigest())


async def save(
    db: AsyncSession, rt: MissionRuntime, user_id: str, body: ProofPacketCreate
) -> ProofPacketOut:
    reviewed = await preview(rt, user_id, body)
    if not compare_digest(reviewed.digest, body.expected_digest):
        raise AppError("proof_packet_changed", "The manifest has changed. Preview it again.", 409)
    row = await ProofPackets(db, user_id).add(
        title=reviewed.manifest.title,
        digest=reviewed.digest,
        manifest=_canonical(reviewed.manifest).decode("utf-8"),
    )
    return ProofPacketOut(
        id=UUID(row.id),
        created_at=row.created_at,
        manifest=reviewed.manifest,
        digest=reviewed.digest,
    )


async def _owned(db: AsyncSession, user_id: str, packet_id: str) -> ProofPacket:
    row = await ProofPackets(db, user_id).get(packet_id)
    if row is None:
        raise AppError("proof_packet_not_found", "Proof packet not found.", 404)
    return row


def _verified_payload(row: ProofPacket) -> bytes:
    payload = row.manifest.encode("utf-8")
    if not compare_digest(sha256(payload).hexdigest(), row.digest):
        raise AppError("proof_packet_unavailable", "The saved manifest is unreadable.", 409)
    return payload


async def read(db: AsyncSession, user_id: str, packet_id: str) -> ProofPacketOut:
    row = await _owned(db, user_id, packet_id)
    return ProofPacketOut(
        id=UUID(row.id),
        created_at=row.created_at,
        manifest=ProofPacketManifest.model_validate_json(_verified_payload(row)),
        digest=row.digest,
    )


async def export(db: AsyncSession, user_id: str, packet_id: str) -> bytes:
    return _verified_payload(await _owned(db, user_id, packet_id))


async def history(db: AsyncSession, user_id: str) -> list[ProofPacketSummary]:
    rows = await ProofPackets(db, user_id).history()
    return [ProofPacketSummary.model_validate(row, from_attributes=True) for row in rows]
