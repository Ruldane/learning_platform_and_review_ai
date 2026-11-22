"""Recette du Pilote, avec réponses du Tuteur scriptées sur la vraie API."""

import argparse
from pathlib import Path

import uvicorn

from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir

REPLIES = [
    "Première question du tuteur.",
    *[
        f"Réponse du tuteur {idx}.\n\n<!-- concentration:{'correct' if idx <= 3 else 'retry'} -->"
        for idx in range(1, 7)
    ],
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8810)
    parser.add_argument("--origin", default="http://127.0.0.1:5210")
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings, scripts={"training_tutor": REPLIES})
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
