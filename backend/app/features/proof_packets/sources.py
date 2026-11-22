from hashlib import sha256
from uuid import UUID

from app.core.errors import AppError
from app.features.missions.service import MissionRuntime, list_missions
from app.features.proof_packets.schemas import (
    ProofPacketItem,
    ProofPacketMeasure,
    ProofPacketReference,
    ProofPacketSource,
)


async def _available(rt: MissionRuntime, user_id: str) -> dict[UUID, ProofPacketItem | None]:
    """Les mesures de la mission et le rendu sont figés dans la même lecture par compte."""
    result: dict[UUID, ProofPacketItem | None] = {}
    for mission in await list_missions(rt, user_id):
        mission_id = UUID(mission.id)
        result[mission_id] = None
        approved = mission.submission
        if (
            approved is None
            or mission.status != "completed"
            or not mission.criteria
            or any(row.observed != row.target for row in mission.criteria)
        ):
            continue
        result[mission_id] = ProofPacketItem(
            mission_id=mission_id,
            title=mission.posting_title or "Mission",
            proof_id=UUID(approved.proof_id),
            revision=mission.revision,
            recorded_at=approved.recorded_at,
            artifact=approved.artifact,
            artifact_digest=sha256(approved.artifact.encode("utf-8")).hexdigest(),
            measurements=[
                ProofPacketMeasure(
                    index=row.index, label=row.text, observed=row.observed, target=row.target
                )
                for row in sorted(mission.criteria, key=lambda row: row.index)
            ],
        )
    return result


async def choices(rt: MissionRuntime, user_id: str) -> list[ProofPacketSource]:
    return [
        ProofPacketSource(
            mission_id=proof.mission_id,
            proof_id=proof.proof_id,
            revision=proof.revision,
            title=proof.title,
        )
        for proof in (await _available(rt, user_id)).values()
        if proof is not None
    ]


async def selected(
    rt: MissionRuntime, user_id: str, references: list[ProofPacketReference]
) -> list[ProofPacketItem]:
    available = await _available(rt, user_id)
    proofs = []
    for reference in sorted(references, key=lambda reference: reference.mission_id):
        if reference.mission_id not in available:
            raise AppError("proof_source_not_found", "Rendu introuvable.", 404)
        proof = available[reference.mission_id]
        if proof is None:
            raise AppError("proof_source_unapproved", "Enregistre d’abord le rendu mesuré.", 409)
        if (proof.proof_id, proof.revision) != (reference.proof_id, reference.revision):
            raise AppError("proof_source_changed", "Le rendu a changé. Relis les preuves.", 409)
        proofs.append(proof)
    return proofs
