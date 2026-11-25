"""Recette de transfert sur le moteur réel et les réponses scriptées du Vérificateur."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db
from app.core.skills import evidence
from app.features.skill_transfer.router import clock
from app.features.skills.service import SkillsService
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir

NOW = datetime(2026, 11, 22, 12, tzinfo=UTC)
SKILL = "Idempotence des écritures"
EXERCISE = {
    "title": "Une billetterie reçoit deux confirmations",
    "prompt": (
        "Un client paie une place. Le portail renvoie deux confirmations du même paiement. "
        "Explique comment garantir un seul billet même après un arrêt du serveur."
    ),
    "criteria": [
        "Identifie une clé stable par paiement.",
        "Protège la création du billet par une transaction atomique.",
        "Explique le rejeu après un arrêt.",
    ],
}
ASSESSMENT = {
    "met": [True, False, True],
    "feedback": "La clé est stable. Précise comment rendre l’écriture et son reçu atomiques.",
}
router = APIRouter(prefix="/e2e/skill-transfer")


@router.post("/ready")
async def ready(db: Db, user: CurrentUserDep) -> dict[str, str]:
    service = SkillsService(db, user.id)
    await service.raise_levels(
        [SKILL], "proven", evidence("project", "livraison-fictive", "Import sans doublons", NOW)
    )
    skill_id = await service.skill_id_for(SKILL)
    assert skill_id is not None
    return {"skill_id": skill_id}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8904)
    parser.add_argument("--origin", default="http://localhost:5304")
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(
        settings,
        scripts={"verifier": [json.dumps(EXERCISE), json.dumps(ASSESSMENT)]},
    )
    app.include_router(router)
    app.dependency_overrides[clock] = lambda: NOW
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
