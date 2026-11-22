"""Recette du procès sur des fichiers fictifs et deux modèles scriptés."""

import argparse
from pathlib import Path

import uvicorn

from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.code_trial.test_trial import SCRIPT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8797)
    parser.add_argument("--origin", default="http://127.0.0.1:5197")
    args = parser.parse_args()
    data_dir = prepare_data_dir(args.data_dir)
    settings = e2e_settings(data_dir, origin=args.origin, port=args.port)
    migrate(settings)
    scripts = {"code_prosecutor": [SCRIPT[0]], "code_defender": [SCRIPT[1]]}
    uvicorn.run(build_app(settings, scripts=scripts), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
