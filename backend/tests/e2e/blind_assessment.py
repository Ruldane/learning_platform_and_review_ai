"""Épreuve en aveugle sur deux versions de CV factices et le vrai moteur."""

import argparse
import json
from pathlib import Path

import uvicorn
from fastapi import APIRouter, Request

from app.core.deps import CurrentUserDep
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.blind_assessment.support import seed_versions

router = APIRouter(prefix="/e2e/blind-assessment")


@router.post("/ready")
async def ready(request: Request, user: CurrentUserDep) -> dict[str, list[str]]:
    return {"version_ids": list(await seed_versions(request.app, user.id))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8904)
    parser.add_argument("--origin", default="http://localhost:5304")
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin=args.origin, port=args.port)
    migrate(settings)
    grade = {
        "scores_a": [1, 2, 3],
        "scores_b": [3, 3, 4],
        "feedback": "Le texte B rend les résultats plus faciles à évaluer.",
    }
    app = build_app(settings, scripts={"verifier": [json.dumps(grade)]})
    app.include_router(router)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
