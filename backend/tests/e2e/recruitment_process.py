"""Répétition d’un recrutement sur un projet, une offre et un évaluateur factices."""

import argparse
import json
from pathlib import Path

import uvicorn
from fastapi import APIRouter, Request

from app.core.deps import CurrentUserDep
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.recruitment_process.support import GRADES, seed_rehearsal

router = APIRouter(prefix="/e2e/recruitment-process")


@router.post("/ready")
async def ready(request: Request, user: CurrentUserDep) -> dict[str, str]:
    posting, project = await seed_rehearsal(request.app, user.id)
    return {"posting_id": posting, "project_id": project}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8904)
    parser.add_argument("--origin", default="http://localhost:5304")
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings, scripts={"verifier": [json.dumps(grade) for grade in GRADES]})
    app.include_router(router)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
