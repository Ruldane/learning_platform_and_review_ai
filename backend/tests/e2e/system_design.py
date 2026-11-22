"""Serveur de recette de l’entretien d’architecture, entièrement scripté."""

import argparse
import json
from pathlib import Path

import uvicorn

from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir

REVIEW = {
    "criteria": {
        name: {"score": 4, "feedback": "Le choix est expliqué et ses limites sont discutées."}
        for name in ("architecture", "reliability", "scale", "tradeoffs")
    },
    "summary": "Le schéma et la défense proposent une reprise explicite.",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--origin", required=True)
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings, scripts={"interviewer": [json.dumps(REVIEW)]})
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
