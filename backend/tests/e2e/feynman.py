"""Deux réponses scriptées pour la recette Explique-moi."""

import argparse
import json
from pathlib import Path

import uvicorn

from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--origin", required=True)
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin, port=args.port)
    migrate(settings)
    reports = [
        {
            "summary": "Il manque un cas limite.",
            "mastered": False,
            "follow_up": "Que renvoie la fonction si la liste est vide ?",
        },
        {
            "summary": "La règle et son cas limite sont expliqués.",
            "mastered": True,
            "cards": [{"front": "Quelle somme pour une liste vide ?", "back": "Zéro."}],
        },
    ]
    app = build_app(settings, scripts={"training_tutor": [json.dumps(item) for item in reports]})
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
