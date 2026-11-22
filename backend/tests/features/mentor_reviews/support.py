from hashlib import sha256
from json import dumps
from uuid import uuid4

from fastapi import FastAPI

from app.db.models.proof_packets import ProofPacket

TITLE = "Dossier synthétique du mentor"
ARTIFACT = "Le prototype fictif traite les deux exemples attendus."


async def seed_packet(app: FastAPI) -> tuple[str, str, str]:
    proof_id = str(uuid4())
    manifest = {
        "schema_version": 1,
        "title": TITLE,
        "proofs": [
            {
                "proof_id": proof_id,
                "mission_id": str(uuid4()),
                "revision": 2,
                "recorded_at": "2026-11-22T12:00:00Z",
                "title": "Prototype fictif",
                "artifact": ARTIFACT,
                "artifact_digest": sha256(ARTIFACT.encode("utf-8")).hexdigest(),
                "measurements": [{"index": 0, "label": "Cas traités", "observed": 2, "target": 2}],
            }
        ],
        "procedure": ["Vérifier le nombre de cas."],
    }
    text = dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    digest = sha256(text.encode("utf-8")).hexdigest()
    async with app.state.session_factory() as db:
        row = ProofPacket(
            user_id=app.state.local_user_id, title=TITLE, digest=digest, manifest=text
        )
        db.add(row)
        await db.flush()
        packet_id = str(row.id)
        await db.commit()
    return packet_id, digest, proof_id
